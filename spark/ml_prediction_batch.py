from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.ml import PipelineModel
from datetime import datetime, timedelta
import uuid

def create_spark_session():
    """Create Spark session with S3A and JDBC configuration."""
    spark = SparkSession.builder \
        .appName("DemandForecastPrediction") \
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1,"
                "org.apache.hadoop:hadoop-aws:3.3.4,"
                "com.amazonaws:aws-java-sdk-bundle:1.12.262") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

def load_model(spark):
    """Load the latest trained model from MinIO."""
    model_path = "s3a://retail-lake/models/demand_forecast_latest"
    
    print(f"Loading model from {model_path}...")
    model = PipelineModel.load(model_path)
    print("Model loaded successfully!")
    
    return model

def generate_prediction_features(spark, days_ahead=7):
    """Generate feature matrix for next N days."""
    print(f"Generating features for next {days_ahead} days...")
    
    # Get unique products and stores from historical data
    historical_df = spark.read.parquet("s3a://retail-lake/year=*/month=*/day=*/*parquet")
    
    products_stores = historical_df \
        .select("product_id", "store_id") \
        .distinct()
    
    # Generate date-hour combinations for next N days
    base_date = datetime.now()
    dates = []
    
    for day_offset in range(days_ahead):
        forecast_date = base_date + timedelta(days=day_offset)
        for hour in range(24):
            forecast_datetime = forecast_date.replace(
                hour=hour, minute=0, second=0, microsecond=0
            )
            
            dates.append({
                "forecast_date": forecast_datetime.date(),
                "forecast_hour": hour,
                "day_of_week": forecast_datetime.isoweekday(),
                "month": forecast_datetime.month,
                "day_of_month": forecast_datetime.day,
                "is_weekend": 1 if forecast_datetime.isoweekday() in [6, 7] else 0,
                "is_holiday_season": 1 if forecast_datetime.month in [11, 12] else 0,
                "is_summer": 1 if forecast_datetime.month in [6, 7, 8] else 0
            })
    
    dates_df = spark.createDataFrame(dates)
    
    # Cross join products/stores with dates
    features_df = products_stores.crossJoin(dates_df)
    
    # Add historical averages as features
    print("Adding historical features...")
    historical_avg = historical_df \
        .filter(col("transaction_type") == "SALE") \
        .groupBy("product_id", "store_id", dayofweek("event_time").alias("day_of_week_hist")) \
        .agg(
            avg("quantity").alias("avg_demand"),
            count("*").alias("transaction_count")
        )
    
    # Join with historical averages and drop duplicate columns
    features_df = features_df \
        .join(
            historical_avg,
            (features_df.product_id == historical_avg.product_id) &
            (features_df.store_id == historical_avg.store_id) &
            (features_df.day_of_week == historical_avg.day_of_week_hist),
            "left"
        ) \
        .drop(historical_avg.product_id) \
        .drop(historical_avg.store_id) \
        .drop(historical_avg.day_of_week_hist) \
        .fillna({"avg_demand": 1.0, "transaction_count": 1})
    
    # Rename for compatibility with model
    features_df = features_df \
        .withColumnRenamed("forecast_hour", "hour_of_day") \
        .select(
            features_df.product_id,
            features_df.store_id,
            "forecast_date",
            "hour_of_day",
            features_df.day_of_week,
            "month",
            "is_weekend",
            "is_holiday_season",
            "is_summer",
            "avg_demand",
            "transaction_count"
        )
    
    print(f"Generated {features_df.count():,} prediction scenarios")
    
    return features_df

def make_predictions(model, features_df, model_version):
    """Apply model to generate predictions."""
    print("Generating predictions...")
    
    predictions = model.transform(features_df)
    
    # Add metadata and confidence intervals (simple ±20% for now)
    predictions_final = predictions \
        .withColumn("prediction_id", expr("uuid()")) \
        .withColumn("predicted_demand", round(col("prediction"), 2)) \
        .withColumn("confidence_lower", round(col("prediction") * 0.8, 2)) \
        .withColumn("confidence_upper", round(col("prediction") * 1.2, 2)) \
        .withColumn("model_version", lit(model_version)) \
        .withColumn("prediction_time", current_timestamp()) \
        .withColumn("seasonal_factor", 
                    when(col("is_holiday_season") == 1, 1.5)
                    .when(col("is_summer") == 1, 1.1)
                    .otherwise(1.0))
    
    # Select final columns
    final_predictions = predictions_final.select(
        col("prediction_id").cast("string"),
        "prediction_time",
        "model_version",
        "product_id",
        "store_id",
        "forecast_date",
        col("hour_of_day").alias("forecast_hour"),
        "predicted_demand",
        "confidence_lower",
        "confidence_upper",
        "day_of_week",
        "month",
        col("is_weekend").cast("int"),
        "seasonal_factor"
    ).filter(col("predicted_demand") > 0)  # Remove zero predictions
    
    print(f"Generated {final_predictions.count():,} valid predictions")
    
    # Show sample predictions
    print("\nSample Predictions:")
    final_predictions.orderBy(col("predicted_demand").desc()).show(10, truncate=False)
    
    return final_predictions

def save_predictions_to_clickhouse(predictions_df):
    """Save predictions to ClickHouse."""
    print("Saving predictions to ClickHouse...")
    
    # Save as Parquet first (for backup)
    output_path = f"s3a://retail-lake/predictions/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    predictions_df.write.mode("overwrite").parquet(output_path)
    print(f"Predictions saved to {output_path}")
    
    # For ClickHouse insertion, we'll write as CSV for manual import
    # In production, use JDBC driver or clickhouse-kafka connector
    csv_path = f"s3a://retail-lake/predictions_csv/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    predictions_df.write \
        .mode("overwrite") \
        .option("header", "true") \
        .csv(csv_path)
    
    print(f"CSV for ClickHouse import saved to {csv_path}")
    print("\nTo import into ClickHouse, run:")
    print(f"  clickhouse-client --query=\"INSERT INTO retail.demand_predictions FORMAT CSVWithNames\" < predictions.csv")
    
    return output_path

def main():
    """Main prediction function."""
    print("\n" + "="*60)
    print("DEMAND FORECASTING - PREDICTION GENERATION")
    print("="*60 + "\n")
    
    spark = create_spark_session()
    model_version = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Load trained model
        model = load_model(spark)
        
        # Generate features for next 7 days
        features_df = generate_prediction_features(spark, days_ahead=7)
        
        # Make predictions
        predictions = make_predictions(model, features_df, model_version)
        
        # Save predictions
        output_path = save_predictions_to_clickhouse(predictions)
        
        print(f"\n{'='*60}")
        print(f"Prediction Complete!")
        print(f"Generated predictions for next 7 days")
        print(f"Output: {output_path}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"Error during prediction: {e}")
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
