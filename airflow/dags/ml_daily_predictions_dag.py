from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# Default arguments
default_args = {
    'owner': 'data-science',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'ml_daily_predictions',
    default_args=default_args,
    description='Generate daily demand forecasts using latest model',
    schedule_interval='0 1 * * *',  # Every day at 1 AM
    catchup=False,
    tags=['ml', 'prediction', 'forecasting']
)

# Task 1: Generate predictions for next 7 days
generate_predictions = BashOperator(
    task_id='generate_7day_forecast',
    bash_command='''
    docker exec spark-master /opt/spark/bin/spark-submit \
        --master spark://spark-master:7077 \
        --deploy-mode client \
        --driver-memory 2g \
        --executor-memory 2g \
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1,org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
        --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
        --conf spark.hadoop.fs.s3a.access.key=minioadmin \
        --conf spark.hadoop.fs.s3a.secret.key=minioadmin \
        --conf spark.hadoop.fs.s3a.path.style.access=true \
        --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
        --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false \
        /opt/airflow/spark/ml_prediction_batch.py
    ''',
    dag=dag
)

# Task 2: Import predictions to ClickHouse
import_to_clickhouse = BashOperator(
    task_id='import_predictions_to_clickhouse',
    bash_command='''
    docker exec clickhouse clickhouse-client --user=default --password=password123 --query="
    INSERT INTO retail.demand_predictions (
        prediction_id,
        prediction_time,
        model_version,
        product_id,
        store_id,
        forecast_date,
        forecast_hour,
        predicted_demand,
        confidence_lower,
        confidence_upper,
        day_of_week,
        month,
        is_weekend,
        seasonal_factor
    )
    SELECT 
        toString(prediction_id) as prediction_id,
        prediction_time,
        model_version,
        product_id,
        store_id,
        forecast_date,
        forecast_hour,
        predicted_demand,
        confidence_lower,
        confidence_upper,
        day_of_week,
        month,
        is_weekend,
        seasonal_factor
    FROM s3(
        'http://minio:9000/retail-lake/predictions/*/part-*.parquet',
        'minioadmin',
        'minioadmin',
        'Parquet'
    )
    WHERE prediction_time >= now() - INTERVAL 2 HOUR
    "
    ''',
    dag=dag
)

# Set task dependencies
generate_predictions >> import_to_clickhouse
