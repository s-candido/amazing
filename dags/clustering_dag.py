import uuid
import json
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy_operator import DummyOperator

import sys
import os
import psycopg2
import pandas as pd
import mlflow
import mlflow.sklearn
sys.path.append('/opt/airflow/dags/src')

from src.batch_prediction.data_prep import prepare_batch_prediction_data

correlation_id = uuid.uuid4()
MY_LOCAL_ASSETS = "/opt/airflow/dags"
MLFLOW_URL= "http://mlflow:5000"
SOURCE_TABLE = "user_features"
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

MODEL_NAME = "MODEL_AMAZING"

def train_and_log_model(**context):
    dag_run_conf = context.get('dag_run').conf or {}
    selected_months = dag_run_conf.get('selected_months', [])
    
    conn = psycopg2.connect(**DB_CONFIG)

    feature_columns = list(FEATURE_COLUMNS)
    if not feature_columns:
        raise ValueError("feature_columns must contain at least one column name.")

    query = f"""
        SELECT *
        FROM {SOURCE_TABLE}_{selected_months}
        LIMIT {SOURCE_TABLE_LIMIT};
    """
    
    print(f"Executing query: {query}")
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"Loaded {len(df)} records from {SOURCE_TABLE} for years {selected_months}")
    
    if df is None or df.empty:
        raise ValueError("No data available for training")
    
    TARGET = "consommation"
    df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")
    
    X = df[feature_columns].fillna(0)
    y = df[TARGET].fillna(0)
    print(" ----------- Modèle entrainé avec ces colonnes ----------- ")
    print(X.head())
    print(f"Training on {len(X)} samples with {len(FEATURE_COLUMNS)} features")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    models = train_models(X_train, y_train)
    
    best_name, best_model, best_r2 = None, None, -999
    
    for name, model in models.items():
        metrics = evaluate_model(model, X_test, y_test)
        print(f"Model: {name}")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")
        
        if metrics["R2"] > best_r2:
            best_r2 = metrics["R2"]
            best_name, best_model = name, model
    
    print(f"Best model: {best_name} (R2={best_r2:.4f})")
    mlflow.set_tracking_uri(MLFLOW_URL)
    mlflow.set_experiment("AMAZING_Model_Experiment")
    
    with mlflow.start_run(run_name=f"training_{best_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        mlflow.log_param("model_type", best_name)
        mlflow.log_param("training_years", str(selected_months))
        mlflow.log_param("n_samples", len(X_train))
        mlflow.log_param("n_features", len(FEATURE_COLUMNS))
        mlflow.log_param("features", FEATURE_COLUMNS)
        mlflow.log_param("correlation_id", str(correlation_id))
        
        final_metrics = evaluate_model(best_model, X_test, y_test)
        mlflow.log_metric("R2", final_metrics['R2'])
        mlflow.log_metric("RMSE", final_metrics['RMSE'])
        mlflow.log_metric("MAPE", final_metrics['MAPE (%)'])

        # Log the model directly to MLflow
        mlflow.sklearn.log_model(best_model, artifact_path=MODEL_NAME)

        # Register the model in MLflow Model Registry
        model_uri = f"runs:/{mlflow.active_run().info.run_id}/{MODEL_NAME}"
        mlflow.register_model(model_uri, MODEL_NAME)

        print(f"Modèle retenu : {best_name} (R2={best_r2:.4f})")
        print(f"Model registered in MLflow as '{MODEL_NAME}' - Run ID: {mlflow.active_run().info.run_id}")

        print(f"Model and artifacts logged to MLflow with correlation_id: {correlation_id}")
        print(f"MLflow experiment: energy_consumption_training")
    
    return {"model_name": best_name, "r2_score": best_r2, "correlation_id": str(correlation_id)}

with DAG(
    dag_id="training_dag",
    schedule_interval=None,
    start_date=datetime(2022, 3, 3),
    catchup=False,
    description="DAG for training ML models on selected years from user_features table",
    tags=["training", "mlflow", "postgresql"],
    params={"selected_months": ["11_2020"]}
    
) as dag:

    start = DummyOperator(task_id="start")

    prepare_data_job = PythonOperator(
        task_id="prepare_data_job",
        python_callable=prepare_batch_prediction_data,
        op_kwargs={
            "source_table": SOURCE_TABLE,
            "prepared_table": "agg_conso_meteo_features",
            "feature_columns": FEATURE_COLUMNS,
            "utils_columns": UTILS_COLUMNS,
            "target": TARGET,
        },
        do_xcom_push=False,
        dag=dag,
    )

    train_model_task = PythonOperator(
        task_id="train_model_task", 
        python_callable=train_and_log_model,
        do_xcom_push=False,
        dag=dag
    )

    complete = DummyOperator(task_id="complete")

    start >> prepare_data_job >> train_model_task >> complete