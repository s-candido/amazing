from pathlib import Path
import pandas as pd
import psycopg2
from datetime import datetime
import sys
import os
import glob
import shutil

from src.db.ingestion_postgre import ingest_postgres
from src.db.ingestion_weather import ingest_weather
from src.ingestion.downloader import download_and_extract

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data.data_loader import load_all_data
from src.db.ingestion_clean_data import *
from src.data.weather_loader import *



DB_CONFIG = {
    "host": "amazing_postgresql",
    "database": "postgres", 
    "user": "postgres",
    "password": "postgres",
    "port": 5432
}

WEATHER_TABLE_NAME = "weather_data"
FEATURES_TABLE_NAME = "features_data"
DATA_DIR = "/opt/airflow/dags/src/data_folder"

def cleanup_data_files(data_dir=DATA_DIR):
    """
    Delete all downloaded data files from the data directory after successful DB insertion.
    """
    print(f"Cleaning up data files in {data_dir}")
    
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"Data directory {data_dir} does not exist, nothing to clean")
        return
    
    # List all supported files
    supported_extensions = [".csv", ".xls", ".xlsx"]
    deleted_count = 0
    total_size_freed = 0
    
    try:
        for file in data_path.iterdir():
            if file.suffix.lower() in supported_extensions:
                file_size = file.stat().st_size
                file.unlink()
                deleted_count += 1
                total_size_freed += file_size
                print(f"Deleted: {file.name}")
        
        # Also try to delete any .zip files that might remain
        for file in data_path.glob("*.zip"):
            file_size = file.stat().st_size
            file.unlink()
            deleted_count += 1
            total_size_freed += file_size
            print(f"Deleted: {file.name}")
            
        print(f"Cleanup completed: {deleted_count} files deleted, {total_size_freed / (1024*1024):.2f} MB freed")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        raise

def run_full_pipeline(start_date="2020-01-01", end_date="2020-12-31", data_dir=DATA_DIR, cleanup=True):
    print("Starting full data pipeline...")
    
    try:
        extracted_files= download_and_extract(start_year=2012, target_dir=data_dir)
        extracted_files_count = len(extracted_files)
        print(f"Extracted {extracted_files_count} files.")
        for e in extracted_files:
            print(f"Extracted File: {e}")
        ingest_postgres()

        ingest_weather(2012, 2023)

        df = load_from_postgres()

        df = create_features(df)
        if cleanup:
            cleanup_data_files(data_dir)
        
        print("Pipeline completed successfully!")
        
    except Exception as e:
        print(f"Pipeline failed: {e}")
        # Don't cleanup if pipeline failed to ensure data is preserved for debugging
        raise

if __name__ == "__main__":
    run_full_pipeline(
        start_date="2020-01-01",
        end_date="2020-12-31",
        data_dir=DATA_DIR
    )