"""Apache Airflow DAG: orchestration layer at the bottom of the DFD.
Copy/symlink into your Airflow dags/ folder and ensure the project is on PYTHONPATH.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.datamart import build as p3
from src.extract import run as p1
from src.raw import run as p0
from src.transform import run as p2

default_args = {
    "owner": "data-eng",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="dfd_full_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule="*/30 * * * *",     # every 30 min -> "continuous"
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
) as dag:
    land_raw = PythonOperator(task_id="P0_land_raw", python_callable=p0.run)
    extract = PythonOperator(task_id="P1_extract", python_callable=p1.run)
    transform_load = PythonOperator(task_id="P2_transform_load", python_callable=p2.run)
    build_mart = PythonOperator(task_id="P3_build_datamart", python_callable=p3.run)

    land_raw >> extract >> transform_load >> build_mart
