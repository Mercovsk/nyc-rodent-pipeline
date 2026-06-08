import os, sys
sys.path.insert(0, '/opt/airflow/pipeline')

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from datetime import datetime, timedelta

default_args = {
    'owner': 'rovic',
    'retries': 1,
    'retry_dalay': timedelta(minutes=5),
}

def run_silver_layer():
    from silver.transform import process_directory
    data_dir = os.path.join('/opt/airflow/pipeline', 'data')
    process_directory(data_dir)


def run_gold_layer():
    from gold.build_gold import run
    run()

with DAG(
    dag_id='nyc_rodent_pipeline',
    default_args=default_args,
    description='NYC Rodent Inspection Pipeline - Silver and Gold layers',
    schedule='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    
    silver_task = PythonOperator(
        task_id='run_silver_layer',
        python_callable=run_silver_layer,
    )

    gold_task = PythonOperator(
        task_id='run_gold_layer',
        python_callable=run_gold_layer,
    )

    silver_task >> gold_task