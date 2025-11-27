from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.ml.feature import VectorAssembler, StringIndexer
from pyspark.ml.regression import RandomForestRegressor, GBTRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml import Pipeline
from datetime import datetime
import json

def create_spark_session():
    """Create Spark session with S3A configuration for MinIO."""
    spark = SparkSession.builder \
        .appName("DemandForecastTraining") \
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

def load_and_prepare_data(spark):
    """Load historical data and prepare features."""
    print("Loading historical data from MinIO...")
    
    # Load partitioned Parquet data
    df = spark.read.parquet("s3a://retail-lake/year=*/month=*/day=*/*parquet")
    
    print(f"Loaded {df.count():,} records")
    
    # Feature engineering
    print("Engineering features...")
    features_df = df \
        .filter(col("transaction_type") == "SALE") \
        .withColumn("day_of_week", dayofweek(col("event_time"))) \
        .withColumn("hour_of_day", hour(col("event_time"))) \
        .withColumn("month", month(col("event_time"))) \
        .withColumn("day_of_month", dayofmonth(col("event_time"))) \
        .withColumn("is_weekend", when((dayofweek(col("event_time")).isin([1, 7])), 1).otherwise(0)) \
        .withColumn("is_holiday_season", when(col("month").isin([11, 12]), 1).otherwise(0)) \
        .withColumn("is_summer", when(col("month").isin([6, 7, 8]), 1).otherwise(0))
    
    # Aggregate to product-store-hour level
    print("Aggregating data for training...")
    training_data = features_df.groupBy(
        "product_id",
        "store_id", 
        "day_of_week",
        "hour_of_day",
        "month",
        "is_weekend",
        "is_holiday_season",
        "is_summer"
    ).agg(
        sum("quantity").alias("total_demand"),
        avg("quantity").alias("avg_demand"),
        count("*").alias("transaction_count")
    ).filter(col("total_demand") > 0)
    
    print(f"Training dataset: {training_data.count():,} samples")
    
    return training_data

def train_model(training_data):
    """Train Random Forest model for demand prediction."""
    print("Preparing ML pipeline...")
    
    # Index categorical features
    product_indexer = StringIndexer(
        inputCol="product_id",
        outputCol="product_idx",
        handleInvalid="keep"
    )
    
    # Assemble features
    feature_cols = [
        "product_idx",
        "store_id",
        "day_of_week",
        "hour_of_day",
        "month",
        "is_weekend",
        "is_holiday_season",
        "is_summer",
        "avg_demand",
        "transaction_count"
    ]
    
    assembler = VectorAssembler(
        inputCols=feature_cols,
        outputCol="features",
        handleInvalid="skip"
    )
    
    # Random Forest Regressor
    rf = RandomForestRegressor(
        featuresCol="features",
        labelCol="total_demand",
        numTrees=100,
        maxDepth=10,
        maxBins=32,
        seed=42
    )
    
    # Create pipeline
    pipeline = Pipeline(stages=[product_indexer, assembler, rf])
    
    # Split data (80% train, 20% test)
    print("Splitting data...")
    train_df, test_df = training_data.randomSplit([0.8, 0.2], seed=42)
    
    print(f"Training samples: {train_df.count():,}")
    print(f"Test samples: {test_df.count():,}")
    
    # Train model
    print("Training model... (this may take a few minutes)")
    model = pipeline.fit(train_df)
    
    # Evaluate model
    print("Evaluating model...")
    predictions = model.transform(test_df)
    
    evaluator_rmse = RegressionEvaluator(
        labelCol="total_demand",
        predictionCol="prediction",
        metricName="rmse"
    )
    
    evaluator_mae = RegressionEvaluator(
        labelCol="total_demand",
        predictionCol="prediction",
        metricName="mae"
    )
    
    evaluator_r2 = RegressionEvaluator(
        labelCol="total_demand",
        predictionCol="prediction",
        metricName="r2"
    )
    
    rmse = evaluator_rmse.evaluate(predictions)
    mae = evaluator_mae.evaluate(predictions)
    r2 = evaluator_r2.evaluate(predictions)
    
    print(f"\n{'='*60}")
    print(f"Model Performance Metrics:")
    print(f"  RMSE: {rmse:.2f}")
    print(f"  MAE: {mae:.2f}")
    print(f"  R² Score: {r2:.4f}")
    print(f"{'='*60}\n")
    
    # Show sample predictions
    print("Sample Predictions:")
    predictions.select(
        "product_id",
        "store_id",
        "day_of_week",
        "hour_of_day",
        "total_demand",
        "prediction"
    ).show(10, truncate=False)
    
    metrics = {
        "rmse": float(rmse),
        "mae": float(mae),
        "r2_score": float(r2),
        "training_samples": train_df.count(),
        "test_samples": test_df.count()
    }
    
    return model, metrics, predictions

def save_model(model, metrics, spark):
    """Save model to MinIO and metrics to ClickHouse."""
    model_version = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = f"s3a://retail-lake/models/demand_forecast_{model_version}"
    
    print(f"Saving model to {model_path}...")
    model.write().overwrite().save(model_path)
    
    print("Saving latest model reference...")
    model.write().overwrite().save("s3a://retail-lake/models/demand_forecast_latest")
    
    # Save metrics to ClickHouse
    print("Saving metrics to ClickHouse...")
    
    metrics_df = spark.createDataFrame([{
        "model_version": model_version,
        "model_type": "demand_forecast",
        "training_date": datetime.now(),
        "training_samples": int(metrics["training_samples"]),
        "rmse": float(metrics["rmse"]),
        "mae": float(metrics["mae"]),
        "r2_score": float(metrics["r2_score"]),
        "parameters": json.dumps({
            "algorithm": "RandomForest",
            "num_trees": 100,
            "max_depth": 10
        }),
        "is_active": 1
    }])
    
    # Write to ClickHouse (you may need clickhouse-jdbc driver)
    # For now, print and manually insert
    print("\nModel Metrics (insert into ClickHouse):")
    print(f"Model Version: {model_version}")
    print(f"RMSE: {metrics['rmse']:.2f}")
    print(f"MAE: {metrics['mae']:.2f}")
    print(f"R² Score: {metrics['r2_score']:.4f}")
    
    return model_version

def main():
    """Main training function."""
    print("\n" + "="*60)
    print("DEMAND FORECASTING MODEL TRAINING")
    print("="*60 + "\n")
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Load and prepare data
        training_data = load_and_prepare_data(spark)
        
        # Train model
        model, metrics, predictions = train_model(training_data)
        
        # Save model
        model_version = save_model(model, metrics, spark)
        
        print(f"\n{'='*60}")
        print(f"Training Complete!")
        print(f"Model Version: {model_version}")
        print(f"Model saved to: s3a://retail-lake/models/")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"Error during training: {e}")
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
