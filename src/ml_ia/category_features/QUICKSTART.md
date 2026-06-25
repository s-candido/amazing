# QUICK START - Feature Engineering Utilisateurs

## Démarrage Rapide

### 1. Installation des dépendances
```bash
cd src/ml_ia/category_features
pip install -r requirements.txt
```

### 2. Lancer le notebook
```bash
jupyter notebook user_features_engineering.ipynb
```

### 3. Exécuter toutes les cellules
- Démarrer par la première cellule et exécuter chaque cellule en ordre
- Le notebook testera la connexion à PostgreSQL et lancera le workflow complet

## Résultat Attendu

À la fin de l'exécution, vous aurez:

1. **Table PostgreSQL `user_features`** créée avec:
   - ✓ 14-16 colonnes numériques
   - ✓ ~1000-100,000 utilisateurs (selon votre dataset)
   - ✓ Indice de clusterabilité pour chaque utilisateur

2. **Console Output** montrant:
   - Statistiques descriptives
   - Distribution du clusterability_index
   - Matrice de corrélation des features
   - Liste complète des colonnes

## Utilisation des Features

### Via Python
```python
from sqlalchemy import create_engine
from user_features_utils import load_user_features, prepare_clustering_data

# Créer l'engine
engine = create_engine('postgresql://...')

# Charger les features
df = load_user_features(engine)

# Filtrer utilisateurs de haute qualité et normaliser
X_scaled, user_ids = prepare_clustering_data(df, min_clusterability=50)

# Utiliser pour clustering
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=5)
clusters = kmeans.fit_predict(X_scaled)
```

### Via SQL
```sql
-- Charger les 5 meilleurs utilisateurs
SELECT user_id, nb_events, clusterability_index
FROM user_features
ORDER BY clusterability_index DESC
LIMIT 5;

-- Filtrer par plage de clusterability
SELECT *
FROM user_features
WHERE clusterability_index >= 50
AND clusterability_index <= 80;

-- Statistiques
SELECT 
    ROUND(AVG(clusterability_index), 2) as avg_clusterability,
    MIN(clusterability_index) as min_index,
    MAX(clusterability_index) as max_index,
    COUNT(*) as total_users
FROM user_features;
```

## Cas d'Usage Avancés

### 1. Clustering avec Feature Selection
```python
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# Charger les features
X_scaled, user_ids = prepare_clustering_data(df, min_clusterability=50)

# PCA pour réduction de dimensión
pca = PCA(n_components=5)
X_pca = pca.fit_transform(X_scaled)

# Clustering
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=5)
df['cluster'] = kmeans.fit_predict(X_pca)
```

### 2. Analyse des Clusters
```python
# Ajouter les clusters à la base
results = df_features.copy()
results['cluster'] = clusters

# Statistiques par cluster
summary = results.groupby('cluster').agg({
    'clusterability_index': ['mean', 'count'],
    'nb_events': 'mean',
    'total_spent': 'mean',
}).round(2)

print(summary)
```

### 3. Monitoring avec Airflow
```bash
# Copier le DAG
cp dags/feature_engineering_dag.py /path/to/airflow/dags/

# Le DAG s'exécutera quotidiennement à 2h du matin
# Vérifier dans Airflow UI: Admin > DAGs > user_features_engineering
```

## Troubleshooting

### Erreur de connexion PostgreSQL
- Vérifier que PostgreSQL est accessible à `172.18.0.1:5441`
- Vérifier les credentials dans `DB_CONFIG`
- Tester: `psql -h 172.18.0.1 -p 5441 -U postgres`

### Table `all_event` non trouvée
- Assurez-vous que les données ont été importées
- Vérifier dans Pgadmin que `all_event` existe
- Voir la section d'inspection du notebook

### Peu de features créées
- Vérifier que le `category_code` existe et contient des hiérarchies
- Afficher les colonnes disponibles: `df_events.columns`

### Clusterability_index too low
- Peut indiquer un dataset avec peu d'événements par utilisateur
- Cela est normal et reflète la qualité réelle des données
- Filtrer les utilisateurs avec `min_clusterability >= 50`

## Architecture de Données

```
PostgreSQL (172.18.0.1:5441)
│
├── all_event (source)
│   ├── event_time
│   ├── user_id
│   ├── category_code
│   ├── event_type
│   └── price
│
└── user_features (destination) ← NOTEBOOK GÉNÈRE
    ├── user_id (PRIMARY KEY)
    ├── nb_events
    ├── session_intensity
    ├── total_spent
    ├── category_entropy
    ├── ratio_cat_*
    ├── clusterability_index
    ├── created_at
    └── updated_at
```

## Metrics Clés

- **Taux de Couverture** : % d'utilisateurs avec features créées
- **Clusterability Moyen** : Qualité globale des profils utilisateurs
- **Nombre de Features** : 14-16 par défaut (ajustable)
- **Diversité Catégorique** : Entropie moyenne (0-log2(n_cat))

## Contact & Support

Pour des questions ou modifications:
1. Consulter le [README.md](README.md)
2. Examiner les commentaires dans le notebook
3. Vérifier les docstrings des fonctions en Python

---

**Version**: 1.0  
**Dernière mise à jour**: 2024  
**Auteur**: Feature Engineering Team
