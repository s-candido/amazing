import psycopg2
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime


def data_cleansing_and_preprocessing(
    source_table: str = "all_events",
    output_table: str = "user_events",
    output_columns: Optional[List[str]] = None,
    target: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if target is None:
        raise ValueError("target (DB_CONFIG) is required")
    
    print(f"Starting data preprocessing from {source_table} to {output_table}")
    print(f"Target database: {target.get('host')}/{target.get('database')}")
    
    connection = psycopg2.connect(
        host=target["host"],
        database=target["database"],
        user=target["user"],
        password=target["password"],
        port=target["port"]
    )
    
    try:
        query = f"""
        WITH base_events AS (
            SELECT
                user_id,
                event_type,
                event_time,
                price,
                LEAD(event_time) OVER (PARTITION BY user_id ORDER BY event_time) AS next_event_time
            FROM {source_table}
            WHERE user_id IS NOT NULL
        ),
        features AS (
            SELECT
                user_id,
                COUNT(*) AS total_events,
                SUM(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) AS total_views,
                SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS total_purchases,
                AVG(EXTRACT(EPOCH FROM (next_event_time - event_time))) AS avg_time_between_events,
                SUM(CASE WHEN event_type = 'purchase' THEN COALESCE(price, 0) ELSE 0 END) AS total_spent,
                COALESCE(AVG(CASE WHEN event_type = 'purchase' THEN price ELSE NULL END), 0) AS avg_basket,
                MAX(event_time) AS last_event_time
            FROM base_events
            GROUP BY user_id
        )
        SELECT
            user_id,
            total_events,
            total_views,
            total_purchases,
            avg_time_between_events,
            total_spent,
            avg_basket,
            last_event_time,
            CASE WHEN total_views > 0 THEN total_purchases * 1.0 / total_views ELSE 0 END AS conversion_rate,
            CASE WHEN (total_views + total_purchases) > 0 THEN total_purchases * 1.0 / (total_views + total_purchases) ELSE 0 END AS purchase_ratio,
            DATE_PART('day', CAST('2020-03-31 22:00:00' AS TIMESTAMP) - last_event_time) AS days_since_last_event
        FROM features
        WHERE total_events >= 10
        """
        
        print("Executing aggregation query...")
        df = pd.read_sql(query, connection)
        print(f"Found {len(df)} users with >= 10 events")
        
        if df.empty:
            print("No users found to process.")
            return {"users_processed": 0, "status": "success"}
        
        print(f"Processing {len(df)} user records...")
        
        cursor = connection.cursor()
        
        cursor.execute(f"DROP TABLE IF EXISTS {output_table}")
        
        cursor.execute(f"""
            CREATE TABLE {output_table} (
                user_id TEXT PRIMARY KEY,
                total_events INTEGER,
                total_views INTEGER,
                total_purchases INTEGER,
                avg_time_between_events DOUBLE PRECISION,
                total_spent DOUBLE PRECISION,
                avg_basket DOUBLE PRECISION,
                last_event_time TIMESTAMP,
                conversion_rate DOUBLE PRECISION,
                purchase_ratio DOUBLE PRECISION,
                days_since_last_event DOUBLE PRECISION
            )
        """)
        
        for _, row in df.iterrows():
            cursor.execute(
                f"""
                INSERT INTO {output_table}
                (user_id, total_events, total_views, total_purchases, avg_time_between_events, 
                 total_spent, avg_basket, last_event_time, conversion_rate, purchase_ratio, days_since_last_event)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(row['user_id']),
                    int(row['total_events']),
                    int(row['total_views']),
                    int(row['total_purchases']),
                    float(row['avg_time_between_events']) if pd.notna(row['avg_time_between_events']) else None,
                    float(row['total_spent']),
                    float(row['avg_basket']),
                    row['last_event_time'],
                    float(row['conversion_rate']),
                    float(row['purchase_ratio']),
                    float(row['days_since_last_event']) if pd.notna(row['days_since_last_event']) else None,
                )
            )
        
        connection.commit()
        cursor.close()
        
        print(f"\nPreprocessing complete. {len(df)} users saved to {output_table}")
        
        return {"users_processed": len(df), "status": "success"}
        
    except Exception as e:
        connection.rollback()
        print(f"Error during preprocessing: {str(e)}")
        raise
    finally:
        connection.close()
        print("Database connection closed.")


if __name__ == "__main__":
    test_config = {
        "host": "localhost",
        "database": "postgres",
        "user": "postgres",
        "password": "postgres",
        "port": 5432
    }
    
    result = data_cleansing_and_preprocessing(
        source_table="all_events",
        output_table="user_events",
        target=test_config
    )
    print(f"Result: {result}")
