#!/usr/bin/env python3
"""
RFM Score Recalculation Script

This script repairs user segment tables and recalculates RFM (Recency, Frequency, Monetary) scores
based on a configurable RFM scoring system. It then updates the database with the new scores.

RFM Scoring Logic:
- Recency (R): Based on days since last event. Lower is better (more recent).
- Frequency (F): Based on number of purchases/transactions. Higher is better.
- Monetary (M): Based on total spent. Higher is better.
- Segment: Calculated from R + F + M score sum.

Usage:
    python repair_and_recalculate_rfm.py [--table TABLE_NAME] [--dry-run] [--help]
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import argparse

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.sql import sqltypes

# ==================== Configuration ====================

# Database Configuration
DB_CONFIG = {
    "host": "172.18.0.1",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
    "port": 5441,
}

# RFM Configuration
RFM_CONFIG = {
    'r_column': 'days_since_last_event',
    'r_thresholds': [30, 150],  # days
    'r_scores': [2, 1, 0],  # scores: [more recent, recent, old]
    'f_column': 'total_purchases',  # or 'frequency' or 'number_of_purchases'
    'f_thresholds': [2, 10],  # number of purchases
    'f_scores': [0, 1, 2],  # scores: [low, medium, high]
    'm_column': 'total_spent',  # monetary
    'm_thresholds': [20, 50],  # amount spent
    'm_scores': [0, 1, 2],  # scores: [low, medium, high]
    'segment_thresholds': [0, 2, 3, 4, 6],  # segment boundaries
    'days_to_months': 30
}

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== Helper Functions ====================

def get_db_engine(config: Dict) -> object:
    """Create SQLAlchemy database engine."""
    try:
        engine = create_engine(
            f"postgresql+psycopg2://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✓ Database connection successful")
        return engine
    except Exception as e:
        logger.error(f"✗ Failed to connect to database: {e}")
        raise

def get_user_segment_tables(engine: object, table_pattern: Optional[str] = None) -> List[str]:
    """
    Fetch all tables matching the pattern (default: 'user_segment_*').
    """
    try:
        inspector = inspect(engine)
        all_tables = inspector.get_table_names()
        
        if table_pattern:
            filtered_tables = [t for t in all_tables if table_pattern in t]
        else:
            filtered_tables = [t for t in all_tables if t.startswith('user_segment_')]
        
        logger.info(f"✓ Found {len(filtered_tables)} user_segment tables")
        return sorted(filtered_tables)
    except Exception as e:
        logger.error(f"✗ Error fetching tables: {e}")
        raise

def load_table(engine: object, table_name: str) -> pd.DataFrame:
    """Load table data into a DataFrame."""
    try:
        query = f'SELECT * FROM "{table_name}"'
        df = pd.read_sql(query, engine)
        logger.info(f"✓ Loaded {len(df)} rows from {table_name}")
        return df
    except Exception as e:
        logger.error(f"✗ Error loading {table_name}: {e}")
        raise

def calculate_r_score(days_since_event: float, thresholds: List[int], scores: List[int]) -> int:
    """
    Calculate Recency score.
    Lower days_since_last_event = higher recency score (more recent customer).
    
    Args:
        days_since_event: Number of days since last event
        thresholds: [30, 150] - breakpoints for scoring
        scores: [2, 1, 0] - scores for each boundary
    
    Returns:
        Recency score (0, 1, or 2)
    
    Logic:
    - If days <= 30: score = 2 (very recent)
    - If 30 < days <= 150: score = 1 (somewhat recent)
    - If days > 150: score = 0 (not recent)
    """
    if pd.isna(days_since_event):
        return 0
    
    days = float(days_since_event)
    if days <= thresholds[0]:
        return scores[0]  # 2 - most recent
    elif days <= thresholds[1]:
        return scores[1]  # 1 - somewhat recent
    else:
        return scores[2]  # 0 - not recent

def calculate_f_score(frequency: float, thresholds: List[int], scores: List[int]) -> int:
    """
    Calculate Frequency score.
    Higher frequency = higher score (more purchases).
    
    Args:
        frequency: Number of purchases/transactions
        thresholds: [2, 10] - breakpoints for scoring
        scores: [0, 1, 2] - scores for each boundary
    
    Returns:
        Frequency score (0, 1, or 2)
    
    Logic:
    - If frequency < 2: score = 0 (low frequency)
    - If 2 <= frequency < 10: score = 1 (medium frequency)
    - If frequency >= 10: score = 2 (high frequency)
    """
    if pd.isna(frequency):
        return 0
    
    freq = float(frequency)
    if freq < thresholds[0]:
        return scores[0]  # 0 - low frequency
    elif freq < thresholds[1]:
        return scores[1]  # 1 - medium frequency
    else:
        return scores[2]  # 2 - high frequency

def calculate_m_score(monetary: float, thresholds: List[float], scores: List[int]) -> int:
    """
    Calculate Monetary score.
    Higher monetary value = higher score (higher spending).
    
    Args:
        monetary: Total amount spent
        thresholds: [20, 50] - breakpoints for scoring
        scores: [0, 1, 2] - scores for each boundary
    
    Returns:
        Monetary score (0, 1, or 2)
    
    Logic:
    - If monetary < 20: score = 0 (low spending)
    - If 20 <= monetary < 50: score = 1 (medium spending)
    - If monetary >= 50: score = 2 (high spending)
    """
    if pd.isna(monetary):
        return 0
    
    amount = float(monetary)
    if amount < thresholds[0]:
        return scores[0]  # 0 - low spending
    elif amount < thresholds[1]:
        return scores[1]  # 1 - medium spending
    else:
        return scores[2]  # 2 - high spending

def calculate_segment(r_score: int, f_score: int, m_score: int, thresholds: List[int]) -> int:
    """
    Calculate segment based on RFM score sum.
    
    Args:
        r_score, f_score, m_score: Individual RFM scores (0-2)
        thresholds: [0, 2, 3, 4, 6] - segment boundaries
        
    Returns:
        Segment number (0-4 or custom based on thresholds)
    
    Scoring:
    - Sum of R + F + M = 0-6
    - Segments: 
      - 0: sum in [0, 2)
      - 1: sum in [2, 3)
      - 2: sum in [3, 4)
      - 3: sum in [4, 6)
      - 4: sum >= 6
    """
    total_score = r_score + f_score + m_score
    
    # Find which segment based on thresholds
    for i in range(len(thresholds) - 1):
        if thresholds[i] <= total_score < thresholds[i + 1]:
            return i
    
    # Default to last segment if score >= last threshold
    return len(thresholds) - 2

def repair_and_calculate_rfm(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """
    Main RFM calculation function.
    
    Calculates recency, frequency, and monetary scores, then updates the dataframe.
    """
    logger.info(f"\nProcessing {len(df)} records...")
    
    # Get column names (handle variations)
    r_col = config['r_column']
    f_col = config['f_column']
    m_col = config['m_column']
    
    # Find actual columns (case-insensitive or with variations)
    available_cols = {col.lower(): col for col in df.columns}
    
    # Map to actual columns in dataframe
    actual_r_col = available_cols.get(r_col.lower(), r_col)
    actual_f_col = None
    actual_m_col = available_cols.get(m_col.lower(), m_col)
    
    # Try to find frequency column
    possible_f_cols = ['total_purchases', 'frequency', 'number_of_purchases', 'nb_purchases']
    for col in possible_f_cols:
        if col.lower() in available_cols:
            actual_f_col = available_cols[col.lower()]
            break
    
    if actual_f_col is None:
        actual_f_col = config['f_column']
    
    logger.info(f"  Recency column: {actual_r_col}")
    logger.info(f"  Frequency column: {actual_f_col}")
    logger.info(f"  Monetary column: {actual_m_col}")
    
    # Validate columns exist
    missing_cols = []
    for col in [actual_r_col, actual_f_col, actual_m_col]:
        if col not in df.columns:
            missing_cols.append(col)
    
    if missing_cols:
        logger.warning(f"  ⚠ Missing columns: {missing_cols}")
        logger.warning(f"  Available columns: {list(df.columns)}")
    
    # Calculate RFM scores
    df['recency'] = df[actual_r_col].apply(
        lambda x: calculate_r_score(x, config['r_thresholds'], config['r_scores'])
    )
    
    df['frequency'] = df[actual_f_col].apply(
        lambda x: calculate_f_score(x, config['f_thresholds'], config['f_scores'])
    )
    
    df['monetary'] = df[actual_m_col].apply(
        lambda x: calculate_m_score(x, config['m_thresholds'], config['m_scores'])
    )
    
    # Calculate segment from RFM scores
    df['segment'] = df.apply(
        lambda row: calculate_segment(
            row['recency'], row['frequency'], row['monetary'],
            config['segment_thresholds']
        ),
        axis=1
    )
    
    # Update processed_at timestamp
    df['processed_at'] = datetime.now()
    
    logger.info(f"  ✓ RFM scores calculated")
    logger.info(f"    - Recency distribution: {df['recency'].value_counts().to_dict()}")
    logger.info(f"    - Frequency distribution: {df['frequency'].value_counts().to_dict()}")
    logger.info(f"    - Monetary distribution: {df['monetary'].value_counts().to_dict()}")
    logger.info(f"    - Segment distribution: {df['segment'].value_counts().to_dict()}")
    
    return df

def update_table(engine: object, table_name: str, df: pd.DataFrame, dry_run: bool = False) -> bool:
    """
    Update the table in the database with recalculated RFM scores.
    """
    try:
        if dry_run:
            logger.info(f"  [DRY RUN] Would update {len(df)} rows in {table_name}")
            logger.info(f"  Sample of new data:")
            sample_cols = ['user_id', 'recency', 'frequency', 'monetary', 'segment', 'processed_at']
            available_cols = [c for c in sample_cols if c in df.columns]
            logger.info(f"\n{df[available_cols].head().to_string()}\n")
            return True
        else:
            # Replace the entire table with updated data
            df.to_sql(table_name, engine, if_exists='replace', index=False)
            logger.info(f"  ✓ Updated {len(df)} rows in {table_name}")
            return True
    except Exception as e:
        logger.error(f"  ✗ Error updating {table_name}: {e}")
        return False

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Repair and recalculate RFM scores for user segment tables',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update all user_segment_* tables
  python repair_and_recalculate_rfm.py
  
  # Update a specific table (dry run)
  python repair_and_recalculate_rfm.py --table user_segment_agglomerative --dry-run
  
  # Update tables matching a pattern
  python repair_and_recalculate_rfm.py --pattern Agglomerative
        """
    )
    
    parser.add_argument(
        '--table',
        type=str,
        help='Specific table name to update (if not provided, updates all user_segment_* tables)'
    )
    parser.add_argument(
        '--pattern',
        type=str,
        help='Pattern to match table names'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without updating the database'
    )
    
    args = parser.parse_args()
    
    # Welcome message
    logger.info("=" * 70)
    logger.info("RFM Score Recalculation Tool")
    logger.info("=" * 70)
    logger.info(f"RFM Configuration:")
    logger.info(f"  Recency: {RFM_CONFIG['r_column']} <= {RFM_CONFIG['r_thresholds'][0]} (score 2), "
                f"<= {RFM_CONFIG['r_thresholds'][1]} (score 1), > {RFM_CONFIG['r_thresholds'][1]} (score 0)")
    logger.info(f"  Frequency: {RFM_CONFIG['f_column']} < {RFM_CONFIG['f_thresholds'][0]} (score 0), "
                f"< {RFM_CONFIG['f_thresholds'][1]} (score 1), >= {RFM_CONFIG['f_thresholds'][1]} (score 2)")
    logger.info(f"  Monetary: {RFM_CONFIG['m_column']} < {RFM_CONFIG['m_thresholds'][0]} (score 0), "
                f"< {RFM_CONFIG['m_thresholds'][1]} (score 1), >= {RFM_CONFIG['m_thresholds'][1]} (score 2)")
    logger.info("=" * 70)
    
    if args.dry_run:
        logger.warning("⚠ DRY RUN MODE - No changes will be made to the database")
    
    try:
        # Connect to database
        engine = get_db_engine(DB_CONFIG)
        
        # Get tables to process
        if args.table:
            tables = [args.table]
        else:
            tables = get_user_segment_tables(engine, args.pattern)
        
        if not tables:
            logger.warning("No tables found matching the criteria")
            return 1
        
        # Process each table
        success_count = 0
        for table_name in tables:
            logger.info(f"\n► Processing table: {table_name}")
            
            try:
                # Load data
                df = load_table(engine, table_name)
                
                # Calculate RFM
                df = repair_and_calculate_rfm(df, RFM_CONFIG)
                
                # Update database
                if update_table(engine, table_name, df, dry_run=args.dry_run):
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"✗ Failed to process {table_name}: {e}")
                continue
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info(f"Processing Complete: {success_count}/{len(tables)} tables successfully updated")
        logger.info("=" * 70)
        
        return 0 if success_count == len(tables) else 1
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
