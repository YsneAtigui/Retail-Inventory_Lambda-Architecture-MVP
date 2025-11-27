import os
import json
from datetime import datetime, timedelta
from kafka import KafkaProducer
from faker import Faker
import random
import time

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

PRICE_RANGES = {
    'Electronics': (100, 1500),
    'Clothing': (20, 200),
    'Home': (30, 300),
    'Books': (10, 50),
    'Sports': (15, 250)
}

def get_seasonal_multiplier(month):
    """Apply seasonal patterns to sales"""
    # Higher sales in Nov-Dec (holidays), lower in Jan-Feb
    seasonal_factors = {
        1: 0.7,   # January (post-holiday slump)
        2: 0.75,  # February
        3: 0.9,   # March
        4: 0.95,  # April
        5: 1.0,   # May
        6: 1.05,  # June
        7: 1.1,   # July
        8: 1.05,  # August
        9: 1.0,   # September
        10: 1.1,  # October
        11: 1.5,  # November (Black Friday)
        12: 1.8   # December (holidays)
    }
    return seasonal_factors.get(month, 1.0)

def get_hourly_multiplier(hour):
    """Apply hourly patterns (more sales during business hours)"""
    if 9 <= hour <= 12:
        return 1.5  # Morning rush
    elif 12 <= hour <= 14:
        return 1.3  # Lunch time
    elif 17 <= hour <= 20:
        return 1.7  # Evening peak
    elif 20 <= hour <= 22:
        return 1.2  # Evening
    elif 0 <= hour <= 6:
        return 0.2  # Late night
    else:
        return 1.0  # Normal hours

def get_weekend_multiplier(day_of_week):
    """Higher sales on weekends"""
    if day_of_week in [5, 6]:  # Saturday, Sunday
        return 1.4
    return 1.0

def generate_historical_event(timestamp):
    """Generate a synthetic retail inventory event for a specific timestamp."""
    category = random.choice(list(CATEGORIES.keys()))
    product = random.choice(CATEGORIES[category])
    
    # Apply probability multipliers
    hour = timestamp.hour
    month = timestamp.month
    day_of_week = timestamp.weekday()
    
    # Calculate if event should be generated based on patterns
    base_probability = 0.3  # 30% base chance
    probability = base_probability * \
                  get_hourly_multiplier(hour) * \
                  get_seasonal_multiplier(month) * \
                  get_weekend_multiplier(day_of_week)
    
    # Skip event if probability not met
    if random.random() > probability:
        return None
    
    # Determine transaction type (90% SALE, 7% RETURN, 3% RESTOCK)
    rand = random.random()
    if rand < 0.90:
        transaction_type = 'SALE'
        quantity = random.randint(1, 10)
    elif rand < 0.97:
        transaction_type = 'RETURN'
        quantity = random.randint(1, 5)
    else:
        transaction_type = 'RESTOCK'
        quantity = random.randint(10, 100)
    
    price_range = PRICE_RANGES[category]
    
    # Add some price variation over time (inflation, discounts)
    months_old = (datetime.now() - timestamp).days / 30
    price_adjustment = 1.0 - (months_old * 0.005)  # Slight price increase over time
    
    # Seasonal discounts
    if month in [11, 12]:  # Holiday discounts
        price_adjustment *= 0.85
    elif month in [1, 7]:  # Clearance sales
        price_adjustment *= 0.90
    
    unit_price = round(random.uniform(price_range[0], price_range[1]) * price_adjustment, 2)
    
    event = {
        "event_time": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
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
                retries=3,
                batch_size=16384,
                linger_ms=10
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

def backfill_historical_data(months_back=12, events_per_hour=3):
    """
    Backfill historical data.
    
    Args:
        months_back: How many months of data to generate (default: 12 months)
        events_per_hour: Average events per hour (default: 3)
    """
    print(f"Starting Historical Data Backfill...")
    print(f"Generating {months_back} months of data")
    print(f"Target: ~{events_per_hour} events per hour")
    
    producer = create_kafka_producer()
    
    # Calculate start and end dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months_back * 30)
    
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    event_count = 0
    batch_count = 0
    current_date = start_date
    
    try:
        while current_date < end_date:
            # Generate events for this hour
            for _ in range(events_per_hour):
                event = generate_historical_event(current_date)
                
                if event:
                    producer.send(KAFKA_TOPIC, value=event)
                    event_count += 1
                    
                    # Progress update every 10000 events
                    if event_count % 10000 == 0:
                        print(f"Generated {event_count:,} events. Current date: {current_date.strftime('%Y-%m-%d %H:%M')}")
            
            # Move to next hour
            current_date += timedelta(hours=1)
            
            # Small delay every 1000 hours to avoid overwhelming Kafka
            if (current_date.hour == 0):
                batch_count += 1
                if batch_count % 10 == 0:  # Every 10 days
                    producer.flush()
                    time.sleep(0.1)
        
        # Final flush
        producer.flush()
        
        print(f"\n{'='*60}")
        print(f"Backfill Complete!")
        print(f"Total events generated: {event_count:,}")
        print(f"Time period: {months_back} months")
        print(f"Average events per day: {event_count / (months_back * 30):,.0f}")
        print(f"{'='*60}")
        
    except KeyboardInterrupt:
        print("\nBackfill interrupted by user")
        print(f"Generated {event_count:,} events before stopping")
    except Exception as e:
        print(f"Error during backfill: {e}")
    finally:
        producer.flush()
        producer.close()
        print(f"Producer stopped. Total events: {event_count:,}")

if __name__ == "__main__":
    # Configuration
    MONTHS_TO_BACKFILL = 12  # Generate 1 year of data
    EVENTS_PER_HOUR = 5      # Average 5 events per hour
    
    print("\n" + "="*60)
    print("RETAIL INVENTORY - HISTORICAL DATA BACKFILL")
    print("="*60)
    print(f"Configuration:")
    print(f"  Months back: {MONTHS_TO_BACKFILL}")
    print(f"  Events/hour: {EVENTS_PER_HOUR}")
    print(f"  Estimated total: ~{MONTHS_TO_BACKFILL * 30 * 24 * EVENTS_PER_HOUR:,} events")
    print(f"  Estimated time: ~5-10 minutes")
    print("="*60 + "\n")
    
    response = input("Start backfill? (y/n): ")
    if response.lower() == 'y':
        backfill_historical_data(
            months_back=MONTHS_TO_BACKFILL,
            events_per_hour=EVENTS_PER_HOUR
        )
    else:
        print("Backfill cancelled")
