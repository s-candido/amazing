#!/usr/bin/env python3
"""
Customer Segmentation Clustering Pipeline
Processes all_events CSV data, trains multiple clustering models with fixed
best-known parameters, and saves predictions to PostgreSQL.

Usage:
    python clustering_pipeline.py --input /path/to/all_events.csv
"""

import argparse
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Machine Learning & Clustering
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, AgglomerativeClustering, Birch, DBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score,
    pairwise_distances_argmin_min
)

# Database
from sqlalchemy import create_engine

# Set random seeds for reproducibility
np.random.seed(42)


# ============================================================================
# CONFIGURATION
# ============================================================================

DB_CONFIG = {
    "host": "172.18.0.1",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
    "port": 5441,
}

RFM_CONFIG = {
    'r_column': 'months_since_last_event',
    'r_thresholds': [1, 5],
    'r_scores': [2, 1, 0],
    'f_column': 'total_purchases',
    'f_thresholds': [2, 10],
    'f_scores': [0, 1, 2],
    'm_column': 'total_spent',
    'm_thresholds': [20, 50],
    'm_scores': [0, 1, 2],
    'segment_thresholds': [0, 2, 3, 4, 6],
    'days_to_months': 30
}

FEATURE_COLUMNS = [
    "total_events",
    "total_views",
    "number_of_purchases",
    "total_spent",
    "avg_basket",
    "conversion_rate",
    "purchase_ratio",
    "days_since_last_event",
    "recency",
    "frequency",
    "monetary",
    "number_of_cart_additions",
    "unique_products",
    "unique_categories",
    "number_of_sessions",
    "avg_time_between_events"
]

N_CLUSTERS = 3
PCA_VARIANCE = 0.95
MAX_ROWS = 100_000
# Models with O(n²) memory complexity are fitted on a sample;
# remaining points are assigned to the nearest cluster centroid.
MAX_SAMPLE_SIZE = 50_000
# Agglomerative with non-ward linkage builds a full pairwise distance matrix
# (O(n²) memory). Keep this well below 20k to stay within RAM limits.
MAX_AGGLOMERATIVE_SAMPLE_SIZE = 10_000
# DBSCAN also builds a pairwise distance matrix for epsilon-neighborhoods.
MAX_DBSCAN_SAMPLE_SIZE = 20_000

BEST_PARAMS = {
    'Agglomerative': {'n_clusters': 3, 'linkage': 'average'},
    'Birch':         {'n_clusters': 3, 'threshold': 0.773389, 'branching_factor': 56},
    'DBSCAN':        {'eps': 3.539519, 'min_samples': 6},
    'GMM':           {'n_components': 4, 'covariance_type': 'tied'},
    'KMeans':        {'n_clusters': 3, 'n_init': 20},
}


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def create_db_engine():
    """Create SQLAlchemy database engine."""
    conn_str = (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    return create_engine(conn_str)


def save_to_postgresql(df, table_name, engine):
    """Save DataFrame to PostgreSQL."""
    try:
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        print(f"✓ Successfully saved {len(df)} rows to table '{table_name}'")
        return True
    except Exception as e:
        print(f"✗ Error saving to PostgreSQL: {e}")
        return False


# ============================================================================
# DATA LOADING & CLEANING
# ============================================================================

def load_csv_data(csv_path):
    """Load CSV data from file."""
    try:
        df = pd.read_csv(csv_path, nrows=MAX_ROWS)
        print(f"✓ Loaded CSV from: {csv_path}")
        print(f"  Shape: {df.shape} (limited to {MAX_ROWS:,} rows)")
        return df
    except Exception as e:
        print(f"✗ Error loading CSV: {e}")
        return None


def create_articles_column(df_clean):
    """Create articles column with list of (category_code, timecode) strings per user."""
    print("\n[CREATING ARTICLES COLUMN]")
    
    # Filter only valid rows with category_code and event_time
    df_articles_raw = df_clean[['user_id', 'category_code', 'event_time']].copy()
    df_articles_raw = df_articles_raw.dropna(subset=['category_code', 'event_time'])
    
    # Group by user_id and create list of (category_code, timecode) strings
    articles = df_articles_raw.groupby('user_id').apply(
        lambda group: [
            f"{row['category_code']}|{row['event_time'].isoformat()}"
            for _, row in group.iterrows()
        ]
    ).reset_index(name='articles')
    
    print(f"✓ Articles column created for {len(articles)} users")
    return articles


def clean_data(df):
    """Clean and preprocess raw data."""
    df_clean = df.copy()
    
    print("\n[CLEANING]")
    print(f"Initial shape: {df_clean.shape}")
    
    # Convert event_time to datetime
    if 'event_time' in df_clean.columns:
        df_clean['event_time'] = pd.to_datetime(df_clean['event_time'], errors='coerce')
    
    # Fill missing values
    if 'brand' in df_clean.columns:
        df_clean['brand'] = df_clean['brand'].fillna('unknown')
    if 'category_code' in df_clean.columns:
        df_clean['category_code'] = df_clean['category_code'].fillna('unknown')
    if 'category_id' in df_clean.columns:
        df_clean['category_id'] = df_clean['category_id'].fillna(-1)
    
    # Handle price anomalies
    if 'price' in df_clean.columns:
        initial_len = len(df_clean)
        df_clean = df_clean[df_clean['price'] > 0]
        
        Q1 = df_clean['price'].quantile(0.25)
        Q3 = df_clean['price'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 3 * IQR
        upper_bound = Q3 + 3 * IQR
        
        df_clean = df_clean[(df_clean['price'] >= lower_bound) & 
                           (df_clean['price'] <= upper_bound)]
    
    # Remove rows with missing values
    if 'event_time' in df_clean.columns and 'user_id' in df_clean.columns:
        df_clean = df_clean.dropna(subset=['event_time', 'user_id'])
    
    print(f"After cleaning: {df_clean.shape}")
    print(f"Data quality: {(len(df_clean) / len(df) * 100):.2f}% retained")
    
    return df_clean


# ============================================================================
# FEATURE ENGINEERING
# ============================================================================

def engineer_features(df_clean):
    """Create RFM and behavioral features."""
    print("\n[FEATURE ENGINEERING]")
    
    # Reference date
    reference_date = df_clean['event_time'].max()
    print(f"Reference date: {reference_date}")
    
    # Aggregate by user_id
    df_events = df_clean.groupby('user_id').agg({
        'event_type': 'count',
        'event_time': ['min', 'max'],
        'product_id': 'nunique',
        'category_id': 'nunique',
        'price': ['sum', 'mean'],
        'user_session': 'nunique'
    }).reset_index()
    
    # Flatten column names
    df_events.columns = ['user_id', 'total_events', 'first_event_time', 'last_event_time',
                        'unique_products', 'unique_categories', 'total_spent', 'avg_price_per_event',
                        'number_of_sessions']
    
    # Calculate time-based features
    df_events['days_since_last_event'] = (reference_date - df_events['last_event_time']).dt.days
    df_events['months_since_last_event'] = df_events['days_since_last_event'] / RFM_CONFIG['days_to_months']
    
    # RFM Features
    df_events['recency'] = df_events['days_since_last_event']
    df_events['frequency'] = df_events['total_events']
    df_events['monetary'] = df_events['total_spent']
    
    # Time features
    df_events['days_since_first_event'] = (reference_date - df_events['first_event_time']).dt.days
    df_events['avg_time_between_events'] = (
        df_events['days_since_first_event'] / (df_events['frequency'].clip(lower=2))
    )
    
    # Revenue features
    df_events['avg_basket'] = df_events['total_spent'] / (df_events['frequency'].clip(lower=1))
    
    # Event-type specific features
    df_view = df_clean[df_clean['event_type'] == 'view'].groupby('user_id').size().reset_index(name='total_views')
    df_cart = df_clean[df_clean['event_type'] == 'cart'].groupby('user_id').size().reset_index(name='number_of_cart_additions')
    df_purchase = df_clean[df_clean['event_type'] == 'purchase'].groupby('user_id').size().reset_index(name='number_of_purchases')
    
    df_events = df_events.merge(df_view, on='user_id', how='left').fillna(0)
    df_events = df_events.merge(df_cart, on='user_id', how='left').fillna(0)
    df_events = df_events.merge(df_purchase, on='user_id', how='left').fillna(0)
    
    # Conversion metrics
    df_events['conversion_rate'] = df_events['number_of_purchases'] / (df_events['total_views'].clip(lower=1))
    df_events['purchase_ratio'] = df_events['number_of_purchases'] / (df_events['total_events'].clip(lower=1))
    df_events['cart_ratio'] = df_events['number_of_cart_additions'] / (df_events['total_views'].clip(lower=1))
    
    print(f"✓ Feature engineering complete: {df_events.shape[0]:,} unique users")
    
    return df_events


# ============================================================================
# FEATURE SCALING & PCA
# ============================================================================

def prepare_features(df_events):
    """Scale and apply PCA to features."""
    print("\n[FEATURE PREPARATION]")
    
    X = df_events[FEATURE_COLUMNS].copy()
    
    # Handle missing values
    X = X.dropna()
    X = X.replace([np.inf, -np.inf], np.nan).dropna()
    print(f"Rows after cleaning: {len(X)}")
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled = pd.DataFrame(X_scaled, columns=FEATURE_COLUMNS, index=X.index)
    
    # Apply PCA
    pca = PCA(n_components=PCA_VARIANCE)
    X_pca = pca.fit_transform(X_scaled)
    
    print(f"✓ Scaling and PCA complete")
    print(f"  Original features: {X_scaled.shape[1]}")
    print(f"  PCA components: {X_pca.shape[1]}")
    print(f"  Variance explained: {pca.explained_variance_ratio_.sum():.4f}")
    
    return X, X_scaled, X_pca, pca, scaler



# ============================================================================
# CLUSTERING
# ============================================================================

def _assign_by_nearest_centroid(X_full, sample_idx, sample_labels):
    """Compute cluster centroids from a sample and assign all points by nearest centroid."""
    unique_labels = sorted(set(sample_labels) - {-1})
    centroids = np.array([
        X_full[sample_idx][sample_labels == lbl].mean(axis=0)
        for lbl in unique_labels
    ])
    assigned, _ = pairwise_distances_argmin_min(X_full, centroids)
    return np.array(unique_labels)[assigned]


def train_model(model_name, X_pca, params):
    """Train a clustering model by name with the given parameters.

    Models with O(n²) memory complexity (Agglomerative, DBSCAN) are fitted on
    a random sample of at most MAX_SAMPLE_SIZE rows; remaining points are then
    assigned to the nearest cluster centroid.
    """
    print(f"\n[{model_name.upper()} CLUSTERING]")
    n_rows = X_pca.shape[0]

    # Agglomerative: pairwise distance matrix is O(n²) memory — use a small sample
    if model_name == 'Agglomerative' and n_rows > MAX_AGGLOMERATIVE_SAMPLE_SIZE:
        rng = np.random.default_rng(42)
        sample_idx = rng.choice(n_rows, size=MAX_AGGLOMERATIVE_SAMPLE_SIZE, replace=False)
        X_sample = X_pca[sample_idx]
        print(f"  (sampling {MAX_AGGLOMERATIVE_SAMPLE_SIZE:,} / {n_rows:,} rows for Agglomerative)")
        model = AgglomerativeClustering(**params)
        sample_labels = model.fit_predict(X_sample)
        labels = _assign_by_nearest_centroid(X_pca, sample_idx, sample_labels)

    # DBSCAN: also O(n²) but handled separately with the larger sample limit
    elif model_name == 'DBSCAN' and n_rows > MAX_DBSCAN_SAMPLE_SIZE:
        rng = np.random.default_rng(42)
        sample_idx = rng.choice(n_rows, size=MAX_DBSCAN_SAMPLE_SIZE, replace=False)
        X_sample = X_pca[sample_idx]
        print(f"  (sampling {MAX_DBSCAN_SAMPLE_SIZE:,} / {n_rows:,} rows for DBSCAN)")
        model = DBSCAN(**params)
        sample_labels = model.fit_predict(X_sample)
        labels = _assign_by_nearest_centroid(X_pca, sample_idx, sample_labels)

    elif model_name == 'KMeans':
        model = KMeans(random_state=42, **params)
        labels = model.fit_predict(X_pca)
    elif model_name == 'Agglomerative':
        model = AgglomerativeClustering(**params)
        labels = model.fit_predict(X_pca)
    elif model_name == 'Birch':
        model = Birch(**params)
        labels = model.fit_predict(X_pca)
    elif model_name == 'DBSCAN':
        model = DBSCAN(**params)
        labels = model.fit_predict(X_pca)
    elif model_name == 'GMM':
        model = GaussianMixture(random_state=42, **params)
        labels = model.fit_predict(X_pca)
    else:
        raise ValueError(f"Unknown model: {model_name}")

    n_unique = len(set(labels) - {-1})
    print(f"✓ {model_name} training complete with {n_unique} clusters")

    return model, labels


# ============================================================================
# EVALUATION METRICS
# ============================================================================

def evaluate_clustering(X_pca, labels):
    """Calculate clustering evaluation metrics.

    silhouette_score also computes pairwise distances so it is evaluated on a
    sample when the dataset exceeds MAX_SAMPLE_SIZE.
    """
    print(f"\n[EVALUATION METRICS]")

    n_rows = X_pca.shape[0]
    n_clusters = len(set(labels) - {-1})

    if n_rows > MAX_SAMPLE_SIZE:
        rng = np.random.default_rng(42)
        idx = rng.choice(n_rows, size=MAX_SAMPLE_SIZE, replace=False)
        X_sil, lbl_sil = X_pca[idx], np.array(labels)[idx]
        print(f"  (silhouette sampled on {MAX_SAMPLE_SIZE:,} rows)")
    else:
        X_sil, lbl_sil = X_pca, labels

    sil_score = silhouette_score(X_sil, lbl_sil)
    db_index = davies_bouldin_score(X_pca, labels)
    ch_score = calinski_harabasz_score(X_pca, labels)
    
    metrics = {
        'Silhouette Score': float(sil_score),
        'Davies-Bouldin Index': float(db_index),
        'Calinski-Harabasz Score': float(ch_score),
        'N Clusters': int(n_clusters)
    }
    
    print(f"  Silhouette Score: {sil_score:.4f}")
    print(f"  Davies-Bouldin Index: {db_index:.4f}")
    print(f"  Calinski-Harabasz Score: {ch_score:.2f}")
    print(f"  Number of Clusters: {n_clusters}")
    
    return metrics


# ============================================================================
# RFM LABELING
# ============================================================================

def assign_rfm_labels_to_segments(df_with_clusters):
    """Assign RFM segment labels based on CLUSTER-LEVEL aggregate RFM characteristics.
    
    This function first aggregates RFM metrics (M, F, R, C) by cluster, then assigns
    segment labels to each cluster based on the cluster's aggregate characteristics.
    Finally, it propagates cluster-level labels back to individual users.

    Priority order for segment labels (first match wins):
      1. HIGH VALUE CUSTOMERS  : M̄_cluster > 1.5×M̄_global  AND  F̄_cluster > 1.5×F̄_global
      2. AT-RISK CUSTOMERS     : M̄_cluster < 0.5×M̄_global  AND  R̄_cluster > 1.5×R̄_global
      3. WINDOW SHOPPERS       : F̄_cluster > 1.5×F̄_global  AND  C̄_cluster < 0.5×C̄_global
      4. LOYAL BUYERS          : M̄_cluster > 1.0×M̄_global  AND  C̄_cluster > 1.5×C̄_global
      5. OCCASIONAL BUYERS     : F̄_cluster < 0.5×F̄_global
      default                  : OTHER
    """
    # Global dataset statistics
    M_global = df_with_clusters['total_spent'].mean()
    F_global = df_with_clusters['number_of_purchases'].mean()
    R_global = df_with_clusters['months_since_last_event'].mean()
    C_global = df_with_clusters['conversion_rate'].mean()

    # Aggregate RFM metrics per cluster
    cluster_rfm = df_with_clusters.groupby('cluster').agg({
        'total_spent': 'mean',
        'number_of_purchases': 'mean',
        'months_since_last_event': 'mean',
        'conversion_rate': 'mean'
    }).reset_index()

    # Rename for clarity
    cluster_rfm.columns = ['cluster', 'M_cluster', 'F_cluster', 'R_cluster', 'C_cluster']

    # Assign RFM labels to each cluster
    segment_labels_list = []
    for _, row in cluster_rfm.iterrows():
        M_c, F_c, R_c, C_c = row['M_cluster'], row['F_cluster'], row['R_cluster'], row['C_cluster']
        
        if (M_c > 1.5 * M_global) and (F_c > 1.5 * F_global):
            label = 'HIGH VALUE CUSTOMERS'
        elif (M_c < 0.5 * M_global) and (R_c > 1.5 * R_global):
            label = 'AT-RISK CUSTOMERS'
        elif (F_c > 1.5 * F_global) and (C_c < 0.5 * C_global):
            label = 'WINDOW SHOPPERS'
        elif (M_c > 1.0 * M_global) and (C_c > 1.5 * C_global):
            label = 'LOYAL BUYERS'
        elif F_c < 0.5 * F_global:
            label = 'OCCASIONAL BUYERS'
        else:
            label = 'OTHER'
        
        segment_labels_list.append(label)

    cluster_rfm['rfm_label'] = segment_labels_list

    # Create a mapping from cluster ID to RFM label
    cluster_to_label = dict(zip(cluster_rfm['cluster'], cluster_rfm['rfm_label']))

    # Apply cluster-level labels to each user
    return df_with_clusters['cluster'].map(cluster_to_label)


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Customer Segmentation Clustering Pipeline'
    )
    parser.add_argument('--input', type=str, required=True,
                       help='Path to input CSV file (all_events data)')
    
    args = parser.parse_args()
    csv_path = args.input
    
    if not Path(csv_path).exists():
        print(f"✗ File not found: {csv_path}")
        return False
    
    # Extract filename for outputs
    csv_filename = Path(csv_path).stem
    
    print("=" * 80)
    print(f"CLUSTERING PIPELINE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # ---- Load Data ----
    df_raw = load_csv_data(csv_path)
    if df_raw is None or df_raw.empty:
        return False
    
    # ---- Clean Data ----
    df_clean = clean_data(df_raw)
    
    # ---- Feature Engineering ----
    df_events = engineer_features(df_clean)
    
    # ---- Create articles column ----
    df_articles = create_articles_column(df_clean)
    
    # ---- Prepare Features (Scale & PCA) ----
    X, X_scaled, X_pca, pca, scaler = prepare_features(df_events)

    # ---- Train all models with fixed best parameters ----
    all_results = {}
    print(f"\n[TRAINING ALL MODELS]")

    try:
        engine = create_db_engine()
    except Exception as e:
        print(f"✗ Database connection error: {e}")
        return False

    for model_name, params in BEST_PARAMS.items():
        model, labels = train_model(model_name, X_pca, params)
        metrics = evaluate_clustering(X_pca, labels)
        all_results[model_name] = {'params': params, 'metrics': metrics}

        # Add cluster labels to dataframe
        df_results = df_events.copy()
        df_results['cluster'] = -1
        df_results.loc[X.index, 'cluster'] = labels
        df_results['rfm_label'] = assign_rfm_labels_to_segments(df_results)

        # Save to PostgreSQL
        print(f"\n[DATABASE - {model_name}]")
        # Include all feature columns plus clustering/RFM labels
        feature_and_label_cols = FEATURE_COLUMNS + ['cluster', 'rfm_label', 'user_id']
        df_segments = df_results[feature_and_label_cols].copy()
        # Merge with articles column
        df_segments = df_segments.merge(df_articles, on='user_id', how='left')
        df_segments.columns = [col if col != 'cluster' else 'segment' for col in df_segments.columns]
        df_segments.rename(columns={'rfm_label': 'label'}, inplace=True)
        df_segments['segment'] = df_segments['segment'].astype(int)
        df_segments['csv_file'] = csv_filename
        df_segments['model'] = model_name
        df_segments['processed_at'] = datetime.now()

        table_name = f"user_segment_{csv_filename}_{model_name.lower()}"
        save_to_postgresql(df_segments, table_name, engine)

    # ---- Save JSON results ----
    print(f"\n[RESULTS]")
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'csv_file': csv_filename,
        'csv_path': str(csv_path),
        'total_records': len(df_raw),
        'records_after_cleaning': len(df_clean),
        'unique_users': len(df_events),
        'users_in_clustering': len(X),
        'best_params': BEST_PARAMS,
        'results': all_results,
        'pca_info': {
            'n_components': int(X_pca.shape[1]),
            'variance_explained': float(pca.explained_variance_ratio_.sum())
        }
    }

    json_output_path = Path(csv_path).parent / f"clustering_results_{csv_filename}.json"
    with open(json_output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f"✓ Results saved to: {json_output_path}")

    print("\n" + "=" * 80)
    print(f"PIPELINE COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    print(f"\nSummary:")
    print(f"  CSV File: {csv_filename}")
    print(f"  Users Clustered: {len(X)}")
    for model_name, res in all_results.items():
        print(f"  [{model_name}] Silhouette: {res['metrics']['Silhouette Score']:.4f} "
              f"| Clusters: {res['metrics']['N Clusters']}")
    print(f"  Results JSON: {json_output_path}")

    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
