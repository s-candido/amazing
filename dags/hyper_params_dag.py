import uuid
from datetime import datetime
import sys

from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import PythonOperator

sys.path.append('/opt/airflow/dags/src')

from src.ml_ia.hyper_params.hyperparam_search import search_best_clustering
from src.ml_ia.hyper_params.evaluate_clustering import evaluate_clustering

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
    "last_event_time",
    "conversion_rate",
    "purchase_ratio",
    "days_since_last_event",
]

TARGET = "segment"

DB_CONFIG = {
    "host": "amazing_postgresql",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
    "port": 5432,
}


def run_hyperparam_search(**context):

    result = search_best_clustering(
        db_config=DB_CONFIG,
        source_table=SOURCE_TABLE,
        target_table=PREDICTION_TABLE,
        feature_columns=FEATURE_COLUMNS,
        limit=SOURCE_TABLE_LIMIT
    )

    context['ti'].xcom_push(key='best_model', value=result)

    return result


def evaluate_clustering_task(**context):

    metrics = evaluate_clustering(
        target=DB_CONFIG,
        source_table=PREDICTION_TABLE,
        feature_columns=FEATURE_COLUMNS,
    )

    context['ti'].xcom_push(key='evaluation_metrics', value=metrics)

    return metrics


with DAG(
    dag_id="hyper_params_dag",
    schedule_interval=None,
    start_date=datetime(2022,3,3),
    catchup=False,
    description="Auto hyperparameter search clustering with MLflow",
    tags=["training","mlflow","clustering"],
) as dag:

    start = DummyOperator(task_id="start")

    hyperparam_search = PythonOperator(
        task_id="hyperparam_search",
        python_callable=run_hyperparam_search,
        provide_context=True
    )

    clustering_evaluation = PythonOperator(
        task_id="evaluate_clustering",
        python_callable=evaluate_clustering_task,
        provide_context=True
    )

    complete = DummyOperator(task_id="complete")

    start >> hyperparam_search >> clustering_evaluation >> complete