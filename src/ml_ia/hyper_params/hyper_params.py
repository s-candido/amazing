import optuna
import mlflow
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

def objective(trial):

    n_clusters = trial.suggest_int("n_clusters",2,10)
    max_iter = trial.suggest_int("max_iter",100,500)

    model = KMeans(
        n_clusters=n_clusters,
        max_iter=max_iter
    )

    labels = model.fit_predict(X)
    score = silhouette_score(X, labels)

    mlflow.log_params({
        "n_clusters": n_clusters,
        "max_iter": max_iter
    })

    mlflow.log_metric("silhouette", score)

    return score