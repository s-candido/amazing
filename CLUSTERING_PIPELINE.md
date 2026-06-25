# Clustering Pipeline - Script Documentation

## Overview

This script implements a complete customer segmentation pipeline using KMeans clustering with Optuna hyperparameter optimization. It processes e-commerce event data from CSV, performs feature engineering, clustering, and saves results to PostgreSQL.

## Features

- **Data Loading & Cleaning**: Load CSV data, handle missing values, and remove outliers
- **Feature Engineering**: Create RFM (Recency, Frequency, Monetary) features and behavioral metrics
- **Feature Scaling**: StandardScaler normalization for machine learning algorithms
- **Dimensionality Reduction**: PCA for maintaining 95% variance while reducing features
- **Hyperparameter Optimization**: Optuna-based optimization of KMeans parameters
- **Clustering**: KMeans clustering with optimized hyperparameters
- **Evaluation**: Three key metrics:
  - **Silhouette Score** (higher is better, range: -1 to 1)
  - **Davies-Bouldin Index** (lower is better, range: 0 to ∞)
  - **Calinski-Harabasz Score** (higher is better)
- **Database Export**: Save results to PostgreSQL in `user_segment_{csv_name}` table

## Requirements

Install dependencies:

```bash
pip install -r requirements_clustering.txt
```

### Database Configuration

The script uses the following PostgreSQL configuration (hardcoded in the script):

```python
DB_CONFIG = {
    "host": "172.18.0.1",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
    "port": 5441,
}
```

Make sure PostgreSQL is running and accessible at this address.

## Usage

### Basic Usage

```bash
python clustering_pipeline.py --input /path/to/all_events.csv
```

### Example

```bash
# Process a CSV file with event data
python clustering_pipeline.py --input ./data/2019-Oct-10pct.csv

# Process from dags/src/data_folder/
python clustering_pipeline.py --input ./dags/src/data_folder/2019-Oct-10pct.csv
```

## Input Data Format

The input CSV should contain event data with these columns:

- `user_id`: Unique user identifier
- `event_type`: Type of event (view, cart, purchase)
- `event_time`: Timestamp of the event
- `product_id`: Product identifier
- `category_id`: Category identifier
- `category_code`: Category code (optional)
- `brand`: Brand name (optional)
- `price`: Price of the product
- `user_session`: Session identifier

## Output

### JSON Results File

A JSON file is created with the name: `clustering_results_{csv_filename}.json`

Example output:

```json
{
  "timestamp": "2026-03-11T10:30:45.123456",
  "csv_file": "2019-Oct-10pct",
  "csv_path": "/path/to/2019-Oct-10pct.csv",
  "total_records": 200000,
  "records_after_cleaning": 198500,
  "unique_users": 5000,
  "users_in_clustering": 4950,
  "optuna_parameters": {
    "n_clusters": 3,
    "n_init": 12
  },
  "metrics": {
    "Silhouette Score": 0.4523,
    "Davies-Bouldin Index": 1.2345,
    "Calinski-Harabasz Score": 456.78,
    "N Clusters": 3
  },
  "pca_info": {
    "n_components": 8,
    "variance_explained": 0.95
  }
}
```

### PostgreSQL Table

A table named `user_segment_{csv_filename}` is created with columns:

- `user_id`: User identifier
- `segment`: Cluster assignment (0, 1, 2, ...)
- `csv_file`: Source CSV filename
- `processed_at`: Timestamp of processing

Example table name: `user_segment_2019_oct_10pct`

## Pipeline Steps

1. **Load CSV** - Read event data from CSV file
2. **Clean Data** - Handle missing values, remove outliers (price > 0, IQR filtering)
3. **Feature Engineering** - Aggregate by user_id, create RFM and behavioral features
4. **Scale Features** - StandardScaler normalization
5. **PCA** - Reduce dimensionality while preserving 95% variance
6. **Optuna Optimization** - Find best KMeans hyperparameters (20 trials by default)
7. **Train KMeans** - Train model with 3 clusters and optimized parameters
8. **Evaluate** - Calculate Silhouette, Davies-Bouldin, Calinski-Harabasz scores
9. **Save Results** - Export JSON metrics and PostgreSQL table

## Configuration

Key parameters in the script (can be modified):

```python
N_CLUSTERS = 3                    # Number of clusters for KMeans
OPTUNA_N_TRIALS = 20              # Number of Optuna optimization trials
PCA_VARIANCE = 0.95               # Variance retention ratio for PCA
```

## Features Used in Clustering

The script uses 16 features for clustering (after aggregation by user):

1. `total_events` - Total number of events
2. `total_views` - Number of view events
3. `number_of_purchases` - Number of purchases
4. `total_spent` - Total monetary value
5. `avg_basket` - Average basket size
6. `conversion_rate` - View to purchase conversion ratio
7. `purchase_ratio` - Purchase events / total events
8. `days_since_last_event` - Recency in days
9. `recency` - Same as days_since_last_event
10. `frequency` - Total number of events
11. `monetary` - Total money spent
12. `number_of_cart_additions` - Cart additions count
13. `unique_products` - Unique products viewed
14. `unique_categories` - Unique categories visited
15. `number_of_sessions` - Number of sessions
16. `avg_time_between_events` - Average days between events

## Evaluation Metrics Interpretation

### Silhouette Score
- **Range**: -1 to 1
- **Best**: Values close to 1
- **Interpretation**: Measures how similar objects are to their own cluster vs other clusters
- **> 0.5**: Good clustering
- **> 0.7**: Excellent clustering

### Davies-Bouldin Index
- **Range**: 0 to ∞
- **Best**: Values close to 0
- **Interpretation**: Average similarity ratio of each cluster with its most similar cluster
- **< 1.0**: Very good clustering
- **< 2.0**: Generally acceptable

### Calinski-Harabasz Score
- **Higher is better**
- **Interpretation**: Ratio of between-cluster dispersion to within-cluster dispersion
- **> 100**: Good clustering
- **> 500**: Excellent clustering

## Error Handling

The script handles:
- Missing CSV file
- Database connection errors
- NaN and infinite values in features
- Empty clusters from DBSCAN (skips if too few clusters)

## Performance

- Typical processing time for 100K+ records: 5-15 minutes
- Memory usage scales with data size
- Optuna optimization time: ~1-3 minutes (20 trials)

## Example Workflow

```bash
# 1. Install dependencies
pip install -r requirements_clustering.txt

# 2. Run pipeline on October 2019 data
python clustering_pipeline.py --input ./dags/src/data_folder/2019-Oct-10pct.csv

# 3. Check results JSON
cat clustering_results_2019-Oct-10pct.json

# 4. Query results in PostgreSQL
psql -h 172.18.0.1 -U postgres -d postgres -c "SELECT * FROM user_segment_2019_oct_10pct LIMIT 10;"
```

## Troubleshooting

### PostgreSQL Connection Error
- Ensure PostgreSQL is running on `172.18.0.1:5441`
- Check credentials in `DB_CONFIG`
- Verify database exists: `postgres`

### CSV Not Found
- Check file path is correct
- Use absolute path or verify relative path

### Memory Issues
- Reduce data size before processing
- Process CSV files in batches

### Optuna Errors
- Check if data size is sufficient (needs at least several hundred rows)
- Verify X_pca has valid data (no NaN/inf values)

## Next Steps

To integrate this script into an Airflow DAG:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def run_clustering_pipeline(csv_path):
    import subprocess
    result = subprocess.run(
        ['python', 'clustering_pipeline.py', '--input', csv_path],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(result.stderr)

with DAG('clustering_pipeline', start_date=datetime(2026, 1, 1)) as dag:
    cluster_task = PythonOperator(
        task_id='run_clustering',
        python_callable=run_clustering_pipeline,
        op_kwargs={'csv_path': './dags/src/data_folder/2019-Oct-10pct.csv'}
    )
```

---

**Last Updated**: March 11, 2026
**Version**: 1.0
