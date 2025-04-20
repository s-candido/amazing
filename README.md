# 🦆 DuckDB ETL - Analyse Comportementale Utilisateur (Projet Amazing)

Ce projet est un pipeline de traitement de logs utilisateurs pour le marketplace **Amazing**, permettant de transformer des fichiers `.csv` en **features utilisateurs** exploitables pour du clustering ou de la segmentation comportementale.

---

## 🧱 Architecture du projet

### 📁 Données d'entrée
Des fichiers CSV contenant les événements utilisateur :

- `view`, `cart`, `remove_from_cart`, `purchase`
- Colonnes : `event_time`, `event_type`, `product_id`, `category_code`, `price`, `user_id`, `user_session`

### 🗃️ Base DuckDB locale
- Fichier généré : `amazing.duckdb`
- Tables principales :
  - `all_events` : tous les logs concaténés
  - `loaded_files` : suivi des fichiers déjà importés
  - `user_features` : statistiques agrégées par utilisateur

---

## ⚙️ Fonctionnalités

- ✅ Chargement automatique des fichiers `.csv` depuis le dossier `./data`
- ✅ Ingestion dans DuckDB avec vérification anti-doublons
- ✅ Génération de `user_features` enrichie :
  - Vues, paniers, achats, catégories explorées
  - Total dépensé, prix moyen, catégorie préférée
- ✅ Clustering des utilisateurs (`KMeans`)
- ✅ Extraction de groupes comportementaux : acheteurs, curieux, etc.

---

## 📊 Exemple de `user_features`

| user_id | nb_view | nb_cart | nb_achats | total_depense | category_top       |
|---------|---------|---------|-----------|----------------|--------------------|
| 123456  | 15      | 3       | 1         | 89.99          | electronics.phone  |
| 987654  | 32      | 0       | 0         | 0.0            | apparel.shoes      |

---

## 🚀 Utilisation

### 1. Créer le dossier `data/` (s’il n’existe pas déjà)

```bash
mkdir data
```

Place dans ce dossier les fichiers `.csv` à importer (`2019-Oct.csv`, etc.)

### 2. Lancer le script

> 🕒 **Note importante** :  
> Le **premier chargement peut être très long** (plusieurs dizaines de minutes) si les fichiers contiennent des millions de lignes.  
> Ensuite, le script détecte automatiquement les fichiers déjà importés grâce à la table `loaded_files`.

---

## 🔎 Requêtes utiles

### Utilisateurs acheteurs

```sql
SELECT * FROM user_features WHERE nb_achats > 0;
```

### Utilisateurs visiteurs (vues mais pas d’achats)

```sql
SELECT * FROM user_features WHERE nb_view > 0 AND nb_achats = 0;
```

### Catégories les plus vues par utilisateur

```sql
SELECT user_id, category_code, COUNT(*) AS nb_visites
FROM all_events
WHERE event_type = 'view'
GROUP BY user_id, category_code
ORDER BY user_id, nb_visites DESC;
```

---

## 👤 Auteur

Projet MSPR Bloc 2 – Étudiant CDA  
Powered by 🦆 DuckDB, 💡 Pandas, 🤖 Scikit-learn
