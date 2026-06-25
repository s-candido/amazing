"""
DAG Airflow pour exécuter le feature engineering utilisateurs

Ce DAG:
1. Lance l'exécution du notebook user_features_engineering.ipynb
2. Generate les features dans la table user_features
3. Valide les résultats

Fréquence: Quotidienne à 2h du matin (après les exports de données)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.exceptions import AirflowException
import logging

logger = logging.getLogger(__name__)

# Configuration par défaut
default_args = {
    'owner': 'data-team',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
}

# Définir le DAG
dag = DAG(
    'user_features_engineering',
    default_args=default_args,
    description='Feature engineering pour le clustering utilisateurs',
    schedule_interval='0 2 * * *',  # Quotidien à 2h du matin
    catchup=False,
    tags=['ml', 'features', 'clustering'],
)


def validate_user_features(**context):
    """
    Valide le résultat du feature engineering.
    Vérifie que la table user_features contient suffisamment de données.
    """
    try:
        from sqlalchemy import create_engine, text
        import pandas as pd
        
        DB_CONFIG = {
            "host": "172.18.0.1",
            "database": "postgres",
            "user": "postgres",
            "password": "postgres",
            "port": 5441,
        }
        
        connection_string = f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        engine = create_engine(connection_string)
        
        # Charger les données
        df = pd.read_sql_table('user_features', engine)
        
        # Validations
        assert len(df) > 0, "Table user_features vide"
        assert len(df.columns) >= 11, f"Nombre de colonnes insuffisant: {len(df.columns)}"
        
        # Vérifier les colonnes critiques
        required_cols = ['user_id', 'nb_events', 'clusterability_index']
        for col in required_cols:
            assert col in df.columns, f"Colonne manquante: {col}"
        
        # Vérifier la qualité des données
        null_count = df.isnull().sum().sum()
        pct_null = 100 * null_count / (len(df) * len(df.columns))
        assert pct_null < 5, f"Trop de valeurs manquantes: {pct_null:.2f}%"
        
        # Statistiques
        stats = {
            'total_users': len(df),
            'total_features': len(df.columns),
            'null_percentage': pct_null,
            'avg_clusterability': df['clusterability_index'].mean(),
            'high_quality_users': (df['clusterability_index'] >= 50).sum(),
        }
        
        logger.info(f"Validation réussie: {stats}")
        context['task_instance'].xcom_push(key='validation_stats', value=stats)
        
        return stats
        
    except Exception as e:
        logger.error(f"Validation échouée: {e}")
        raise AirflowException(f"Validation des features échouée: {e}")


# Task 1: Lancer le notebook
run_notebook = BashOperator(
    task_id='run_feature_engineering_notebook',
    bash_command='''
    cd /home/c-enjalbert/Documents/Github/MSPR/bloc_2/amazing_airflow/amazing
    jupyter nbconvert --to notebook --execute \
        --ExecutePreprocessor.timeout=3600 \
        src/ml_ia/category_features/user_features_engineering.ipynb
    ''',
    dag=dag,
)

# Task 2: Valider les résultats
validate = PythonOperator(
    task_id='validate_user_features',
    python_callable=validate_user_features,
    provide_context=True,
    dag=dag,
)

# Task 3: Notifications (optionnel)
notify_success = BashOperator(
    task_id='notify_success',
    bash_command='echo "Feature engineering completed successfully"',
    dag=dag,
)

# Dépendances
run_notebook >> validate >> notify_success


if __name__ == '__main__':
    logger.info("DAG user_features_engineering chargé")
