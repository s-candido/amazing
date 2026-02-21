import uuid
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy_operator import DummyOperator

import sys
import os

from src.data_ingestion import run_full_pipeline

from src.etl.load_all_events import load_all_events
from src.etl.data_preprocessing import data_cleansing_and_preprocessing


correlation_id = uuid.uuid4()

MY_LOCAL_ASSETS = "/opt/airflow/dags"
DATA_FOLDER_PATH = "/opt/airflow/dags/src/data_folder"

ALL_EVENTS_TABLE = "all_events"
USER_EVENTS_TABLE = "user_events"
USER_EVENT_COLUMNS = [
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

DB_CONFIG = {
    "host": "amazing_postgresql",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
    "port": 5432,
}




with DAG(
        dag_id="data_ingestion_dag",
        schedule_interval=None,
        start_date=datetime(2022, 3, 3,),
        catchup=False,
        description="""DAG for : 
        1.  Loading .csv file from dat_folder/ and load into PostgreSQL
        2.  Data Cleansing and PreProcessing""",
        tags=["data", "ingestion", "postgresql"]) as dag:

    start = DummyOperator(task_id="start")


    loading_job = PythonOperator(
        task_id="cleanning_job",
        python_callable=load_all_events,
        op_kwargs={
            "data_folder_path": DATA_FOLDER_PATH,
            "output_table": USER_EVENTS_TABLE,
            "output_columns": USER_EVENT_COLUMNS,
            "target": DB_CONFIG,
        },
        do_xcom_push=False,
        dag=dag
    )

    processing_job = PythonOperator(
        task_id="processing_job",
        python_callable=data_cleansing_and_preprocessing,
        op_kwargs={
            "source_table": ALL_EVENTS_TABLE,
            "output_table": USER_EVENTS_TABLE,
            "output_columns": USER_EVENT_COLUMNS,
            "target": DB_CONFIG,
        },
        do_xcom_push=False,
        dag=dag
    )


    complete = DummyOperator(task_id="complete")

    start >> loading_job >> processing_job >> complete