from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sklearn.cluster import KMeans
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler


class ClusteringError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClusteringConfig:
    source_table: str
    target_table: str
    feature_columns: List[str]
    id_column: str = "user_id"
    limit: Optional[int] = None
    drop_columns: Optional[Iterable[str]] = None
    n_clusters: int = 4
    lower_quantile: float = 0.0
    upper_quantile: float = 0.75


def _fetch_dataframe(connection, config: ClusteringConfig) -> pd.DataFrame:
    with connection.cursor() as cursor:
        columns = [config.id_column, *config.feature_columns]
        query = f"SELECT {', '.join(columns)} FROM {config.source_table}"
        if config.limit:
            query += f" LIMIT {int(config.limit)}"
        cursor.execute(query)
        rows = cursor.fetchall()

    if not rows:
        raise ClusteringError("No data returned from source table.")

    df = pd.DataFrame(rows, columns=columns)
    df.dropna(subset=config.feature_columns, how="all", inplace=True)
    if df.empty:
        raise ClusteringError("Dataset empty after dropping rows with missing features.")
    return df


def _clip_outliers(df: pd.DataFrame, columns: Iterable[str], lower: float, upper: float) -> pd.DataFrame:
    cleaned = df.copy()
    for col in columns:
        if col not in cleaned.columns:
            continue
        lower_threshold = cleaned[col].quantile(lower)
        upper_threshold = cleaned[col].quantile(upper)
        cleaned[col] = cleaned[col].clip(lower=lower_threshold, upper=upper_threshold)
    return cleaned


def _standardize(df: pd.DataFrame, columns: Iterable[str]) -> np.ndarray:
    scaler = StandardScaler()
    return scaler.fit_transform(df.loc[:, columns])


def _fit_kmeans(x_scaled: np.ndarray, n_clusters: int) -> KMeans:
    if x_scaled.size == 0:
        raise ClusteringError("Empty feature matrix, cannot fit KMeans.")
    model = KMeans(n_clusters=n_clusters, random_state=42)
    model.fit(x_scaled)
    return model


def _insert_segments(connection, config: ClusteringConfig, segments: pd.DataFrame) -> None:
    if segments.empty:
        raise ClusteringError("No segments to insert.")

    with connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {config.target_table}")

        feature_columns_sql = ",\n".join(
            f"{col} DOUBLE PRECISION" for col in config.feature_columns
        )

        cursor.execute(
            f"""
            CREATE TABLE {config.target_table} (
                {config.id_column} TEXT,
                {feature_columns_sql},
                segment INTEGER
            )
            """
        )

        ordered_columns = [config.id_column, *config.feature_columns, "segment"]
        records = []
        for _, row in segments.iterrows():
            record = []
            for col in ordered_columns:
                value = row[col]
                if col == config.id_column:
                    record.append(str(value))
                elif col == "segment":
                    record.append(int(value))
                else:
                    record.append(float(value) if pd.notna(value) else None)
            records.append(tuple(record))

        execute_values(
            cursor,
            f"INSERT INTO {config.target_table} ({', '.join(ordered_columns)}) VALUES %s",
            records,
        )
    connection.commit()


def run_clustering(
    target: Dict[str, Any],
    source_table: str,
    target_table: str,
    feature_columns: List[str],
    id_column: str = "user_id",
    limit: Optional[int] = None,
    n_clusters: int = 4,
    drop_columns: Optional[Iterable[str]] = None,
    lower_quantile: float = 0.0,
    upper_quantile: float = 0.75,
) -> Dict[str, Any]:
    required = {"host", "database", "user", "password", "port"}
    if not required.issubset(target):
        missing = required - set(target)
        raise ValueError(f"target configuration missing keys: {', '.join(missing)}")

    config = ClusteringConfig(
        source_table=source_table,
        target_table=target_table,
        feature_columns=feature_columns,
        id_column=id_column,
        limit=limit,
        drop_columns=drop_columns,
        n_clusters=n_clusters,
        lower_quantile=lower_quantile,
        upper_quantile=upper_quantile,
    )

    connection = psycopg2.connect(**target)
    try:
        df = _fetch_dataframe(connection, config)
        if config.drop_columns:
            df = df.drop(columns=list(config.drop_columns), errors="ignore")

        df_clean = _clip_outliers(df, config.feature_columns, config.lower_quantile, config.upper_quantile)
        x_scaled = _standardize(df_clean, config.feature_columns)
        model = _fit_kmeans(x_scaled, config.n_clusters)
        segments = df_clean[[config.id_column, *config.feature_columns]].copy()
        segments["segment"] = model.labels_

        _insert_segments(connection, config, segments)

        silhouette = silhouette_score(x_scaled, model.labels_)
        calinski = calinski_harabasz_score(x_scaled, model.labels_)
        davies = davies_bouldin_score(x_scaled, model.labels_)

        return {
            "status": "success",
            "rows_processed": len(df_clean),
            "n_clusters": config.n_clusters,
            "metrics": {
                "silhouette_score": float(silhouette),
                "calinski_harabasz_score": float(calinski),
                "davies_bouldin_score": float(davies),
            },
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


__all__ = ["run_clustering", "ClusteringError"]
