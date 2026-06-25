# Feature Engineering Utilisateurs pour le Clustering

## Description

Ce dossier contient un notebook Jupyter complet (en français) dédié à la construction de features utilisateurs pertinentes pour le clustering.

### Fichier Principal
- **`user_features_engineering.ipynb`** : Notebook Jupyter exécutable de bout en bout

## Objectif

Transformer les données brutes d'événements utilisateurs (table `all_event`) en une matrice de features numériques compacte et pertinente stockée dans PostgreSQL sous la table `user_features`.

## Architecture du Notebook

Le notebook est structuré en 10 sections + conclusion :

### 1. **Configuration et Connexion PostgreSQL**
   - Import des bibliothèques requises (pandas, numpy, sqlalchemy, psycopg2, sklearn, matplotlib)
   - Configuration de la base de données
   - Test de connectivité

### 2. **Inspection des Tables Source**
   - Chargement des tables `all_event` et `user_event`
   - Analyse de la structure et des données
   - Exploration des `category_code`

### 3. **Nettoyage et Préparation**
   - Suppression des valeurs manquantes critiques
   - Conversion des types de données
   - Standardisation des formats

### 4. **Parsing de la Hiérarchie Category_Code**
   - Extraction des niveaux hiérarchiques (cat_lvl1, cat_lvl2, cat_lvl3)
   - Analyse de la distribution des catégories niveau 1

### 5. **Feature Engineering au Niveau Utilisateur**
   
   **Features créées :**
   - **Comportementales** : nb_events, nb_sessions, session_intensity
   - **Monétaires** : nb_purchases, purchase_rate, total_spent, avg_price_viewed
   - **Diversité** : nb_distinct_cat_lvl1, category_entropy
   - **Ratios de catégories** : 5 ratios basés sur les top catégories du dataset

### 6. **Calcul du Clusterability Index**
   - Indice composite (0-100) basé sur :
     - Nombre d'événements
     - Diversité catégorique
     - Comportement monétaire
     - Nombre de sessions
     - Complétude des données

### 7. **Sélection et Validation des Features**
   - Sélection d'un set compact de features
   - Gestion des NaN et valeurs infinies
   - Analyse de corrélation entre features
   - Visualisation de la matrice de corrélation

### 8. **Création de la Table SQL**
   - Génération du DDL SQL
   - Création de la table `user_features` si elle n'existe pas
   - Création d'index pour les requêtes

### 9. **Insertion et Upsert**
   - Insertion des données dans PostgreSQL
   - Support du upsert (ON CONFLICT DO UPDATE)
   - Gestion des transactions et erreurs

### 10. **Vérification Finale**
   - Chargement de la table depuis la base
   - Aperçu des données (head/tail)
   - Statistiques descriptives
   - Distribution du clusterability_index
   - Liste complète des colonnes retenues

## Configuration de la Base de Données

```python
DB_CONFIG = {
    "host": "172.18.0.1",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
    "port": 5441,
}
```

## Structure de la Table `user_features`

```sql
CREATE TABLE user_features (
    user_id BIGINT PRIMARY KEY,
    nb_events NUMERIC(12, 4),
    nb_sessions NUMERIC(12, 4),
    nb_purchases NUMERIC(12, 4),
    purchase_rate NUMERIC(12, 4),
    session_intensity NUMERIC(12, 4),
    total_spent NUMERIC(12, 4),
    avg_price_viewed NUMERIC(12, 4),
    nb_distinct_cat_lvl1 NUMERIC(12, 4),
    category_entropy NUMERIC(12, 4),
    ratio_cat_<cat1> NUMERIC(12, 4),
    ratio_cat_<cat2> NUMERIC(12, 4),
    ratio_cat_<cat3> NUMERIC(12, 4),
    ratio_cat_<cat4> NUMERIC(12, 4),
    ratio_cat_<cat5> NUMERIC(12, 4),
    clusterability_index NUMERIC(12, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Utilisation pour le Clustering

```python
import pandas as pd
from sqlalchemy import create_engine

# Charger les features
df = pd.read_sql_table('user_features', engine)

# Filtrer les utilisateurs clusterisables (optional)
df_clusterizable = df[df['clusterability_index'] >= 50]

# Extraire les features numériques
X = df_clusterizable.drop(['user_id', 'created_at', 'updated_at'], axis=1)

# Normaliser (recommandé)
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Appliquer le clustering (exemple: KMeans)
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=5, random_state=42)
df_clusterizable['cluster'] = kmeans.fit_predict(X_scaled)
```

## Prérequis

### Bibliothèques Python
```
pandas>=1.0.0
numpy>=1.18.0
sqlalchemy>=1.3.0
psycopg2-binary>=2.8.0
scikit-learn>=0.24.0
matplotlib>=3.1.0
seaborn>=0.11.0
```

### Accès Base de Données
- PostgreSQL 12+ accessible à `172.18.0.1:5441`
- Tables source : `all_event` et optionnellement `user_event`
- Support du upsert SQL (`ON CONFLICT DO UPDATE`)

## Exécution du Notebook

```bash
# 1. Installer les dépendances
pip install pandas numpy sqlalchemy psycopg2-binary scikit-learn matplotlib seaborn

# 2. Ouvrir le notebook
jupyter notebook user_features_engineering.ipynb

# 3. Exécuter les cellules de haut en bas
# Chaque section peut être exécutée indépendamment une fois les données chargées
```

## Notes Importantes

1. **Données manquantes** : Les values nulles dans les features comportementales/monétaires sont remplacées par 0
2. **Valeurs infinies** : Gérées en remplacement par 0
3. **Clusterability Index** : Score composite entre 0 et 100 indiquant la richesse du profil utilisateur
4. **Catégories** : Seul le niveau 1 (`cat_lvl1`) est utilisé pour les features finales
5. **Ratios** : Basés dynamiquement sur les top 5 catégories du dataset
6. **Upsert** : Si un utilisateur existe déjà, ses features sont mises à jour

## Sortie du Notebook

À la fin de l'exécution, le notebook affiche :
- Aperçu des premières et dernières lignes de `user_features`
- Statistiques descriptives de toutes les features
- Distribution du `clusterability_index`
- **Liste complète des colonnes retenues** pour le clustering

## Maintenance

### Mise à jour des Features
Pour réutiliser le notebook avec des nouvelles données :
1. Les nouvelles données d'événements sont chargées
2. Les features existantes sont **remplacées** (upsert)
3. Les statistiques du clusterability_index se **réajustent**

### Vérification de la Qualité
```sql
-- Vérifier le nombre d'utilisateurs
SELECT COUNT(*) FROM user_features;

-- Vérifier les mises à jour récentes
SELECT COUNT(*) FROM user_features 
WHERE updated_at > NOW() - INTERVAL '1 day';

-- Distribution du clusterability_index
SELECT 
    FLOOR(clusterability_index / 10) * 10 as index_range,
    COUNT(*) as nb_users
FROM user_features
GROUP BY FLOOR(clusterability_index / 10)
ORDER BY index_range;
```

## Auteur

Feature engineering pour Amazing Airflow - Clustering utilisateurs

## License

Interne - Amazing Airflow Project
