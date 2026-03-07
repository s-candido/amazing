import pandas as pd
from sqlalchemy import create_engine
from sklearn.metrics import silhouette_score


def evaluate_clustering(target, source_table, feature_columns):

    conn = f"postgresql://{target['user']}:{target['password']}@{target['host']}:{target['port']}/{target['database']}"
    engine = create_engine(conn)

    df = pd.read_sql(f"SELECT * FROM {source_table}", engine)

    X = df[feature_columns]
    labels = df["segment"]

    score = silhouette_score(X, labels)

    return {
        "metrics": {
            "silhouette_score": score
        }
    }