import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from src.data.data_loader import load_all_data
from src.data.weather_loader import fetch_weather

from src.features.features import create_features
from src.features.weather_features import *

from src.modeling.train import train_models
from src.modeling.evaluate import evaluate_model

from src.ingestion.downloader import download_and_extract

from sklearn.model_selection import train_test_split
import mlflow

import joblib
import os
import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient
import mlflow.sklearn
import joblib
import os
import joblib

import mlflow
import mlflow.sklearn
import joblib
import os
import argparse

MLFLOW_URL="http://mlflow:5000"
MODEL_NAME="MODEL_AMAZING"
MY_LOCAL_ASSETS= "/opt/airflow/dags"
DATA_DIR = "/opt/airflow/dags/src/data_folder"
TARGET = "consommation"


def run_ml_pipeline(data_dir=DATA_DIR, target=TARGET, test_size=0.2, random_state=42, 
                    start_year=2012, download=True, save_model=True, model_path="/opt/airflow/dags/src/models/model.joblib"):
    """
    Run the complete ML pipeline: data loading, feature engineering, training, and evaluation.
    
    Args:
        data_dir (str): Directory containing the data files
        target (str): Target column name
        test_size (float): Test set size ratio (default: 0.2)
        random_state (int): Random seed for reproducibility (default: 42)
        start_year (int): Start year for data download (default: 2012)
        download (bool): Whether to download and extract data (default: True)
        save_model (bool): Whether to save the best model (default: True)
        model_path (str): Path to save the model (default: "./src/models/model.joblib")
    
    Returns:
        dict: Dictionary containing:
            - 'best_model': The best trained model
            - 'best_name': Name of the best model
            - 'best_r2': R² score of the best model
            - 'models': All trained models
            - 'X_test': Test features
            - 'y_test': Test target
            - 'metrics': Evaluation metrics for all models
    """
    
    ## Download data if requested
    #if download:
    #    download_and_extract(start_year=start_year, target_dir=data_dir)
    
    # Load and prepare data
    df = load_all_data(data_dir)
    print("Source Files :", df["source_file"].unique().tolist())
    source_files = df["source_file"].unique().tolist()
    print("Features columns :", df.columns.tolist())
    features = df.columns.tolist()
    df = create_features(df)
    print(df.describe())
    # Handle target columnAMAZING_Model_Experiment
    df[target] = pd.to_numeric(df[target], errors="coerce")
    
    X = df.drop(columns=[target])
    y = df[target]
    
    X = X.fillna(0)
    y = y.fillna(0)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    
    # Train models
    models = train_models(X_train, y_train)
    
    # Evaluate models
    best_name, best_model, best_r2 = None, None, -999
    metrics_all = {}
    
    for name, model in models.items():
        metrics = evaluate_model(model, X_test, y_test)
        metrics_all[name] = metrics
        
        print(f"Modèle : {name}")
        for k, v in metrics.items():
            print(f"{k} : {v:.4f}")
        
        if metrics["R2"] > best_r2:
            best_r2 = metrics["R2"]
            best_name, best_model = name, model
    

    # Configure MLflow BEFORE starting the run
    mlflow.set_tracking_uri(MLFLOW_URL)
    mlflow.set_experiment("AMAZING_Model_Experiment")

    # Register model in MLflow without saving locally
    with mlflow.start_run():
        mlflow.log_param("source_files", source_files)
        ##mlflow.log_param("features", features)
        # Log params and metrics (strings → params, numbers → metrics)
        mlflow.log_param("model_type", best_name)
        mlflow.log_metric("R2", float(best_r2))

        # Log the model directly to MLflow
        mlflow.sklearn.log_model(best_model, artifact_path=MODEL_NAME)

        # Register the model in MLflow Model Registry
        model_uri = f"runs:/{mlflow.active_run().info.run_id}/{MODEL_NAME}"
        mlflow.register_model(model_uri, MODEL_NAME)

        print(f"Modèle retenu : {best_name} (R2={best_r2:.4f})")
        print(f"Model registered in MLflow as '{MODEL_NAME}' - Run ID: {mlflow.active_run().info.run_id}")

    # Fetch weather data
    fetch_weather("2020-01-01", "2020-12-31")
    
    print(f"Modèle retenu : {best_name} (R2={best_r2:.4f})")
    
    return {
        'best_model': best_model,
        'best_name': best_name,
        'best_r2': best_r2,
        'models': models,
        'X_test': X_test,
        'y_test': y_test,
        'metrics': metrics_all
    }


if __name__ == "__main__":
    # Run the pipeline when executed directly
    results = run_ml_pipeline()