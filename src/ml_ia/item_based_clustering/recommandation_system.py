import logging
from pathlib import Path
import pandas as pd
import duckdb
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix

LOG = logging.getLogger(__name__)
DB_NAME = Path("../../amazing.duckdb")

# Global model/state placeholders (initialized on first use)
_models = {
    'item_similarity_df': None,
    'item_popularity': None,
    'product_category_map': None,
    'user_item_matrix': None,
    'initialized': False,
}


def _get_cf_matrix(limit=50):
    """Open a short-lived DuckDB connection and return cf_matrix as DataFrame.
    This avoids doing DB work at import time and closes connections cleanly.
    """
    try:
        with duckdb.connect(str(DB_NAME)) as con:
            cfq = con.sql(f"SELECT * FROM cf_matrix LIMIT {limit}")
            return cfq.df()
    except Exception as e:
        LOG.exception("Failed to load cf_matrix from DB: %s", e)
        return None


def _build_models(events_limit=500, cf_limit=100):
    """Load data, build user-item and item-similarity matrices. Safe and idempotent."""
    if _models['initialized']:
        return

    try:
        with duckdb.connect(str(DB_NAME)) as con:
            LOG.info("Connected to database at: %s", DB_NAME)
            # load sample of events (bounded for memory)
            q = f"SELECT * FROM all_events ORDER BY RANDOM() LIMIT {events_limit}"
            all_events_df = con.sql(q).df()

        if all_events_df is None or all_events_df.empty:
            LOG.warning("No events loaded from DB; models will not be initialized.")
            _models['initialized'] = True
            return

        # Select relevant columns and clean
        allevents_df_CF = all_events_df[["user_id", "product_id", "category_code", "category_id", "event_type"]].copy()
        allevents_df_CF.dropna(subset=["category_code"], inplace=True)

        # Map event types to numeric scores (tunable)
        allevents_df_CF["event_score"] = allevents_df_CF["event_type"].map({"view": 1, "cart": 2, "purchase": 5}).fillna(0)

        # Build user-item matrix (items x users)
        user_item_matrix = allevents_df_CF.pivot_table(
            index='product_id',
            columns='user_id',
            values='event_score',
            aggfunc='max'
        ).fillna(0)

        # Popularity and category map for fallback
        item_popularity = allevents_df_CF['product_id'].value_counts()
        product_category_map = allevents_df_CF[['product_id', 'category_code']].drop_duplicates('product_id').set_index('product_id')

        # Load cf_matrix from DB; it should align with user_item_matrix index ideally
        cf_matrix_df = _get_cf_matrix(limit=cf_limit)

        item_similarity_df = None
        if cf_matrix_df is not None and not cf_matrix_df.empty:
            # If the cf_matrix has an index column (like product_id) try to set it
            # If first column is non-numeric we assume it's an id column
            if cf_matrix_df.shape[1] > 0 and not np.issubdtype(cf_matrix_df.iloc[:, 0].dtype, np.number):
                try:
                    cf_matrix_df = cf_matrix_df.set_index(cf_matrix_df.columns[0])
                except Exception:
                    pass

            # Ensure numeric values only for similarity computation
            numeric_df = cf_matrix_df.select_dtypes(include=[np.number])
            if numeric_df.shape[0] > 0 and numeric_df.shape[1] > 0:
                try:
                    sparse_user_item = csr_matrix(numeric_df.values.astype(float))
                    # Avoid computing if matrix is degenerate
                    if sparse_user_item.shape[0] > 1 and sparse_user_item.shape[1] > 0:
                        item_similarity = cosine_similarity(sparse_user_item)
                        # align index labels: prefer numeric_df.index if present, else user_item_matrix.index
                        idx = list(numeric_df.index) if numeric_df.index is not None else list(user_item_matrix.index)
                        # If lengths mismatch, fall back to user_item_matrix index intersection
                        if len(idx) != item_similarity.shape[0]:
                            LOG.warning("Index length mismatch between cf_matrix and similarity output; skipping label alignment.")
                            item_similarity_df = pd.DataFrame(item_similarity)
                        else:
                            item_similarity_df = pd.DataFrame(item_similarity, index=idx, columns=idx)
                except Exception:
                    LOG.exception("Failed computing cosine similarity; will disable CF similarity.")

        # Save into globals
        _models['item_similarity_df'] = item_similarity_df
        _models['item_popularity'] = item_popularity
        _models['product_category_map'] = product_category_map
        _models['user_item_matrix'] = user_item_matrix
        _models['initialized'] = True
        LOG.info("Model build complete. Items: %s", 0 if user_item_matrix is None else user_item_matrix.shape[0])

    except Exception:
        LOG.exception("Unexpected error while building models")
        _models['initialized'] = True


def get_parent_category(category_code):
    """Extracts the parent category from a dot-separated category code."""
    if pd.isna(category_code) or category_code == "Unknown":
        return None
    parts = str(category_code).split('.')
    if len(parts) > 1:
        return '.'.join(parts[:-1])
    return parts[0]


def get_similar_items(product_id, n=5, threshold=0.5):
    """Return top-N similar items for a product_id with safe fallbacks.

    If CF similarity is not available or the top score is below `threshold`,
    it falls back to popular items in the parent category.
    """
    # Lazy initialization on first call
    if not _models['initialized']:
        _build_models()

    product_category_map = _models.get('product_category_map')
    item_similarity_df = _models.get('item_similarity_df')
    item_popularity = _models.get('item_popularity')

    product_cat_code = None
    if product_category_map is not None and product_id in product_category_map.index:
        product_cat_code = product_category_map.loc[product_id]['category_code']
    else:
        product_cat_code = "Unknown"

    LOG.info("Product ID: %s, Category Code: %s", product_id, product_cat_code)

    # If similarity matrix isn't ready, fallback to popularity in same category
    if item_similarity_df is None or product_id not in item_similarity_df.index:
        LOG.info("No CF similarity available for %s; using category/popularity fallback.", product_id)
        return _fallback_category_recommendation(product_id, n, product_cat_code, item_popularity, product_category_map)

    # Safe extraction of similarity scores
    try:
        similar_scores = item_similarity_df.loc[product_id]
        top_similar = similar_scores.sort_values(ascending=False)[1:n+1]
    except Exception:
        LOG.exception("Error extracting similarity scores; falling back")
        return _fallback_category_recommendation(product_id, n, product_cat_code, item_popularity, product_category_map)

    best_score = float(top_similar.iloc[0]) if not top_similar.empty else 0.0

    if best_score < threshold:
        LOG.info("Max similarity %s below threshold %s — using fallback", best_score, threshold)
        return _fallback_category_recommendation(product_id, n, product_cat_code, item_popularity, product_category_map)

    # Build result DataFrame
    result_df = pd.DataFrame(top_similar)
    result_df.columns = ['score']
    result_df['method'] = 'Item-Based CF'
    if product_category_map is not None:
        result_df = result_df.join(product_category_map)
    return result_df


def _fallback_category_recommendation(product_id, n, product_cat_code, item_popularity, product_category_map):
    parent_cat = get_parent_category(product_cat_code)
    if not parent_cat or product_category_map is None or item_popularity is None:
        LOG.warning("No parent category or popularity data available for fallback")
        return []

    mask = product_category_map['category_code'].str.startswith(parent_cat, na=False)
    candidate_products = product_category_map[mask].index
    candidate_products = candidate_products[candidate_products != product_id]
    valid_candidates = [p for p in candidate_products if p in item_popularity.index]

    if not valid_candidates:
        LOG.warning("No valid fallback candidates found in parent category %s", parent_cat)
        return []

    top_fallback = item_popularity.loc[valid_candidates].sort_values(ascending=False).head(n)
    result_df = pd.DataFrame(top_fallback)
    result_df.columns = ['score']
    result_df['method'] = 'Category Popularity (Fallback)'
    result_df = result_df.join(product_category_map)
    return result_df


if __name__ == "__main__":
    # Simple smoke test when run as script
    logging.basicConfig(level=logging.INFO)
    _build_models()
    print("Model initialization complete.")
    

