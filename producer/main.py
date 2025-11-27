import os
import json
import time
from datetime import datetime
from kafka import KafkaProducer
from faker import Faker
import random

# Initialize Faker
fake = Faker()

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'retail_events')

# Product categories and items
CATEGORIES = {
    'Electronics': ['Laptop', 'Smartphone', 'Tablet', 'Headphones', 'Smartwatch'],
    'Clothing': ['T-Shirt', 'Jeans', 'Jacket', 'Sneakers', 'Dress'],
    'Home': ['Coffee Maker', 'Blender', 'Vacuum', 'Lamp', 'Bedding'],
    'Books': ['Novel', 'Textbook', 'Magazine', 'Comic', 'Biography'],
    'Sports': ['Basketball', 'Tennis Racket', 'Yoga Mat', 'Dumbbells', 'Running Shoes']
}

TRANSACTION_TYPES = ['SALE', 'RETURN', 'RESTOCK']

# Price ranges per category
PRICE_RANGES = {
    'Electronics': (100, 1500),
    'Clothing': (20, 200),
    'Home': (30, 300),
    'Books': (10, 50),
    'Sports': (15, 250)
}

def generate_event():
    """Generate a synthetic retail inventory event."""
    category = random.choice(list(CATEGORIES.keys()))
    product = random.choice(CATEGORIES[category])
    transaction_type = random.choice(TRANSACTION_TYPES)
    
    # Adjust quantity based on transaction type
    if transaction_type == 'SALE':
        quantity = random.randint(1, 10)
    elif transaction_type == 'RETURN':
        quantity = random.randint(1, 5)
    else:  # RESTOCK
        quantity = random.randint(10, 100)
    
    price_range = PRICE_RANGES[category]
    unit_price = round(random.uniform(price_range[0], price_range[1]), 2)
    
    event = {
        "event_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "store_id": random.randint(1, 10),
        "product_id": product,
        "category": category,
        "transaction_type": transaction_type,
        "quantity": quantity,
        "unit_price": unit_price
    }
    
    return event

def create_kafka_producer():
    """Create Kafka producer with retry logic."""
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            print(f"Successfully connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries}: Failed to connect to Kafka: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise

def main():
    """Main function to produce events continuously."""
    print("Starting Retail Inventory Event Producer...")
    print(f"Target Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Target Topic: {KAFKA_TOPIC}")
    
    # Create producer with retry logic
    producer = create_kafka_producer()
    
    event_count = 0
    
    try:
        while True:
            # Generate and send event
            event = generate_event()
            producer.send(KAFKA_TOPIC, value=event)
            event_count += 1
            
            # Log every 10 events
            if event_count % 10 == 0:
                print(f"Produced {event_count} events. Last event: {event}")
            
            # 2 events per second = 0.5 second delay
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nShutting down producer...")
    except Exception as e:
        print(f"Error in producer: {e}")
    finally:
        producer.flush()
        producer.close()
        print(f"Producer stopped. Total events: {event_count}")

if __name__ == "__main__":
    main()
