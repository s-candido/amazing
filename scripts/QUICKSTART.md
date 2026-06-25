# RFM Recalculation - Quick Start Guide

## What is This?

A complete toolkit to **repair and recalculate RFM (Recency, Frequency, Monetary) scores** for your user segmentation tables in PostgreSQL.

## What's Included?

1. **repair_and_recalculate_rfm.py** - Main command-line script
2. **rfm_utils.py** - Reusable Python module for RFM calculations
3. **RFM_Recalculation_Example.ipynb** - Jupyter notebook with examples
4. **README_RFM.md** - Comprehensive documentation

## Getting Started (5 Minutes)

### 1. Install Dependencies

```bash
pip install -r requirements_rfm.txt
```

### 2. Test the Connection

```bash
python -c "from sqlalchemy import create_engine; \
  create_engine('postgresql://postgres:postgres@172.18.0.1:5441/postgres').connect(); \
  print('✓ Connection OK')"
```

### 3. Preview Changes (DRY RUN)

```bash
python repair_and_recalculate_rfm.py --dry-run
```

This shows what **would** be updated without making changes.

### 4. Update the Database

```bash
python repair_and_recalculate_rfm.py
```

That's it! Your tables now have recalculated RFM scores.

## Understanding RFM

| Metric | Meaning | Weight | Better = |
|--------|---------|--------|----------|
| **R**ecency | Days since last purchase | Higher score = recent | Lower days |
| **F**requency | Number of purchases | Higher score = active | More purchases |
| **M**onetary | Total amount spent | Higher score = valuable | More spending |

### Scoring

Each metric gets a score from **0-2**:
- **0** = Low/bad (old, inactive, cheap)
- **1** = Medium (okay)
- **2** = High/good (recent, active, expensive)

### Segments

Segments are derived from R+F+M sum (total 0-6):
- **Segment 0** (0-1): At-risk/dormant
- **Segment 1** (2): Need attention
- **Segment 2** (3): Stable
- **Segment 3** (4-5): Promising
- **Segment 4** (6): Champions

## Common Commands

### Update All Tables
```bash
python repair_and_recalculation_rfm.py
```

### Update Specific Table (with preview)
```bash
python repair_and_recalculate_rfm.py --table user_segment_agglomerative --dry-run
```

### Update Tables Matching Pattern
```bash
python repair_and_recalculate_rfm.py --pattern Agglomerative
```

### Get Help
```bash
python repair_and_recalculate_rfm.py --help
```

## Using in Python/Jupyter

```python
from rfm_utils import RFMCalculator
import pandas as pd

# Initialize calculator
calc = RFMCalculator()

# Calculate RFM for your dataframe
df_with_rfm = calc.calculate_rfm(df)

# Get summary statistics
summary = calc.get_segment_summary(df_with_rfm)
print(summary)

# Get interpretation of a segment
interp = calc.get_segment_interpretation(4)  # Segment 4 = Champions
print(interp)
```

## Configuration (Optional)

Edit the `RFM_CONFIG` dict in the script to customize thresholds:

```python
RFM_CONFIG = {
    # Recency: Lower is better (more recent)
    'r_column': 'days_since_last_event',
    'r_thresholds': [30, 150],      # <= 30 (score 2), <= 150 (score 1), else (score 0)
    'r_scores': [2, 1, 0],
    
    # Frequency: Higher is better (more purchases)
    'f_column': 'total_purchases',
    'f_thresholds': [2, 10],        # < 2 (score 0), < 10 (score 1), else (score 2)
    'f_scores': [0, 1, 2],
    
    # Monetary: Higher is better (more spent)
    'm_column': 'total_spent',
    'm_thresholds': [20, 50],       # < 20 (score 0), < 50 (score 1), else (score 2)
    'm_scores': [0, 1, 2],
    
    'segment_thresholds': [0, 2, 3, 4, 6],
}
```

## Verify Results

After updating, check your database:

```sql
-- Segment distribution
SELECT segment, COUNT(*) FROM user_segment_agglomerative GROUP BY segment;

-- Check timestamp
SELECT MAX(processed_at), MIN(processed_at) FROM user_segment_agglomerative;

-- RFM score distribution
SELECT recency, frequency, monetary, COUNT(*) 
FROM user_segment_agglomerative 
GROUP BY recency, frequency, monetary;
```

## Troubleshooting

### ❌ Connection Error
```
Failed to connect to database
```
**→** Check DB_CONFIG values match your PostgreSQL setup

### ❌ Missing Column
```
Missing columns: ['total_purchases']
```
**→** The script tries common variations. If not found, update `f_column` in RFM_CONFIG

### ❌ Permission Denied
```
permission denied for schema public
```
**→** Ensure your PostgreSQL user has ALTER table permissions

## Next Steps

1. ✅ Run with `--dry-run` to preview changes
2. ✅ Review the output and distribution
3. ✅ Run without `--dry-run` to apply changes
4. ✅ Verify using SQL queries above
5. ✅ Update your dashboard/analysis with new scores

## Support

- See **README_RFM.md** for detailed documentation
- See **RFM_Recalculation_Example.ipynb** for Jupyter examples
- Check log output for detailed error messages

---

**Happy RFM Segmenting! 🚀**
