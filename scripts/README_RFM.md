# RFM Score Recalculation Script

## Overview

This script repairs and recalculates **RFM (Recency, Frequency, Monetary)** scores for user segment tables in PostgreSQL. It's designed to fix corrupted or outdated RFM values and replace them with fresh calculations based on configurable scoring rules.

## Features

✅ **Automated RFM Calculation**
- Recency (R): Days since last event
- Frequency (F): Number of purchases
- Monetary (M): Total amount spent

✅ **Flexible Scoring Thresholds**
- Fully configurable scoring boundaries
- Custom segment mapping
- Easy to adjust for business needs

✅ **Database Operations**
- Batch processing of multiple tables
- Dry-run mode for safety
- Transaction-safe updates
- Detailed logging

✅ **User-Friendly CLI**
- Process all tables at once
- Target specific tables
- Pattern matching support
- Clear progress reporting

## Installation

### Prerequisites

```bash
python >= 3.8
```

### Dependencies

```bash
pip install pandas sqlalchemy psycopg2-binary numpy
```

Or use the provided requirements:
```bash
pip install -r requirements_rfm.txt
```

## Configuration

The script uses the following RFM configuration:

```python
RFM_CONFIG = {
    # Recency: Days since last event
    'r_column': 'days_since_last_event',
    'r_thresholds': [30, 150],      # days
    'r_scores': [2, 1, 0],          # [recent, medium, old]
    
    # Frequency: Number of purchases
    'f_column': 'total_purchases',
    'f_thresholds': [2, 10],        # count
    'f_scores': [0, 1, 2],          # [low, medium, high]
    
    # Monetary: Total amount spent
    'm_column': 'total_spent',
    'm_thresholds': [20, 50],       # currency
    'm_scores': [0, 1, 2],          # [low, medium, high]
    
    # Segment: Derived from R+F+M sum
    'segment_thresholds': [0, 2, 3, 4, 6],
}
```

### Database Configuration

Update the `DB_CONFIG` in the script if needed:

```python
DB_CONFIG = {
    "host": "172.18.0.1",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
    "port": 5441,
}
```

## Usage

### Basic Usage

Update **all** user_segment tables:
```bash
python repair_and_recalculate_rfm.py
```

### Dry-Run Mode (Recommended First Step)

Preview changes without modifying the database:
```bash
python repair_and_recalculate_rfm.py --dry-run
```

### Target Specific Table

Update a single table:
```bash
python repair_and_recalculate_rfm.py --table user_segment_agglomerative
```

With dry-run:
```bash
python repair_and_recalculate_rfm.py --table user_segment_agglomerative --dry-run
```

### Pattern Matching

Update tables matching a pattern:
```bash
python repair_and_recalculate_rfm.py --pattern Agglomerative
```

Or:
```bash
python repair_and_recalculate_rfm.py --pattern "KMeans"
```

## RFM Scoring Logic

### Recency (R) - How recent is the customer?

| Days Since Last Event | Score | Meaning |
|----------------------|-------|---------|
| ≤ 30 days            | 2     | Very recent (hot) |
| 31 - 150 days        | 1     | Somewhat recent (warm) |
| > 150 days           | 0     | Not recent (cold) |

**Logic**: Lower days = higher score (more valuable) → range [0, 2]

### Frequency (F) - How often does the customer purchase?

| Number of Purchases | Score | Meaning |
|--------------------|-------|---------|
| < 2                | 0     | Low frequency |
| 2 - 9              | 1     | Medium frequency |
| ≥ 10               | 2     | High frequency |

**Logic**: More purchases = higher score → range [0, 2]

### Monetary (M) - How much does the customer spend?

| Total Spent | Score | Meaning |
|-------------|-------|---------|
| < $20      | 0     | Low spender |
| $20 - $49  | 1     | Medium spender |
| ≥ $50      | 2     | High spender |

**Logic**: More spending = higher score → range [0, 2]

### Segment - RFM Score Sum

The **Segment** is calculated from the sum of R + F + M scores (range: 0-6):

| RFM Sum | Segment | Type |
|---------|---------|------|
| 0 - 1   | 0       | Low-value |
| 2       | 1       | Medium-low |
| 3       | 2       | Medium |
| 4 - 5   | 3       | Medium-high |
| 6       | 4       | High-value |

## Output Columns

The script adds/updates these columns:

- **recency** (0-2): Recency score
- **frequency** (0-2): Frequency score
- **monetary** (0-2): Monetary score
- **segment** (0-4): Calculated segment
- **processed_at** (timestamp): When scores were calculated

## Example Output

```
====================================================================
RFM Score Recalculation Tool
====================================================================
RFM Configuration:
  Recency: days_since_last_event <= 30 (score 2), <= 150 (score 1), > 150 (score 0)
  Frequency: total_purchases < 2 (score 0), < 10 (score 1), >= 10 (score 2)
  Monetary: total_spent < 20 (score 0), < 50 (score 1), >= 50 (score 2)
====================================================================

► Processing table: user_segment_agglomerative
  Recency column: days_since_last_event
  Frequency column: total_purchases
  Monetary column: total_spent
✓ Loaded 1000 rows from user_segment_agglomerative
✓ RFM scores calculated
  - Recency distribution: {0: 300, 1: 400, 2: 300}
  - Frequency distribution: {0: 500, 1: 350, 2: 150}
  - Monetary distribution: {0: 400, 1: 350, 2: 250}
  - Segment distribution: {0: 200, 1: 250, 2: 300, 3: 150, 4: 100}
✓ Updated 1000 rows in user_segment_agglomerative

====================================================================
Processing Complete: 1/1 tables successfully updated
====================================================================
```

## Troubleshooting

### Connection Issues

**Error**: `Failed to connect to database`

**Solution**: Check DB_CONFIG parameters:
```bash
# Test connection
python -c "from sqlalchemy import create_engine; \
  conn = create_engine('postgresql://postgres:postgres@172.18.0.1:5441/postgres'); \
  print('Connected successfully')"
```

### Missing Columns

**Warning**: `Missing columns: ['total_purchases']`

**Solution**: The script tries common column name variations. If a column still can't be found:
1. Check the actual table structure: `SELECT * FROM table_name LIMIT 1;`
2. Update the column name in `RFM_CONFIG`

### Large Table Performance

For tables with millions of rows:
1. Use `--table` to process one at a time
2. Consider increasing available memory
3. Add indexing to source columns for better performance

## Advanced: Customizing Thresholds

To change the RFM scoring rules, edit the `RFM_CONFIG` dictionary:

```python
RFM_CONFIG = {
    'r_column': 'days_since_last_event',
    'r_thresholds': [7, 30],        # More strict: 7 days, 30 days
    'r_scores': [2, 1, 0],
    
    'f_column': 'total_purchases',
    'f_thresholds': [5, 20],        # Higher thresholds
    'f_scores': [0, 1, 2],
    
    'm_column': 'total_spent',
    'm_thresholds': [100, 500],     # Higher thresholds
    'm_scores': [0, 1, 2],
    
    'segment_thresholds': [0, 2, 3, 4, 6],  # Same segment logic
}
```

Then run the script normally - it will use the new configuration.

## Performance Tips

1. **Use Dry-Run First**: Always test with `--dry-run` before committing changes
2. **Process One Table**: For large tables, use `--table` option
3. **Monitor Disk Space**: Ensure sufficient disk space for table replacement
4. **Off-Peak Hours**: Run during low-traffic hours if possible

## Integration with Airflow

To integrate this script into an Airflow DAG:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import subprocess

def recalculate_rfm(**context):
    result = subprocess.run([
        'python', 
        '/path/to/repair_and_recalculate_rfm.py',
        '--pattern', 'Agglomerative'  # or any pattern
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"RFM recalculation failed: {result.stderr}")
    
    return result.stdout

dag = DAG(
    'rfm_recalculation',
    start_date=datetime(2026, 3, 1),
    schedule_interval='@weekly'  # Run weekly
)

task = PythonOperator(
    task_id='recalculate_rfm',
    python_callable=recalculate_rfm,
    dag=dag
)
```

## Validation

After running, verify the results:

```sql
-- Check segment distribution
SELECT segment, COUNT(*) as count 
FROM user_segment_agglomerative 
GROUP BY segment 
ORDER BY segment;

-- Check RFM score distribution
SELECT 
    recency, frequency, monetary, 
    COUNT(*) as count 
FROM user_segment_agglomerative 
GROUP BY recency, frequency, monetary 
ORDER BY recency, frequency, monetary;

-- Check when last processed
SELECT MAX(processed_at), MIN(processed_at) 
FROM user_segment_agglomerative;
```

## Support & Issues

For issues or questions:
1. Check the loggers output for detailed error messages
2. Run with `--dry-run` to see what would be changed
3. Verify database connection and table structure
4. Check available disk space

## License & Attribution

Created for the Amazing Airflow project - MSPR Bloc 2

---

**Happy RFM Segmenting! 🚀**
