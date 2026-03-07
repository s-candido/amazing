# User Classification Model

This directory contains the implementation of a user classification model for assigning new users to existing clusters based on their behavior patterns.

## Files

- `user_classification_model.ipynb` - Main Jupyter notebook for training and evaluating classification models
- `classify_user.py` - Command-line tool for classifying users (single or batch)
- `random_forest.ipynb` - Existing Random Forest implementation (for reference)

## Models Implemented

- **XGBoost Classifier** - Gradient boosting model with high accuracy
- **LightGBM Classifier** - Fast gradient boosting with good performance  
- **Neural Network (MLP)** - Multi-layer perceptron for complex patterns
- **Random Forest** - Ensemble of decision trees (baseline)
- **Ensemble Model** - Voting classifier combining best models

## Features Used

The classification model uses the following user behavior features:

1. **total_events** - Total number of user interactions
2. **total_views** - Number of product views
3. **total_purchases** - Number of purchases
4. **avg_time_between_events** - Average time between user actions
5. **total_spent** - Total amount spent
6. **avg_basket** - Average basket size
7. **conversion_rate** - Purchase conversion rate
8. **purchase_ratio** - Purchase to view ratio
9. **days_since_last_event** - User activity recency
10. **is_active** - Active user flag (days_since_last_event < 30)
11. **events_per_day** - Derived feature: events per active day
12. **spend_per_event** - Derived feature: average spend per event
13. **view_to_purchase_ratio** - Derived feature: views per purchase

## Usage

### 1. Train Models

Run the Jupyter notebook to train and evaluate all models:

```bash
jupyter notebook user_classification_model.ipynb
```

The notebook will:
- Load user data from the database
- Perform feature engineering
- Train multiple classification models
- Evaluate and compare performance
- Save the best model automatically

### 2. Classify New Users

#### Interactive Mode:
```bash
python classify_user.py --interactive
```

#### Single User (JSON file):
```bash
python classify_user.py --user-data user.json
```

Example user.json:
```json
{
  "total_events": 45,
  "total_views": 38,
  "total_purchases": 3,
  "avg_time_between_events": 85000,
  "total_spent": 245.50,
  "avg_basket": 81.83,
  "conversion_rate": 0.067,
  "purchase_ratio": 0.079,
  "days_since_last_event": 15,
  "is_active": 1
}
```

#### Batch Classification:
```bash
python classify_user.py --batch users.json
```

Example users.json:
```json
[
  {
    "total_events": 45,
    "total_views": 38,
    "total_purchases": 3,
    "avg_time_between_events": 85000,
    "total_spent": 245.50,
    "avg_basket": 81.83,
    "conversion_rate": 0.067,
    "purchase_ratio": 0.079,
    "days_since_last_event": 15,
    "is_active": 1
  },
  {
    "total_events": 120,
    "total_views": 95,
    "total_purchases": 8,
    "avg_time_between_events": 65000,
    "total_spent": 1250.00,
    "avg_basket": 156.25,
    "conversion_rate": 0.084,
    "purchase_ratio": 0.084,
    "days_since_last_event": 5,
    "is_active": 1
  }
]
```

## Model Performance

The models are evaluated using:
- **Accuracy** - Overall classification accuracy
- **F1-Score** - Weighted F1 score for class imbalance
- **Cross-Validation** - 5-fold stratified cross-validation
- **Per-class metrics** - Precision and recall for each segment

## Output

Classification results include:
- **predicted_segment** - Assigned cluster (0-5)
- **confidence** - Model confidence score (0-1)
- **all_probabilities** - Probability for each segment
- **model_name** - Model used for classification
- **model_accuracy** - Model's test accuracy

## Model Files

Trained models are saved in the `saved_models/` directory:
- `best_classifier_[model]_[timestamp].joblib` - Best performing model
- `scaler_[timestamp].joblib` - Feature scaler
- `metadata_[timestamp].json` - Model metadata and feature list

## Requirements

```bash
pip install xgboost lightgbm scikit-learn pandas numpy matplotlib seaborn duckdb pathlib tqdm joblib
```

## Database Connection

The model connects to the DuckDB database at `../../amazing.duckdb` and expects:
- `user_segments_kmeans` table (or `user_segments`)
- User features and cluster assignments

If the database is empty, the notebook will create sample data for demonstration.

## Integration with Workflow

This classification model integrates with your user segmentation workflow:

1. **Clustering Phase** - K-means creates user clusters from existing users
2. **Training Phase** - Classification model learns the cluster patterns
3. **Classification Phase** - New users are assigned to appropriate clusters
4. **Retraining Phase** - Model is updated periodically with new data

This allows you to efficiently classify new users without re-running the entire clustering process.