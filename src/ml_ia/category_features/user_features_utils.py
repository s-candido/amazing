"""
Module utilitaire pour charger et utiliser les features utilisateurs du clustering

Exemple d'utilisation:
    from user_features_utils import load_user_features, prepare_clustering_data
    
    df_features = load_user_features(engine)
    X_scaled, user_ids = prepare_clustering_data(df_features, min_clusterability=50)
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler
from typing import Tuple, List


def load_user_features(engine) -> pd.DataFrame:
    """
    Charge la table user_features depuis PostgreSQL.
    
    Args:
        engine: SQLAlchemy engine connecté à la base de données
        
    Returns:
        DataFrame: Données de user_features
    """
    return pd.read_sql_table('user_features', engine)


def prepare_clustering_data(
    df_features: pd.DataFrame, 
    min_clusterability: float = 0,
    normalize: bool = True,
    exclude_low_quality: bool = True
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prépare les données pour le clustering.
    
    Args:
        df_features (DataFrame): Table user_features chargée
        min_clusterability (float): Score minimum de clusterability (0-100)
                                   Défaut: 0 (tous les utilisateurs)
        normalize (bool): Si True, normalise les features avec StandardScaler
        exclude_low_quality (bool): Si True, exclut les utilisateurs avec 
                                   clusterability_index < min_clusterability
    
    Returns:
        Tuple[np.ndarray, np.ndarray]: (X_scaled, user_ids) 
                                      X_scaled: matrice de features normalisées
                                      user_ids: identifiants correspondants
    """
    
    # Filtrer par clusterability si demandé
    if exclude_low_quality and min_clusterability > 0:
        df_filtered = df_features[
            df_features['clusterability_index'] >= min_clusterability
        ].copy()
    else:
        df_filtered = df_features.copy()
    
    # Extraire les features numériques (exclure les métadonnées)
    exclude_cols = ['user_id', 'created_at', 'updated_at']
    feature_cols = [col for col in df_filtered.columns if col not in exclude_cols]
    
    X = df_filtered[feature_cols].values
    user_ids = df_filtered['user_id'].values
    
    # Normaliser si demandé
    if normalize:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
    else:
        X_scaled = X
    
    return X_scaled, user_ids, feature_cols


def get_clusterability_stats(df_features: pd.DataFrame) -> dict:
    """
    Renvoie les statistiques du clusterability_index.
    
    Args:
        df_features (DataFrame): Table user_features
        
    Returns:
        dict: Statistiques du clusterability_index
    """
    idx = df_features['clusterability_index']
    
    return {
        'count': len(idx),
        'mean': idx.mean(),
        'median': idx.median(),
        'std': idx.std(),
        'min': idx.min(),
        'max': idx.max(),
        'q25': idx.quantile(0.25),
        'q75': idx.quantile(0.75),
        'high_quality': (idx >= 50).sum(),
        'high_quality_pct': 100 * (idx >= 50).sum() / len(idx),
    }


def filter_by_clusterability(
    df_features: pd.DataFrame,
    min_score: float = 0,
    max_score: float = 100
) -> pd.DataFrame:
    """
    Filtre les utilisateurs par plage de clusterability_index.
    
    Args:
        df_features (DataFrame): Table user_features
        min_score (float): Score minimum (inclus)
        max_score (float): Score maximum (inclus)
        
    Returns:
        DataFrame: Utilisateurs filtrés
    """
    return df_features[
        (df_features['clusterability_index'] >= min_score) &
        (df_features['clusterability_index'] <= max_score)
    ]


# Exemple d'utilisation
if __name__ == '__main__':
    from sqlalchemy import create_engine
    
    DB_CONFIG = {
        "host": "172.18.0.1",
        "database": "postgres",
        "user": "postgres",
        "password": "postgres",
        "port": 5441,
    }
    
    connection_string = f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(connection_string)
    
    # Charger les features
    df = load_user_features(engine)
    print(f"Chargé {len(df)} utilisateurs")
    
    # Statistiques de clusterability
    stats = get_clusterability_stats(df)
    print(f"\nStatistiques clusterability_index:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Préparer les données pour le clustering (utilisateurs de haute qualité)
    X_scaled, user_ids, feature_names = prepare_clustering_data(
        df, 
        min_clusterability=50,
        normalize=True
    )
    
    print(f"\nMatrice de clustering: {X_scaled.shape}")
    print(f"  Utilisateurs: {len(user_ids)}")
    print(f"  Features: {len(feature_names)}")
    
    print(f"\nFeatures incluses:")
    for i, fname in enumerate(feature_names, 1):
        print(f"  {i:2d}. {fname}")
