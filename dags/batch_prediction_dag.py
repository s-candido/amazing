from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
from src.batch_prediction.batch_prediction import batch_prediction
from src.batch_prediction.data_prep import prepare_batch_prediction_data


SOURCE_TABLE = "user_features"
PREPARED_TABLE = "agg_conso_meteo_features"
PREDICTION_TABLE = "user_segments"
FEATURE_COLUMNS = [
    "temp_fr",
    "snow_fr",
    "hour",
    "month",
    "dayofweek",
    "weekend",
]
UTILS_COLUMNS = [
    "id",
    "conso_id",
    "datetime",
    "year",
    "day"
]

DB_CONFIG = {
    "host": "amazing_postgresql",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
    "port": 5432,
}
TARGET = "consommation"
MLFLOW_URL = "http://mlflow:5000"


with DAG(
    dag_id="batch_prediction_dag",
    schedule_interval=None,
    start_date=datetime(2022, 3, 3,),
    catchup=False,
    description="DAG for batch prediction from PostgreSQL and MLflow",
    tags=["data", "prediction", "postgresql"],
    params={
        "selected_years": [2020],
        "selected_months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "selected_days": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31],
        }) as dag:


    start = DummyOperator(task_id="start")

    prepare_data_job = PythonOperator(
        task_id="prepare_data_job",
        python_callable=prepare_batch_prediction_data,
        op_kwargs={
            "source_table": SOURCE_TABLE,
            "prepared_table": PREPARED_TABLE,
            "feature_columns": FEATURE_COLUMNS,
            "utils_columns": UTILS_COLUMNS,
            "target": TARGET,
        },
        do_xcom_push=False,
        dag=dag,
    )

    batch_prediction_job = PythonOperator(
        task_id="batch_prediction_job",
        python_callable=batch_prediction,
        op_kwargs={
            "model_name": "MODEL_AMAZING",
            "source_table": PREPARED_TABLE,
            "prediction_table": PREDICTION_TABLE,
            "feature_columns": FEATURE_COLUMNS,
            "db_config" : DB_CONFIG,
            "mlflow_url" : MLFLOW_URL,
        },
        do_xcom_push=False,
        dag=dag,
    )


    complete = DummyOperator(task_id="complete")

    start >> prepare_data_job >> batch_prediction_job >> complete