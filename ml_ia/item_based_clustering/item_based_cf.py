import duckdb
import pandas as pd
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os

DB_NAME = Path("amazing.duckdb")

if not DB_NAME.exists():
    DB_NAME = Path("../../amazing.duckdb")

def get_cf_matrix(limit=100):
    """
    Connect to database and retrieve the collaborative filtering matrix.
    Limits the result to avoid memory crashes.
    """
    try:
        con = duckdb.connect(str(DB_NAME), read_only=True)
        print(f"Connected to database at: {DB_NAME}")

        cf_matrix = con.sql(f"""
            SELECT *
            FROM cf_matrix
            LIMIT {limit}
        """)
        
        cf_matrix_df = cf_matrix.df()
        con.close()
        
        return cf_matrix_df
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def recommandation_system(product_id, n=5, threshold=0.5):
    """
    Recommends similar products based on item-based collaborative filtering.
    
    Args:
        product_id (int or str): The ID of the product to find recommendations for.
        n (int): Number of recommendations to return.
        threshold (float): Minimum similarity score threshold.
        
    Returns:
        list: List of tuples (product_id, score) containing similar products.
    """
    df = get_cf_matrix()
    
    if df is None or df.empty:
        return []

    if 'product_id' in df.columns:
        df = df.set_index('product_id')
    
    if product_id not in df.index:
        print(f"Product ID {product_id} not found in the loaded matrix subset.")
        return []

    target_product_vector = df.loc[product_id].values.reshape(1, -1)
    similarity_scores = cosine_similarity(df.values, target_product_vector).flatten()
    
    sim_series = pd.Series(similarity_scores, index=df.index)
    
    sim_series = sim_series.drop(product_id)
    sim_series = sim_series[sim_series >= threshold]
    
    top_recommendations = sim_series.sort_values(ascending=False).head(n)
    
    result = list(zip(top_recommendations.index, top_recommendations.values))
    
    return result

if __name__ == "__main__":
    print("Testing recommendation system...")
    
    try:
        con = duckdb.connect(str(DB_NAME), read_only=True)
        sample_id = con.sql("SELECT product_id FROM cf_matrix LIMIT 1").fetchone()
        con.close()
        
        if sample_id:
            test_id = sample_id[0]
            print(f"Testing with Product ID: {test_id}")
            recommendations = recommandation_system(test_id, n=5, threshold=0.1)
            
            print(f"Recommendations for product {test_id}:")
            for pid, score in recommendations:
                print(f"Product: {pid}, Similarity: {score:.4f}")
        else:
            print("No products found in cf_matrix table.")
            
    except Exception as e:
        print(f"Error in main block: {e}")
