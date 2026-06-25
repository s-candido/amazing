"""
Airflow DAG for RFM Score Recalculation

This DAG recalculates RFM (Recency, Frequency, Monetary) scores for user segment tables
on a scheduled basis.

Usage:
    1. Copy this file to your dags/ directory
    2. Update the paths and configuration as needed
    3. Enable the DAG in Airflow UI
    
Schedule:
    - Default: Weekly (adjust as needed)
    - Can be triggered manually
"""

from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup

# ==================== Configuration ====================

# Project paths
PROJECT_ROOT = Path("/home/c-enjalbert/Documents/Github/MSPR/bloc_2/amazing_airflow/amazing")
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SCRIPT_PATH = SCRIPTS_DIR / "repair_and_recalculate_rfm.py"

# Logging
logger = logging.getLogger(__name__)

# Default arguments for the DAG
default_args = {
    'owner': 'data-team',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2026, 3, 1),
    'depends_on_past': False,
}

# ==================== DAG Definition ====================

dag = DAG(
    'rfm_score_recalculation',
    default_args=default_args,
    description='Recalculate RFM (Recency, Frequency, Monetary) scores for user segments',
    schedule_interval='@weekly',  # Weekly schedule, adjust as needed
    catchup=False,
    tags=['rfm', 'segmentation', 'user-profiles'],
)

# ==================== Python Functions ====================

def check_script_exists() -> bool:
    """Verify the RFM script exists and is executable."""
    if not SCRIPT_PATH.exists():
        raise FileNotFoundError(f"RFM script not found at: {SCRIPT_PATH}")
    
    logger.info(f"✓ RFM script found at: {SCRIPT_PATH}")
    return True


def run_rfm_recalculation_dry_run(**context) -> str:
    """
    Run RFM recalculation in dry-run mode to preview changes.
    Useful for validation before actual update.
    """
    logger.info("=" * 70)
    logger.info("Running RFM Recalculation (DRY RUN)")
    logger.info("=" * 70)
    
    cmd = [
        'python',
        str(SCRIPT_PATH),
        '--dry-run'  # Preview without making changes
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        logger.info("STDOUT:")
        logger.info(result.stdout)
        
        if result.stderr:
            logger.warning("STDERR:")
            logger.warning(result.stderr)
        
        if result.returncode != 0:
            raise Exception(f"Script failed with return code {result.returncode}")
        
        logger.info("✓ Dry run completed successfully")
        return result.stdout
        
    except subprocess.TimeoutExpired:
        raise Exception("RFM recalculation timed out after 5 minutes")
    except Exception as e:
        logger.error(f"✗ Dry run failed: {e}")
        raise


def run_rfm_recalculation_full(**context) -> str:
    """
    Run RFM recalculation to actually update the database.
    Should be preceded by dry-run task.
    """
    logger.info("=" * 70)
    logger.info("Running RFM Recalculation (FULL UPDATE)")
    logger.info("=" * 70)
    
    cmd = [
        'python',
        str(SCRIPT_PATH)
        # No --dry-run flag, will actually update database
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for actual updates
        )
        
        logger.info("STDOUT:")
        logger.info(result.stdout)
        
        if result.stderr:
            logger.warning("STDERR:")
            logger.warning(result.stderr)
        
        if result.returncode != 0:
            raise Exception(f"Script failed with return code {result.returncode}")
        
        logger.info("✓ RFM recalculation completed successfully")
        return result.stdout
        
    except subprocess.TimeoutExpired:
        raise Exception("RFM recalculation timed out after 10 minutes")
    except Exception as e:
        logger.error(f"✗ Update failed: {e}")
        raise


def run_rfm_for_table(table_name: str, **context) -> str:
    """
    Recalculate RFM for a specific table.
    Can be parameterized for different models.
    """
    logger.info(f"Recalculating RFM for table: {table_name}")
    
    cmd = [
        'python',
        str(SCRIPT_PATH),
        '--table', table_name
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        logger.info(result.stdout)
        
        if result.returncode != 0:
            raise Exception(f"Failed to update {table_name}")
        
        return result.stdout
        
    except Exception as e:
        logger.error(f"✗ Error processing {table_name}: {e}")
        raise


def verify_updates(query: str, **context) -> dict:
    """
    Verify RFM scores were calculated by running a validation query.
    """
    logger.info("Verifying RFM updates...")
    
    from sqlalchemy import create_engine, text
    
    db_config = {
        "host": "172.18.0.1",
        "database": "postgres",
        "user": "postgres",
        "password": "postgres",
        "port": 5441,
    }
    
    try:
        engine = create_engine(
            f"postgresql+psycopg2://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
        
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
        
        logger.info(f"✓ Verification query returned {len(rows)} rows")
        logger.info(f"Sample: {rows[:3] if rows else 'No results'}")
        
        return {
            'checks_passed': len(rows) > 0,
            'row_count': len(rows),
            'sample_data': str(rows[:3]) if rows else None
        }
        
    except Exception as e:
        logger.error(f"✗ Verification failed: {e}")
        raise


# ==================== Task Definitions ====================

# Task: Check prerequisites
check_script = PythonOperator(
    task_id='check_prerequisites',
    python_callable=check_script_exists,
    dag=dag,
)

# Task: Run dry-run
dry_run_task = PythonOperator(
    task_id='run_dry_run',
    python_callable=run_rfm_recalculation_dry_run,
    dag=dag,
)

# Task: Run full update
full_update_task = PythonOperator(
    task_id='run_full_update',
    python_callable=run_rfm_recalculation_full,
    dag=dag,
)

# Task: Verify updates
verify_task = PythonOperator(
    task_id='verify_updates',
    python_callable=verify_updates,
    op_kwargs={
        'query': """
            SELECT segment, COUNT(*) as count 
            FROM user_segment_agglomerative 
            GROUP BY segment 
            ORDER BY segment;
        """
    },
    dag=dag,
)

# Task: Send notification
notify_task = BashOperator(
    task_id='send_notification',
    bash_command='echo "✓ RFM recalculation completed successfully"',
    dag=dag,
)

# Alternative: Process individual tables in parallel
with TaskGroup('process_tables', dag=dag) as process_tables_group:
    """Process RFM for each clustering model in parallel."""
    
    tables_to_process = [
        'user_segment_agglomerative',
        'user_segment_birch',
        'user_segment_kmeans',
        # Add more tables as needed
    ]
    
    for table in tables_to_process:
        PythonOperator(
            task_id=f'process_{table}',
            python_callable=run_rfm_for_table,
            op_kwargs={'table_name': table},
        )

# ==================== Task Dependencies ====================

# Simple linear workflow
check_script >> dry_run_task >> full_update_task >> verify_task >> notify_task

# Alternative: Process tables in parallel
# check_script >> [process_tables_group] >> verify_task >> notify_task

# ==================== Additional DAGs (Optional) ====================

# For manual intervention if needed
dag_manual = DAG(
    'rfm_score_recalculation_manual',
    default_args={
        'owner': 'data-team',
        'retries': 1,
        'start_date': datetime(2026, 3, 1),
    },
    description='Manual trigger for RFM recalculation (dry-run)',
    schedule_interval=None,  # Manual only
    tags=['rfm', 'manual', 'user-profiles'],
)

manual_task = PythonOperator(
    task_id='manual_rfm_dry_run',
    python_callable=run_rfm_recalculation_dry_run,
    dag=dag_manual,
)

# For daily validation
dag_validation = DAG(
    'rfm_validation',
    default_args={
        'owner': 'data-team',
        'retries': 1,
        'start_date': datetime(2026, 3, 1),
    },
    description='Daily validation of RFM scores',
    schedule_interval='@daily',
    tags=['rfm', 'validation'],
)

validation_task = PythonOperator(
    task_id='validate_rfm_scores',
    python_callable=verify_updates,
    op_kwargs={
        'query': """
            SELECT 
                'segment_distribution' as check_type,
                COUNT(DISTINCT segment) as unique_segments,
                COUNT(*) as total_rows
            FROM user_segment_agglomerative
            WHERE processed_at >= NOW() - INTERVAL '1 day';
        """
    },
    dag=dag_validation,
)
