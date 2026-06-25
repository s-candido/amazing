import uuid
from datetime import datetime
import sys
from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import PythonOperator




sys.path.append('/opt/airflow/dags/src')


from ml_ia.clustering.clustering_kmeans import run_clustering
from ml_ia.evaluate_clustering import evaluate_clustering

correlation_id = uuid.uuid4()
MY_LOCAL_ASSETS = "/opt/airflow/dags"
SOURCE_TABLE = "user_events"
SOURCE_TABLE_LIMIT = 10000
PREDICTION_TABLE = "user_segments"
FEATURE_COLUMNS = [
    "total_events",
    "total_views",
    "total_purchases",
    "avg_time_between_events",
    "total_spent",
    "avg_basket",
    "conversion_rate",
    "purchase_ratio",
    "days_since_last_event",
]
UTILS_COLUMNS = [
    "user_id"
]
TARGET = "segment"

DB_CONFIG = {
    "host": "amazing_postgresql",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
    "port": 5432,
}


def run_clustering_task(**context):
    conf = context.get('dag_run').conf or {}
    cluster_kwargs = {
        "target": DB_CONFIG,
        "source_table": SOURCE_TABLE,
        "target_table": PREDICTION_TABLE,
        "feature_columns": FEATURE_COLUMNS,
        "limit": conf.get('source_limit', SOURCE_TABLE_LIMIT),
        "n_clusters": conf.get('n_clusters', 4),
        "drop_columns": conf.get('drop_columns', []),
        "lower_quantile": conf.get('lower_quantile', 0.0),
        "upper_quantile": conf.get('upper_quantile', 0.75),
    }
    result = run_clustering(**cluster_kwargs)
    context['ti'].xcom_push(key='clustering_metrics', value=result['metrics'])
    return result


def evaluate_clustering_task(**context):
    metrics = evaluate_clustering(
        target=DB_CONFIG,
        source_table=PREDICTION_TABLE,
        feature_columns=FEATURE_COLUMNS,
    )
    context['ti'].xcom_push(key='evaluation_metrics', value=metrics['metrics'])
    return metrics

with DAG(
    dag_id="clustering_dag",
    schedule_interval=None,
    start_date=datetime(2022, 3, 3),
    catchup=False,
    description="DAG for predict clsuter on user events and log model to MLflow",
    tags=["training", "mlflow", "postgresql"],
    params={"selected_months": ["11_2020"]}
    
) as dag:

    start = DummyOperator(task_id="start")

    clustering_training = PythonOperator(
        task_id="run_clustering", 
        python_callable=run_clustering_task,
        provide_context=True,
        dag=dag
    )

    clustering_evaluation = PythonOperator(
        task_id="evaluate_clustering", 
        python_callable=evaluate_clustering_task,
        provide_context=True,
        dag=dag
    )

    complete = DummyOperator(task_id="complete")

    start >> clustering_training >> clustering_evaluation >> complete
