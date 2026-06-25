#!/usr/bin/env python3
"""
Simple RFM Repair Script
Recalculates RFM scores and updates a PostgreSQL table.

Usage:
    python rfm_repair.py user_segment_agglomerative
    python rfm_repair.py user_segment_kmeans
"""

import sys
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

# Database config
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
    'r_thresholds': [30, 150],
    'r_scores': [2, 1, 0],
    'f_column': 'number_of_purchases',
    'f_thresholds': [2, 10],
    'f_scores': [0, 1, 2],
    'm_column': 'total_spent',
    'm_thresholds': [20, 50],
    'm_scores': [0, 1, 2],
    'segment_thresholds': [0, 2, 3, 4, 6],
}

def calculate_r_score(days, thresholds, scores):
    if pd.isna(days):
        return 0
    days = float(days)
    if days <= thresholds[0]:
        return scores[0]
    elif days <= thresholds[1]:
        return scores[1]
    else:
        return scores[2]

def calculate_f_score(freq, thresholds, scores):
    if pd.isna(freq):
        return 0
    freq = float(freq)
    if freq < thresholds[0]:
        return scores[0]
    elif freq < thresholds[1]:
        return scores[1]
    else:
        return scores[2]

def calculate_m_score(monetary, thresholds, scores):
    if pd.isna(monetary):
        return 0
    amount = float(monetary)
    if amount < thresholds[0]:
        return scores[0]
    elif amount < thresholds[1]:
        return scores[1]
    else:
        return scores[2]

def calculate_segment(r, f, m, thresholds):
    total = r + f + m
    for i in range(len(thresholds) - 1):
        if thresholds[i] <= total < thresholds[i + 1]:
            return i
    return len(thresholds) - 2

def main():
    if len(sys.argv) != 2:
        print("Usage: python rfm_repair.py TABLE_NAME")
        print("Example: python rfm_repair.py user_segment_agglomerative")
        sys.exit(1)
    
    table_name = sys.argv[1]
    
    print(f"🔄 Repairing RFM for table: {table_name}")
    
    try:
        # Connect to database
        engine = create_engine(
            f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
            f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        )
        
        # Load data
        print(f"📥 Loading data from {table_name}...")
        df = pd.read_sql(f'SELECT * FROM "{table_name}"', engine)
        print(f"✓ Loaded {len(df)} rows")
        
        # Find columns
        r_col = RFM_CONFIG['r_column']
        f_col = RFM_CONFIG['f_column']
        m_col = RFM_CONFIG['m_column']
        
        # Check columns exist
        missing = []
        for col in [r_col, f_col, m_col]:
            if col not in df.columns:
                # Try case-insensitive
                found = [c for c in df.columns if c.lower() == col.lower()]
                if found:
                    if col == r_col:
                        r_col = found[0]
                    elif col == f_col:
                        f_col = found[0]
                    elif col == m_col:
                        m_col = found[0]
                else:
                    missing.append(col)
        
        if missing:
            print(f"✗ Missing columns: {missing}")
            print(f"Available: {list(df.columns)}")
            sys.exit(1)
        
        print(f"📊 Using columns: R={r_col}, F={f_col}, M={m_col}")
        
        # Calculate RFM scores
        print("🧮 Calculating RFM scores...")
        df['recency'] = df[r_col].apply(
            lambda x: calculate_r_score(x, RFM_CONFIG['r_thresholds'], RFM_CONFIG['r_scores'])
        )
        df['frequency'] = df[f_col].apply(
            lambda x: calculate_f_score(x, RFM_CONFIG['f_thresholds'], RFM_CONFIG['f_scores'])
        )
        df['monetary'] = df[m_col].apply(
            lambda x: calculate_m_score(x, RFM_CONFIG['m_thresholds'], RFM_CONFIG['m_scores'])
        )
        df['segment'] = df.apply(
            lambda row: calculate_segment(
                row['recency'], row['frequency'], row['monetary'],
                RFM_CONFIG['segment_thresholds']
            ),
            axis=1
        )
        df['processed_at'] = datetime.now()
        
        # Show distribution
        print(f"\n📈 RFM Distribution:")
        print(f"  Recency: {dict(df['recency'].value_counts().sort_index())}")
        print(f"  Frequency: {dict(df['frequency'].value_counts().sort_index())}")
        print(f"  Monetary: {dict(df['monetary'].value_counts().sort_index())}")
        print(f"  Segment: {dict(df['segment'].value_counts().sort_index())}")
        
        # Update database
        print(f"\n💾 Updating {table_name} in database...")
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        
        print(f"✅ Done! Updated {len(df)} rows with RFM scores.")
        print(f"   Columns added: recency, frequency, monetary, segment, processed_at")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
