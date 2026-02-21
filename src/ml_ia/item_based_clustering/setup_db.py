import duckdb
import pandas as pd
from pathlib import Path

db_path = Path("../../amazing.duckdb")
con = duckdb.connect(str(db_path))
print(f"Connected to database at: {db_path}")

all_events = con.sql("SELECT * FROM all_events ORDER BY RANDOM() LIMIT 50000").df()

allevents_df_CF = all_events[["user_id", "product_id", "category_code", "event_type"]].copy()
allevents_df_CF.dropna(subset=["category_code"], inplace=True)
allevents_df_CF["event_score"] = allevents_df_CF["event_type"].map({"view": 1, "cart": 3, "purchase": 5})

user_item_matrix = allevents_df_CF.pivot_table(
    index='product_id', 
    columns='user_id', 
    values='event_score', 
    aggfunc='max'
).fillna(0)

user_item_matrix_reset = user_item_matrix.reset_index()

con.register('user_item_matrix_view', user_item_matrix_reset)
con.execute("CREATE OR REPLACE TABLE cf_matrix AS SELECT * FROM user_item_matrix_view")
print("Table cf_matrix created successfully.")
con.close()
