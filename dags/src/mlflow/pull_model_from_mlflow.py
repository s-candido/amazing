import mlflow
from mlflow.pyfunc import load_model
from mlflow.tracking import MlflowClient

MLFLOW_URL="http://mlflow:5000"

MODEL_NAME="MODEL_AMAZING"

# Set the MLflow tracking URI
mlflow.set_tracking_uri(MLFLOW_URL)

def get_latest_model_version(model_name: str) -> int:
    """
    Get the latest version of a model from the MLflow model registry.

    Args:
        model_name (str): The name of the model in the MLflow model registry.

    Returns:
        int: The latest version of the model.
    """
    try:
        client = MlflowClient()
        versions = client.get_latest_versions(model_name, stages=["None", "Staging", "Production"])
        if versions:
            latest_version = max(int(version.version) for version in versions)
            print(f"Latest version of model '{model_name}' is: {latest_version}")
            return latest_version
        else:
            print(f"No versions found for model '{model_name}'.")
            return None
    except Exception as e:
        print(f"Error fetching latest version: {e}")
        return None

if __name__ == "__main__":
    version = get_latest_model_version(MODEL_NAME)
    model_name = MODEL_NAME
    model_uri = f"models:/{model_name}/{version}"
    model = load_model(model_uri)
    print(" ------------------------- MLFLOW  ------------------------- " )
    print("Model loaded successfully!")
    print(f"Model name : {version}")
    print("Model URI :", model_uri)
    print(f"Version : {model_name}")
    print("Model metadata:", model.metadata)
    print("Model configuration:", model.model_config)