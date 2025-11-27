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
        
        # Data enrichment: Add derived metrics and time dimensions
        print("Enriching data with derived metrics...")
        from pyspark.sql.functions import dayofweek, hour, when
        
        enriched_df = processed_df \
            .withColumn("revenue", col("quantity") * col("unit_price")) \
            .withColumn("year", col("event_time").substr(1, 4).cast("int")) \
            .withColumn("month", col("event_time").substr(6, 2).cast("int")) \
            .withColumn("day", col("event_time").substr(9, 2).cast("int")) \
            .withColumn("hour_of_day", hour(col("event_time"))) \
            .withColumn("day_of_week", dayofweek(col("event_time"))) \
            .withColumn("is_weekend", 
                when((dayofweek(col("event_time")) == 1) | 
                     (dayofweek(col("event_time")) == 7), True).otherwise(False))
        
        # Data validation: Filter out invalid records
        print("Applying data quality checks...")
        validated_df = enriched_df.filter(
            (col("quantity") > 0) & 
            (col("unit_price") > 0) &
            (col("revenue") > 0)
        )
        
        # Write to MinIO as Parquet with partitioning by date
        print("Writing to MinIO (s3a://retail-lake/) with date partitioning...")
        query = validated_df.writeStream \
            .format("parquet") \
            .partitionBy("year", "month", "day") \
            .option("path", "s3a://retail-lake/") \
            .option("checkpointLocation", "/tmp/checkpoint/retail-lake") \
            .outputMode("append") \
            .trigger(processingTime="30 seconds") \
            .start()
        
        print("Batch processor is running...")
        print("Writing partitioned data to s3a://retail-lake/ every 30 seconds")
        print("Partitioning by: year, month, day")
        print("Enrichments: revenue, time dimensions, is_weekend flag")
        
        # Wait for termination
        query.awaitTermination()
        
    except Exception as e:
        print(f"Error in batch processor: {e}")
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
