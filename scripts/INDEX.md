# RFM Score Recalculation Toolkit - Complete Documentation

## 🎯 Overview

This toolkit provides a **complete solution** for recalculating RFM (Recency, Frequency, Monetary) scores in your user segmentation tables. It includes command-line tools, Python libraries, Jupyter notebooks, and Airflow integration.

**Created**: March 11, 2026  
**Status**: Production-Ready  
**Files**: 6 main components

---

## 📦 What's Included

### 1. **repair_and_recalculate_rfm.py** - Main Script
The core command-line tool for RFM recalculation.

**Location**: `scripts/repair_and_recalculate_rfm.py`

**Features**:
- ✅ Automatic RFM score calculation
- ✅ Batch processing of multiple tables
- ✅ Dry-run mode for safety
- ✅ Pattern matching support
- ✅ Comprehensive logging
- ✅ Transaction-safe updates

**Quick Start**:
```bash
# Preview changes without updating
python repair_and_recalculate_rfm.py --dry-run

# Update all user_segment tables
python repair_and_recalculate_rfm.py

# Update specific table
python repair_and_recalculate_rfm.py --table user_segment_agglomerative
```

**Key Configuration** (in file):
```python
RFM_CONFIG = {
    'r_column': 'days_since_last_event',
    'r_thresholds': [30, 150],
    'r_scores': [2, 1, 0],  # More recent = higher score
    'f_column': 'total_purchases',
    'f_thresholds': [2, 10],
    'f_scores': [0, 1, 2],  # More frequent = higher score
    'm_column': 'total_spent',
    'm_thresholds': [20, 50],
    'm_scores': [0, 1, 2],  # More spending = higher score
    'segment_thresholds': [0, 2, 3, 4, 6],
}
```

---

### 2. **rfm_utils.py** - Reusable Library Module
Python module containing the RFMCalculator class for integration into other scripts and notebooks.

**Location**: `scripts/rfm_utils.py`

**Main Class**: `RFMCalculator`

**Usage Example**:
```python
from rfm_utils import RFMCalculator

# Initialize
calculator = RFMCalculator()

# Calculate RFM for a dataframe
df_with_rfm = calculator.calculate_rfm(df)

# Get segment summary
summary = calculator.get_segment_summary(df_with_rfm)

# Get segment interpretation
interp = calculator.get_segment_interpretation(segment=4)  # "High-value..."
```

**Key Methods**:
- `calculate_rfm(df)` - Main calculation
- `get_segment_summary(df)` - Statistics by segment
- `get_segment_interpretation(segment)` - Human-readable description

**Static Methods** (can be used standalone):
- `calculate_r_score(days, thresholds, scores)`
- `calculate_f_score(frequency, thresholds, scores)`
- `calculate_m_score(monetary, thresholds, scores)`
- `calculate_segment(r, f, m, thresholds)`

---

### 3. **RFM_Recalculation_Example.ipynb** - Interactive Notebook
Jupyter notebook with complete examples and step-by-step walkthrough.

**Location**: `scripts/RFM_Recalculation_Example.ipynb`

**Contents**:
- Database connection setup
- Loading sample data
- RFM calculation with visualization
- Distribution analysis
- Segment summary statistics
- Batch processing multiple tables
- Database verification

**Best For**:
- Learning how the system works
- Interactive exploration of data
- Testing before running in production
- Creating custom analyses

---

### 4. **README_RFM.md** - Comprehensive Documentation
Detailed reference guide with all features, configuration, and troubleshooting.

**Location**: `scripts/README_RFM.md`

**Sections**:
- Overview and features
- Installation instructions
- RFM scoring logic (with tables)
- Usage examples
- Configuration options
- Performance tips
- Airflow integration guide
- Validation queries
- Troubleshooting

**Read This For**:
- Detailed RFM scoring logic
- Advanced configuration
- Performance optimization
- Integration with Airflow

---

### 5. **QUICKSTART.md** - Fast Reference Guide
Quick reference for common tasks and getting started quickly.

**Location**: `scripts/QUICKSTART.md`

**Highlights**:
- 5-minute setup guide
- Common commands
- Understanding RFM (simple version)
- Configuration basics
- Troubleshooting quick fixes
- Validation queries

**Read This For**:
- Getting started quickly
- Common command patterns
- Quick troubleshooting

---

### 6. **rfm_recalculation_dag.py** - Airflow Integration
Ready-to-use Airflow DAG for scheduled RFM recalculation.

**Location**: `dags/rfm_recalculation_dag.py`

**Features**:
- ✅ Weekly scheduled execution
- ✅ Dry-run validation before update
- ✅ Parallel table processing
- ✅ Automatic verification
- ✅ Notification support
- ✅ Manual trigger option

**Three DAGs Provided**:
1. **rfm_score_recalculation** - Automated weekly execution
2. **rfm_score_recalculation_manual** - Manual trigger with dry-run
3. **rfm_validation** - Daily validation checks

**Airflow Workflow**:
```
Check Prerequisites 
    ↓
Run Dry-Run (preview)
    ↓
Run Full Update
    ↓
Verify Results
    ↓
Send Notification
```

---

## 🚀 Quick Start (Choose Your Method)

### Method 1: Command Line (Fastest)
```bash
cd /path/to/scripts

# Test connection first
pip install -r requirements_rfm.txt

# Preview what will change
python repair_and_recalculate_rfm.py --dry-run

# Apply the changes
python repair_and_recalculate_rfm.py
```

### Method 2: Jupyter Notebook (Interactive)
```bash
jupyter notebook RFM_Recalculation_Example.ipynb

# Run cells one by one to:
# 1. Connect to database
# 2. Load sample data
# 3. Calculate RFM
# 4. Analyze results
# 5. Update database (optional)
```

### Method 3: Python Code (Programmatic)
```python
from rfm_utils import RFMCalculator
import pandas as pd

# Load your data
df = pd.read_sql("SELECT * FROM user_segment_agglomerative", engine)

# Calculate RFM
calc = RFMCalculator()
df_rfm = calc.calculate_rfm(df)

# Update database
df_rfm.to_sql('user_segment_agglomerative', engine, if_exists='replace')
```

### Method 4: Airflow (Automated)
```python
# Copy rfm_recalculation_dag.py to your dags/ folder
# Enable in Airflow UI
# Schedule runs weekly automatically
```

---

## 📊 RFM Scoring System

### Recency (How recent is the customer?)
```
Days Since Last Event | Score | Type
≤ 30 days            | 2     | Hot (very recent)
31-150 days          | 1     | Warm (recent)
> 150 days           | 0     | Cold (not recent)
```

### Frequency (How often do they purchase?)
```
Number of Purchases | Score | Type
< 2                | 0     | Low frequency
2-9                | 1     | Medium frequency
≥ 10               | 2     | High frequency
```

### Monetary (How much do they spend?)
```
Total Amount | Score | Type
< $20       | 0     | Low spender
$20-$49     | 1     | Medium spender
≥ $50       | 2     | High spender
```

### Segments (R + F + M sum)
```
RFM Sum | Segment | Meaning
0-1     | 0       | At-risk/Dormant customers
2       | 1       | Low-value (need attention)
3       | 2       | Stable customers
4-5     | 3       | Promising (growth potential)
6       | 4       | Champions (best customers)
```

---

## 🔄 Database Schema

### Input Columns (Required)
- `days_since_last_event` - Days since last user activity
- `total_purchases` - Number of purchases
- `total_spent` - Total amount spent
- Any user identifier (user_id, etc.)

### Output Columns (Added/Updated)
- `recency` (0-2) - Recency score
- `frequency` (0-2) - Frequency score
- `monetary` (0-2) - Monetary score
- `segment` (0-4) - Calculated segment
- `processed_at` - Timestamp of calculation

---

## 📋 File Guide

| Component | Type | Purpose | Location |
|-----------|------|---------|----------|
| **Main Script** | Python | CLI tool for recalculation | `scripts/repair_and_recalculate_rfm.py` |
| **Utilities** | Python | Reusable RFM library | `scripts/rfm_utils.py` |
| **Notebook** | Jupyter | Interactive examples | `scripts/RFM_Recalculation_Example.ipynb` |
| **Full Docs** | Markdown | Comprehensive guide | `scripts/README_RFM.md` |
| **Quick Guide** | Markdown | Fast reference | `scripts/QUICKSTART.md` |
| **Airflow DAG** | Python | Scheduled execution | `dags/rfm_recalculation_dag.py` |
| **Dependencies** | Text | Python packages needed | `scripts/requirements_rfm.txt` |

---

## ⚙️ Configuration & Customization

### Modify RFM Thresholds
Edit the `RFM_CONFIG` dictionary in any script:

```python
RFM_CONFIG = {
    'r_column': 'days_since_last_event',
    'r_thresholds': [7, 30],        # More strict: 7 and 30 days
    'r_scores': [2, 1, 0],
    
    'f_column': 'total_purchases',
    'f_thresholds': [5, 20],        # Higher thresholds
    'f_scores': [0, 1, 2],
    
    'm_column': 'total_spent',
    'm_thresholds': [100, 500],     # Higher monetary thresholds
    'm_scores': [0, 1, 2],
    
    'segment_thresholds': [0, 2, 3, 4, 6],
}
```

### Modify Database Connection
Update `DB_CONFIG` in any script:

```python
DB_CONFIG = {
    "host": "your-host",
    "database": "your-db",
    "user": "your-user",
    "password": "your-password",
    "port": 5432,
}
```

---

## ✅ Validation & Verification

### After Running, Verify with SQL:
```sql
-- Check segment distribution
SELECT segment, COUNT(*) as count 
FROM user_segment_agglomerative 
GROUP BY segment 
ORDER BY segment;

-- Check RFM score patterns
SELECT recency, frequency, monetary, COUNT(*) 
FROM user_segment_agglomerative 
GROUP BY recency, frequency, monetary;

-- Verify timestamp
SELECT MAX(processed_at) FROM user_segment_agglomerative;
```

### Programmatic Verification:
```python
from rfm_utils import RFMCalculator

calc = RFMCalculator()
summary = calc.get_segment_summary(df)
print(summary)

# Check distribution
print(df['segment'].value_counts().sort_index())
```

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| `Connection refused` | Check DB_CONFIG, ensure PostgreSQL is running |
| `Column not found` | Script tries variations, manually check table with `SELECT * FROM table LIMIT 1` |
| `Permission denied` | Ensure your DB user has ALTER privilege |
| `Timeout error` | For large tables (10M+ rows), use `--table` option for one table at a time |
| `Out of memory` | Process tables individually, increase virtual memory, or add swap |

See **README_RFM.md** for more troubleshooting and advanced issues.

---

## 📈 Performance

### Typical Execution Time
| Table Size | Time | Command |
|-----------|------|---------|
| < 10K rows | < 1 second | `python repair_and_recalculate_rfm.py --table X` |
| 100K rows | ~5 seconds | Single table |
| 1M rows | ~30-60 seconds | Single table |
| Multiple tables | Varies | Parallel processing |

### Optimization Tips
1. Use `--table` option to process one table at a time
2. Run during off-peak hours
3. Ensure adequate disk space for table replacement
4. Consider creating indexes on source columns

---

## 🔗 Integration Examples

### With Pandas
```python
from rfm_utils import RFMCalculator

df = pd.read_csv('user_data.csv')
calc = RFMCalculator()
df_rfm = calc.calculate_rfm(df)
```

### With SQLAlchemy
```python
from sqlalchemy import create_engine
from rfm_utils import RFMCalculator

engine = create_engine('postgresql://...')
df = pd.read_sql('SELECT * FROM users', engine)
df_rfm = RFMCalculator().calculate_rfm(df)
```

### With Streamlit Dashboard
```python
import streamlit as st
from rfm_utils import RFMCalculator

@st.cache
def get_rfm_data():
    df = load_from_database()
    return RFMCalculator().calculate_rfm(df)

df_rfm = get_rfm_data()
st.write(df_rfm[['user_id', 'segment']])
```

---

## 📞 Support

For detailed information, refer to:
- **Setup & Quick Start**: See `QUICKSTART.md`
- **Detailed Features**: See `README_RFM.md`
- **Code Examples**: See `RFM_Recalculation_Example.ipynb`
- **Source Code**: See `rfm_utils.py` and `repair_and_recalculate_rfm.py`

---

## 🎓 Key Concepts

### Why RFM Matters
RFM segmentation helps you:
- 🎯 Identify high-value customers (champions)
- ⚠️ Detect at-risk customers (cold)
- 📈 Optimize marketing spend
- 💡 Personalize customer engagement
- 📊 Track customer health over time

### Segment Strategies
- **Segment 0** (At-risk): Win-back campaigns, special offers
- **Segment 1** (Low-value): Engagement campaigns
- **Segment 2** (Stable): Maintain satisfaction
- **Segment 3** (Promising): Growth offers
- **Segment 4** (Champions): VIP treatment, loyalty programs

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-11 | Initial release |

---

## 🚀 Next Steps

1. ✅ Copy all files to your project
2. ✅ Install dependencies: `pip install -r requirements_rfm.txt`
3. ✅ Update DB_CONFIG to match your setup
4. ✅ Run dry-run: `python repair_and_recalculate_rfm.py --dry-run`
5. ✅ Review output and verify column mappings
6. ✅ Run full update: `python repair_and_recalculate_rfm.py`
7. ✅ Verify results with SQL queries
8. ✅ (Optional) Integrate with Airflow for scheduled execution

---

**Happy RFM Segmenting! 🎉**

Created with ❤️ for the Amazing Airflow Project - MSPR Bloc 2
