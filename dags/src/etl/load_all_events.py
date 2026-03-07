"""
Load all events from CSV files in data folder into PostgreSQL database.

This module provides the load_all_events function that:
1. Scans data folder for CSV files
2. Loads new CSV files into the all_events table
3. Tracks loaded files to avoid duplicates
"""

import os
import psycopg2
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional


def get_file_paths(data_folder_path: str) -> List[str]:
    """Get sorted list of CSV file paths from data folder."""
    data_folder = Path(data_folder_path)
    return sorted([str(p.resolve()) for p in data_folder.glob("*.csv")])


def get_loaded_filenames(connection) -> set:
    """Get set of already loaded filenames from the database."""
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT filename FROM loaded_files")
        return {row[0] for row in cursor.fetchall()}
    except psycopg2.errors.UndefinedTable:
        # Table doesn't exist yet, return empty set
        return set()
    finally:
        cursor.close()


def init_tables(connection) -> None:
    """Initialize required tables in PostgreSQL."""
    cursor = connection.cursor()
    
    # Create all_events table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS all_events (
            event_time TIMESTAMP,
            event_type TEXT,
            product_id TEXT,
            category_id TEXT,
            category_code TEXT,
            brand TEXT,
            price DOUBLE PRECISION,
            user_id TEXT,
            user_session TEXT
        )
    """)
    
    # Create loaded_files table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loaded_files (
            filename TEXT PRIMARY KEY
        )
    """)
    
    connection.commit()
    cursor.close()


def load_csv_to_database(
    connection,
    file_path: str,
    loaded_filenames: set
) -> bool:
    """
    Load a CSV file into all_events table if not already loaded.
    
    Returns True if file was loaded, False if already exists.
    """
    filename = os.path.basename(file_path)
    
    if filename in loaded_filenames:
        print(f"{filename} already loaded. Skipped.")
        return False
    
    print(f"Loading {filename} into all_events...")
    
    df = pd.read_csv(file_path)
    
    column_mapping = {
        'event_time': 'event_time',
        'event_type': 'event_type', 
        'product_id': 'product_id',
        'category_id': 'category_id',
        'category_code': 'category_code',
        'brand': 'brand',
        'price': 'price',
        'user_id': 'user_id',
        'user_session': 'user_session'
    }
    
    df = df.rename(columns=column_mapping)
    columns = list(column_mapping.values())
    df = df[columns]
    
    cursor = connection.cursor()
    
    for _, row in df.iterrows():
        cursor.execute(
            """
            INSERT INTO all_events 
            (event_time, event_type, product_id, category_id, category_code, brand, price, user_id, user_session)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                row['event_time'],
                row['event_type'],
                str(row['product_id']) if pd.notna(row['product_id']) else None,
                str(row['category_id']) if pd.notna(row['category_id']) else None,
                row['category_code'] if pd.notna(row['category_code']) else None,
                row['brand'] if pd.notna(row['brand']) else None,
                float(row['price']) if pd.notna(row['price']) else None,
                str(row['user_id']) if pd.notna(row['user_id']) else None,
                row['user_session'] if pd.notna(row['user_session']) else None,
            )
        )
    
    cursor.execute("INSERT INTO loaded_files (filename) VALUES (%s)", (filename,))
    
    connection.commit()
    cursor.close()
    
    print(f"{filename} loaded successfully.")
    return True


def load_all_events(
    data_folder_path: str,
    output_table: str = "all_events",
    output_columns: Optional[List[str]] = None,
    target: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Load all CSV files from data folder into PostgreSQL database.
    
    This function is designed to be called by an Airflow DAG.
    
    Args:
        data_folder_path: Path to folder containing CSV files
        output_table: Name of the target table (default: all_events)
        output_columns: List of column names for output table
        target: Database configuration dictionary with keys:
            - host: Database host
            - database: Database name
            - user: Database user
            - password: Database password
            - port: Database port
    
    Returns:
        Dictionary with execution results:
            - files_found: Number of CSV files found
            - files_loaded: Number of new files loaded
            - status: 'success' or 'error'
    """
    
    if target is None:
        raise ValueError("target (DB_CONFIG) is required")
    
    print(f"Starting load process from: {data_folder_path}")
    print(f"Target database: {target.get('host')}/{target.get('database')}")
    
    # Connect to PostgreSQL
    connection = psycopg2.connect(
        host=target["host"],
        database=target["database"],
        user=target["user"],
        password=target["password"],
        port=target["port"]
    )
    
    try:
        # Initialize tables
        init_tables(connection)
        print("Database tables initialized.")
        
        # Get CSV files to load
        file_paths = get_file_paths(data_folder_path)
        print(f"Found {len(file_paths)} CSV file(s) in {data_folder_path}")
        
        if not file_paths:
            print("No CSV files found to load.")
            return {
                "files_found": 0,
                "files_loaded": 0,
                "status": "success"
            }
        
        # Get already loaded filenames
        loaded_filenames = get_loaded_filenames(connection)
        print(f"Already loaded: {len(loaded_filenames)} file(s)")
        
        # Load new files
        files_loaded = 0
        for file_path in file_paths:
            if load_csv_to_database(connection, file_path, loaded_filenames):
                files_loaded += 1
        
        print(f"\nLoad complete. {files_loaded} new file(s) loaded.")
        
        return {
            "files_found": len(file_paths),
            "files_loaded": files_loaded,
            "status": "success"
        }
        
    except Exception as e:
        connection.rollback()
        print(f"Error during load: {str(e)}")
        raise
    finally:
        connection.close()
        print("Database connection closed.")


if __name__ == "__main__":
    # For testing without Airflow
    test_config = {
        "host": "localhost",
        "database": "postgres",
        "user": "postgres", 
        "password": "postgres",
        "port": 5432
    }
    
    # Test with local path
    result = load_all_events(
        data_folder_path="/home/c-enjalbert/Documents/Github/MSPR/bloc_2/amazing_airflow/data",
        output_table="all_events",
        target=test_config
    )
    print(f"Result: {result}")
