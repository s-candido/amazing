import pandas as pd
import mlflow
import mlflow.sklearn

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sqlalchemy import create_engine


def load_data(db_config, table, features, limit):

    conn = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    engine = create_engine(conn)

    query = f"""
    SELECT {','.join(features)}
    FROM {table}
    LIMIT {limit}
    """

    df = pd.read_sql(query, engine)
    return df


def run_clustering(
    target,
    source_table,
    target_table,
    feature_columns,
    limit,
    n_clusters,
    drop_columns,
    lower_quantile,
    upper_quantile,
):

    df = load_data(target, source_table, feature_columns, limit)

    X = df[feature_columns]

    with mlflow.start_run():

        model = KMeans(n_clusters=n_clusters, random_state=42)

        labels = model.fit_predict(X)

        score = silhouette_score(X, labels)

        mlflow.log_param("n_clusters", n_clusters)
        mlflow.log_metric("silhouette_score", score)

        mlflow.sklearn.log_model(model, "kmeans_model")

    return {
        "metrics": {
            "silhouette_score": score,
            "n_clusters": n_clusters
        }
    }