#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail

# uncomment below when you see any issue with db...
# https://github.com/ymym3412/mlflow-docker-compose/issues/4
# mlflow db upgrade $MLFLOW_DB_URI

mlflow server --host 0.0.0.0  --port 5000  --backend-store-uri "postgresql+psycopg2://mlflow:mlflow-pwd@postgresql:5432/mlflow-db" --default-artifact-root "file:./mlflow/artifacts" --artifacts-destination "file:./mlflow/artifacts"