from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd
import psycopg2
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler


def evaluate_clustering(
    target: Dict[str, Any],
    source_table: str = "user_segments",
    id_column: str = "user_id",
    feature_columns: Optional[list[str]] = None,
) -> Dict[str, Any]:
    if feature_columns is None:
        raise ValueError("feature_columns must be provided")

    connection = psycopg2.connect(**target)
    try:
        query = f"SELECT {id_column}, {', '.join(feature_columns)}, segment FROM {source_table}"
        df = pd.read_sql(query, connection)
        if df.empty:
            return {"status": "error", "message": "No data found for evaluation"}

        features = df[feature_columns]
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(features)
        labels = df["segment"].to_numpy()

        results = {
            "status": "success",
            "rows_evaluated": len(df),
            "metrics": {
                "silhouette_score": float(silhouette_score(x_scaled, labels)),
                "calinski_harabasz_score": float(calinski_harabasz_score(x_scaled, labels)),
                "davies_bouldin_score": float(davies_bouldin_score(x_scaled, labels)),
            },
        }
        return results
    finally:
        connection.close()


__all__ = ["evaluate_clustering"]
