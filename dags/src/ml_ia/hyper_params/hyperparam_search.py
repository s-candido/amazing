import itertools
import mlflow

from ml_ia.clustering.clustering_kmeans import run_clustering


def search_best_clustering(
    db_config,
    source_table,
    target_table,
    feature_columns,
    limit,
):

    param_grid = {
        "n_clusters": [3,4,5,6,7]
    }

    best_score = -1
    best_params = None

    for params in itertools.product(*param_grid.values()):

        n_clusters = params[0]

        result = run_clustering(
            target=db_config,
            source_table=source_table,
            target_table=target_table,
            feature_columns=feature_columns,
            limit=limit,
            n_clusters=n_clusters,
            drop_columns=[],
            lower_quantile=0,
            upper_quantile=0.75
        )

        score = result["metrics"]["silhouette_score"]

        if score > best_score:
            best_score = score
            best_params = n_clusters

    return {
        "best_score": best_score,
        "best_clusters": best_params
    }