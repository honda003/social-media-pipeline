from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# DAG definition
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": True,
    "email": ["mohannad.husny@gmail.com"],  # optional
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="social_media_pipeline",
    default_args=default_args,
    description="Orchestrate Reddit, YouTube, and Spark ETL pipeline",
    schedule_interval="@daily",
    start_date=datetime(2025, 11, 9),
    catchup=False,
    tags=["social-media", "ETL"],
) as dag:

    # --- Reddit extraction ---
    reddit_extract = BashOperator(
        task_id="reddit_extract",
        bash_command="python3 /opt/airflow/python/reddit.py",
    )

    # --- YouTube extraction ---
    youtube_extract = BashOperator(
        task_id="youtube_extract",
        bash_command="python3 /opt/airflow/python/youtube.py",
    )

    # --- Spark transformation ---
    spark_processing = BashOperator(
        task_id="spark_processing",
        bash_command=(
            "docker exec spark-master "
            "spark-submit --master spark://spark-master:7077 "
            "/opt/spark/python/social_media_processing.py"
        ),
    )

    # Dependencies
    [reddit_extract, youtube_extract] >> spark_processing
