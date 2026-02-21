import uuid
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule
from airflow.operators.dummy_operator import DummyOperator
from src.main import run_ml_pipeline  # Import the functions from the script


# Correlation id for training job (this can be also found on MLFLow tracking)
correlation_id = uuid.uuid4()

MY_LOCAL_ASSETS= "/opt/airflow/dags"


# Define the DAG
with DAG(
        dag_id="main_dag",
        schedule_interval=None,
        start_date=datetime(2022, 3, 3,),
        catchup=False,
        description="DAG for loading weather and consumption data into PostgreSQL",
        tags=["train","evaluate", "local", "mlflow"]) as dag:

    start = DummyOperator(task_id="start")

    # Task for running data preprocessing task
    preprocessing_task = PythonOperator(
        task_id="main_script_job",
        python_callable=run_ml_pipeline,
        do_xcom_push=False,
        dag=dag
    )


    complete = DummyOperator(task_id="complete")

    # Linear pipeline: start -> preprocessing -> training -> complete
    start >> preprocessing_task >>  complete


