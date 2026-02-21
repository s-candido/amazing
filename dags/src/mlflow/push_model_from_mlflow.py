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

# Name of the model to save in MLflow Model Registry
MODEL_NAME="MODEL_AMAZING"

# Default path of the local model file to import 
DEFAULT_MODEL_PATH="./src/models/model.joblib"

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Push a model to MLflow')
parser.add_argument('--model_path', type=str, default=DEFAULT_MODEL_PATH,
                    help=f'Path to the model file to import (default: {DEFAULT_MODEL_PATH})')
args = parser.parse_args()

mlflow.set_tracking_uri(MLFLOW_URL)

model_path = joblib.load(str(args.model_path))

model_name = MODEL_NAME

#mlflow.create_experiment("AMAZING_Model_Experiment")
mlflow.set_experiment("AMAZING_Model_Experiment")

with mlflow.start_run():
    # Log the artifact
    mlflow.log_artifact(args.model_path, artifact_path=model_name)
    
    # Log the sklearn model
    mlflow.sklearn.log_model(model_path, artifact_path=model_name)
    
    # Register the model (this will create a new version if the model already exists)
    mlflow.register_model(
        f"runs:/{mlflow.active_run().info.run_id}/{model_name}",
        model_name,
    )
    
    print(f"Model registered as '{model_name}' - Run ID: {mlflow.active_run().info.run_id}")

print("Upload complete!")