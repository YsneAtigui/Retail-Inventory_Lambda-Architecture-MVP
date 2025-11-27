from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, to_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType

# Define the schema for retail events
schema = StructType([
    StructField("event_time", StringType(), True),
    StructField("store_id", IntegerType(), True),
    StructField("product_id", StringType(), True),
    StructField("category", StringType(), True),
    StructField("transaction_type", StringType(), True),
    StructField("quantity", IntegerType(), True),
    StructField("unit_price", DoubleType(), True)
])

def create_spark_session():
    """Create Spark session with S3A configuration for MinIO."""
    spark = SparkSession.builder \
        .appName("RetailInventoryBatchProcessor") \
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
        .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoint") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

def main():
    """Main batch processing function."""
    print("Starting Retail Inventory Batch Processor...")
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Read from Kafka
        print("Reading from Kafka topic: retail_events")
        kafka_df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "kafka:29092") \
            .option("subscribe", "retail_events") \
            .option("startingOffsets", "earliest") \
            .load()
        
        # Parse JSON data
        print("Parsing JSON messages...")
        parsed_df = kafka_df.select(
            from_json(col("value").cast("string"), schema).alias("data")
        ).select("data.*")
        
        # Convert event_time to timestamp
        processed_df = parsed_df.withColumn(
            "event_time", 
            to_timestamp(col("event_time"), "yyyy-MM-dd HH:mm:ss")
        )
        
        # Write to MinIO as Parquet
        print("Writing to MinIO (s3a://retail-lake/)...")
        query = processed_df.writeStream \
            .format("parquet") \
            .option("path", "s3a://retail-lake/") \
            .option("checkpointLocation", "/tmp/checkpoint/retail-lake") \
            .outputMode("append") \
            .trigger(processingTime="30 seconds") \
            .start()
        
        print("Batch processor is running...")
        print("Writing data to s3a://retail-lake/ every 30 seconds")
        
        # Wait for termination
        query.awaitTermination()
        
    except Exception as e:
        print(f"Error in batch processor: {e}")
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
