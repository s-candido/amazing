import uuid
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
from src.test.performance_test import run_performance_test
import mlflow

MY_LOCAL_ASSETS = "/opt/airflow/dags"
MLFLOW_URL = "http://mlflow:5000"


def run_performance_test_task(**context):
    """
    Airflow task to run performance test on the latest model with noise injection.

    This task:
    1. Pulls the latest model from MLFlow
    2. Tests the model with increasing noise levels (0.0 to 0.5)
    3. Measures metrics degradation
    4. Logs all results and plots to MLFlow as artifacts and metrics

    Args:
        **context: Airflow context (for XCom, task instance, etc.)
    """
    mlflow.set_tracking_uri(MLFLOW_URL)

    results = run_performance_test(
        noise_levels=[0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        experiment_name="Performance_Test"
    )

    print("\n" + "="*60)
    print("PERFORMANCE TEST COMPLETED")
    print("="*60)
    print(f"Model Version Tested: {results['model_version']}")
    print(f"Baseline R2: {results['baseline']['R2']:.4f}")
    print(f"Baseline RMSE: {results['baseline']['RMSE']:.4f}")
    print(f"Baseline MAPE: {results['baseline']['MAPE (%)']:.2f}%")
    print(f"MLFlow Run ID: {results['mlflow_run_id']}")
    print("="*60)

    return results


with DAG(
    dag_id="performance_test_dag",
    schedule_interval=None,
    start_date=datetime(2022, 3, 3),
    catchup=False,
    description="""
    Performance test DAG for ML model robustness evaluation.

    This DAG runs a noise-injection performance test on the latest model
    from MLFlow to evaluate its robustness to data quality degradation.

    Test Details:
    - Pulls latest model version from MLFlow registry (MODEL_AMAZING)
    - Tests model with 9 different noise levels: [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]
    - Noise level = fraction of feature standard deviation
    - Measures R2, RMSE, MAPE at each noise level
    - Calculates degradation relative to baseline (noise=0.0)
    - Logs ALL results to MLFlow experiment "Performance_Test"

    Outputs (all in MLFlow):
    - Metrics: R2, RMSE, MAPE and their degradation at each noise level
    - Artifacts:
      * performance_test_v{version}_summary.png: Multi-panel plot with all metrics
      * degradation_analysis_v{version}.png: Degradation analysis with thresholds
      * performance_results.csv: Complete results in CSV format

    View results in MLFlow UI: http://localhost:5000
    """, 
    tags=["test", "mlflow", "performance_test"]
) as dag:

    start = DummyOperator(task_id="start")

    performance_test_task = PythonOperator(
        task_id="run_performance_test",
        python_callable=run_performance_test_task,
        do_xcom_push=False,
        dag=dag
    )

    complete = DummyOperator(task_id="complete")

    start >> performance_test_task >> complete
