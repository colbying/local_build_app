#!/usr/bin/env python3
import random
import datetime
import time
import threading
import sys
import math
from pymongo import MongoClient

#############################################
# CONFIGURATION - MODIFY THESE VALUES
#############################################

# MongoDB connection
MONGODB_URL = "mongodb+srv://natreya:Levante123@democluster.ytvgm.mongodb.net/?retryWrites=true&w=majority&appName=DemoCluster"
DATABASE_NAME = "smart_home_data"
COLLECTION_NAME = "power_readings"

# Date range
START_DATE = datetime.datetime(2024, 1, 1)  # Year, Month, Day
END_DATE = datetime.datetime(2024, 12, 31, 23, 59, 59)  # Year, Month, Day, Hour, Minute, Second

# Data generation frequency
INTERVAL_SECONDS = 20  # Seconds between readings

# Batch size for MongoDB inserts
BATCH_SIZE = 1000  # Number of documents per batch insert
PROGRESS_REPORT_FREQUENCY = 300000  # Report progress every 300k documents

#############################################
# END OF CONFIGURATION
#############################################

# Special days (high consumption events)
SPECIAL_DAYS = {
    # Christmas Eve and Day
    "2024-12-24": "Christmas Eve",
    "2024-12-25": "Christmas Day",
    # Thanksgiving (4th Thursday in November 2024)
    "2024-11-28": "Thanksgiving",
    # Independence Day
    "2024-07-04": "Independence Day",
    # New Year's Eve/Day
    "2024-12-31": "New Year's Eve",
    "2024-01-01": "New Year's Day",
    # Super Bowl Sunday 2024 (February 11)
    "2024-02-11": "Super Bowl Sunday"
}

# Define devices with detailed information
DEVICES = [
    {
        "Device": "HVAC001",
        "Brand": "Carrier",
        "Model": "Infinity",
        "Name": "Living Room AC",
        "Category": "HVAC",
        "base_power": 2.5,  # Base power consumption in kW
        "always_on": False
    },
    {
        "Device": "FRIDGE001",
        "Brand": "Samsung",
        "Model": "Smart Family Hub",
        "Name": "Kitchen Refrigerator",
        "Category": "Appliance",
        "base_power": 0.15,
        "always_on": True
    },
    {
        "Device": "TV001",
        "Brand": "LG",
        "Model": "OLED65C3",
        "Name": "Living Room TV",
        "Category": "Entertainment",
        "base_power": 0.15,
        "always_on": False
    },
    {
        "Device": "WASHER001",
        "Brand": "Whirlpool",
        "Model": "FrontLoad Pro",
        "Name": "Laundry Washer", 
        "Category": "Appliance",
        "base_power": 0.9,
        "always_on": False
    },
    {
        "Device": "DRYER001",
        "Brand": "Whirlpool",
        "Model": "HeatSense",
        "Name": "Laundry Dryer",
        "Category": "Appliance",
        "base_power": 2.1,
        "always_on": False
    },
    {
        "Device": "OVEN001",
        "Brand": "GE",
        "Model": "Profile Smart",
        "Name": "Kitchen Oven",
        "Category": "Appliance",
        "base_power": 2.4,
        "always_on": False
    },
    {
        "Device": "DISHWASHER001",
        "Brand": "Bosch",
        "Model": "Silence Plus",
        "Name": "Kitchen Dishwasher",
        "Category": "Appliance",
        "base_power": 1.2,
        "always_on": False
    },
    {
        "Device": "LIGHTS001",
        "Brand": "Philips",
        "Model": "Hue System",
        "Name": "Home Lighting",
        "Category": "Lighting",
        "base_power": 0.3,
        "always_on": False
    },
    {
        "Device": "WATER_HEATER001",
        "Brand": "Rheem",
        "Model": "Performance Plus",
        "Name": "Water Heater",
        "Category": "Appliance",
        "base_power": 4.5,
        "always_on": True
    },
    {
        "Device": "COMPUTER001",
        "Brand": "Dell",
        "Model": "XPS Desktop",
        "Name": "Home Office PC",
        "Category": "Entertainment",
        "base_power": 0.2,
        "always_on": False
    }
]

# Shared variables
lock = threading.Lock()
total_inserted = 0
process_start = time.time()
total_data_points = 0  # Will be calculated in main()

def get_interval():
    """Return the configured interval in seconds"""
    return INTERVAL_SECONDS

def calculate_amps(power, voltage):
    """Calculate amperage from power (kW) and voltage"""
    # P = VI, so I = P/V
    # Convert kW to W for calculation
    watts = power * 1000
    amps = watts / voltage
    return round(amps, 2)

def should_device_be_on(device, timestamp, is_special_day):
    """Determine if a device should be on at a given time"""
    if device["always_on"]:
        return True
        
    hour = timestamp.hour
    day_of_week = timestamp.weekday()  # 0-6 (Monday to Sunday)
    is_weekend = day_of_week >= 5
    
    # Different operation patterns for each device category
    if device["Category"] == "HVAC":
        # HVAC operates more on evenings and mornings
        if is_weekend:
            if (7 <= hour <= 23):  # Longer operation on weekends
                return random.random() < 0.75
        else:  # Weekday
            if (6 <= hour <= 9) or (17 <= hour <= 22):  # Morning and evening
                return random.random() < 0.85
            elif (9 <= hour <= 17):  # Daytime
                return random.random() < 0.3
            elif (22 <= hour <= 23) or (0 <= hour < 6):  # Night
                return random.random() < 0.15
                
    elif device["Category"] == "Entertainment":
        # Entertainment systems more likely in evenings and weekends
        if is_special_day:
            return random.random() < 0.8  # High probability on special days
        elif is_weekend:
            if (10 <= hour <= 23):  # Longer entertainment periods on weekends
                return random.random() < 0.6
            else:
                return random.random() < 0.05
        else:  # Weekday
            if (18 <= hour <= 23):  # Evening entertainment on weekdays
                return random.random() < 0.7
            elif (8 <= hour <= 18):  # Some daytime usage
                return random.random() < 0.15
            else:
                return random.random() < 0.02
                
    elif device["Category"] == "Lighting":
        # Lighting based on daylight hours
        if (6 <= hour <= 8) or (17 <= hour <= 23):  # Morning/evening
            return random.random() < 0.9
        elif (9 <= hour <= 16):  # Daytime
            return random.random() < 0.2
        else:  # Night
            return random.random() < 0.1
            
    elif device["Category"] == "Appliance":
        # Different patterns for different appliances
        if device["Device"].startswith("WASHER") or device["Device"].startswith("DRYER"):
            # More laundry on weekends and evenings
            if is_weekend:
                return random.random() < 0.3  # Higher chance on weekends
            elif (18 <= hour <= 21):  # Evening laundry
                return random.random() < 0.25
            else:
                return random.random() < 0.05
                
        elif device["Device"].startswith("OVEN") or device["Device"].startswith("DISHWASHER"):
            # Meal-time patterns
            if is_special_day:
                return random.random() < 0.6  # Much higher on holidays
            elif (7 <= hour <= 9) or (11 <= hour <= 13) or (17 <= hour <= 20):  # Meal times
                return random.random() < 0.4
            else:
                return random.random() < 0.05
                
        elif device["Device"].startswith("WATER_HEATER"):
            # Water heater is mostly always on, but with usage spikes
            if (6 <= hour <= 9) or (18 <= hour <= 22):  # Morning/evening showers
                return True
            else:
                return device["always_on"]
                
    # Default case
    return random.random() < 0.1

def get_power_adjustment(device, timestamp, is_special_day):
    """Calculate power adjustment factors based on time and date"""
    month = timestamp.month
    hour = timestamp.hour
    is_weekend = timestamp.weekday() >= 5
    
    # Base seasonal adjustments
    # Summer: June-August, Winter: December-February
    if device["Category"] == "HVAC":
        if month in [6, 7, 8]:  # Summer - cooling
            seasonal_factor = 1.3
        elif month in [12, 1, 2]:  # Winter - heating
            seasonal_factor = 1.4
        else:  # Spring/Fall - moderate
            seasonal_factor = 0.6
    else:
        # Less seasonal impact on other devices
        if month in [6, 7, 8, 12, 1, 2]:  # More indoor activity in extreme seasons
            seasonal_factor = 1.1
        else:
            seasonal_factor = 1.0
    
    # Special day adjustments
    if is_special_day:
        if device["Device"].startswith("OVEN"):
            special_factor = 1.5  # Ovens get heavy use on holidays
        elif device["Category"] == "Entertainment":
            special_factor = 1.3  # More TV/entertainment on holidays
        else:
            special_factor = 1.2  # General increase
    else:
        special_factor = 1.0
        
    # Time of day adjustments
    if device["Category"] == "HVAC":
        if (13 <= hour <= 18):  # Afternoon peak
            time_factor = 1.2
        elif (7 <= hour <= 9) or (19 <= hour <= 22):  # Morning/evening
            time_factor = 1.1
        else:  # Night
            time_factor = 0.8
    elif device["Category"] == "Appliance" or device["Category"] == "Entertainment":
        if (17 <= hour <= 22):  # Evening peak
            time_factor = 1.15
        elif (7 <= hour <= 9):  # Morning peak
            time_factor = 1.1
        else:
            time_factor = 1.0
    else:
        time_factor = 1.0
        
    # Weekend adjustments
    if is_weekend:
        weekend_factor = 1.1  # Slightly more usage on weekends
    else:
        weekend_factor = 1.0
        
    # Combine all factors
    adjustment = seasonal_factor * special_factor * time_factor * weekend_factor
    
    # Add random noise (±10%)
    noise = 0.9 + (random.random() * 0.2)
    
    return adjustment * noise

def maintenance_probability(device, timestamp):
    """Calculate probability of maintenance being needed"""
    # Base probability by device type
    if device["Category"] == "HVAC":
        base_prob = 0.005  # 0.5% chance normally
    elif device["Category"] == "Appliance":
        if device["Device"].startswith("WATER_HEATER"):
            base_prob = 0.004
        else:
            base_prob = 0.002
    else:
        base_prob = 0.001
    
    # Increase probability during heavy use seasons
    month = timestamp.month
    if device["Category"] == "HVAC":
        if month in [1, 7, 8, 12]:  # Extreme temperature months
            base_prob *= 3  # Triple failure rate during extreme months
    
    # Age-based increase (devices "age" throughout the year)
    days_from_start = (timestamp - START_DATE).days
    age_factor = 1 + (days_from_start / 365)  # Increase by up to 100% by year end
    
    return base_prob * age_factor

def generate_reading(device, timestamp):
    """Generate a device reading with simplified metrics"""
    
    # Check if this is a special day
    date_str = timestamp.strftime("%Y-%m-%d")
    is_special_day = date_str in SPECIAL_DAYS
    
    # Determine if device is running
    if not should_device_be_on(device, timestamp, is_special_day):
        # Device is off or on standby
        power = random.uniform(0.001, 0.01) if not device["always_on"] else device["base_power"] * 0.1
    else:
        # Device is on - calculate power with adjustments
        adjustment = get_power_adjustment(device, timestamp, is_special_day)
        base = device["base_power"]
        power = base * adjustment
    
    # Add small random variation
    power = round(power * (0.95 + random.random() * 0.1), 3)
    
    # Calculate realistic voltage (slight variation around 120V)
    voltage = round(120 + random.uniform(-3, 3), 1)
    
    # Calculate amps based on power and voltage
    amps = calculate_amps(power, voltage)
    
    # Determine if maintenance is needed
    maintenance = random.random() < maintenance_probability(device, timestamp)
    
    # Create the reading
    reading = {
        "device_id": {
            "Device": device["Device"],
            "Brand": device["Brand"],
            "Model": device["Model"],
            "Name": device["Name"],
            "Category": device["Category"]
        },
        "timestamp": timestamp,
        "current_power": power,
        "voltage": voltage,
        "amps": amps,
        "maintenance_needed": maintenance
    }
    
    return reading

def worker_thread(device, start_date, end_date, batch_size, mongodb_url, database_name, collection_name):
    """Worker thread that generates and inserts data for a specific device"""
    
    global total_inserted, total_data_points
    
    # Connect to MongoDB
    client = MongoClient(mongodb_url)
    db = client[database_name]
    collection = db[collection_name]
    
    # Generate and insert data in batches
    device_inserted = 0
    batch = []
    
    current_time = start_date
    
    while current_time <= end_date:
        # Generate reading for this device
        reading = generate_reading(device, current_time)
        batch.append(reading)
        
        # Insert when batch is full
        if len(batch) >= batch_size:
            try:
                collection.insert_many(batch)
                
                with lock:
                    device_inserted += len(batch)
                    total_inserted += len(batch)
                    
                    # Print progress based on configured frequency
                    if total_inserted % PROGRESS_REPORT_FREQUENCY < batch_size:
                        elapsed = time.time() - process_start
                        docs_per_second = total_inserted / elapsed if elapsed > 0 else 0
                        time_diff = (end_date - start_date).total_seconds()
                        if time_diff > 0:
                            percent_time = ((current_time - start_date).total_seconds() / time_diff) * 100
                            est_remaining_secs = (elapsed / percent_time * 100) - elapsed if percent_time > 0 else 0
                        else:
                            percent_time = 100
                            est_remaining_secs = 0
                        
                        print("\n" + "=" * 70)
                        print(f"PROGRESS UPDATE [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
                        print("-" * 70)
                        print(f"Documents inserted: {total_inserted:,} of ~{total_data_points:,} estimated")
                        print(f"Current timestamp: {current_time.strftime('%Y-%m-%d %H:%M:%S')} ({percent_time:.1f}% complete)")
                        print("=" * 70)
            except Exception as e:
                print(f"Error inserting batch for {device['Device']}: {e}")
                # Try to continue with the next batch
            
            batch = []
        
        # Move to next timestamp with fixed interval
        current_time += datetime.timedelta(seconds=INTERVAL_SECONDS)
    
    # Insert any remaining documents
    if batch:
        try:
            collection.insert_many(batch)
            with lock:
                device_inserted += len(batch)
                total_inserted += len(batch)
        except Exception as e:
            print(f"Error inserting final batch for {device['Device']}: {e}")
    
    client.close()

def main():
    """Main function to set up and run the data generation process"""
    
    # Use predefined variables
    mongodb_url = MONGODB_URL
    database_name = DATABASE_NAME
    collection_name = COLLECTION_NAME
    start_date = START_DATE
    end_date = END_DATE
    
    # Connect to MongoDB
    print(f"\nConnecting to MongoDB at: {datetime.datetime.now().strftime('%H:%M:%S')}")
    print(f"MongoDB URL: {mongodb_url}")
    print(f"Database: {database_name}")
    print(f"Collection: {collection_name}")
    
    try:
        client = MongoClient(mongodb_url)
        # Quick test of the connection
        client.server_info()
        # Create database reference
        db = client[database_name]
        print("MongoDB connection successful!")
    except Exception as e:
        print(f"\nError connecting to MongoDB: {e}")
        sys.exit(1)
    
    # Create collection with time series configuration if it doesn't exist
    if collection_name not in db.list_collection_names():
        print(f"\nCreating time series collection: {collection_name}")
        try:
            db.create_collection(
                collection_name,
                timeseries={
                    "timeField": "timestamp",
                    "metaField": "device_id",
                    "granularity": "seconds"
                }
            )
            print(f"Created time series collection: {collection_name}")
        except Exception as e:
            print(f"Warning: Could not create time series collection: {e}")
            print("Will use regular collection instead.")
    
    # Calculate total documents and estimate data size
    global total_data_points
    days_in_range = (end_date - start_date).days + 1
    avg_readings_per_day = 86400 / INTERVAL_SECONDS  # Readings per day based on interval
    total_data_points = int(days_in_range * avg_readings_per_day * len(DEVICES))
    estimated_size_mb = total_data_points * 0.0005  # Rough estimate of 500 bytes per document
    
    print(f"\nData Generation Plan:")
    print(f"  Time range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} (full year)")
    print(f"  Resolution: Every {INTERVAL_SECONDS} seconds")
    print(f"  Devices: {len(DEVICES)}")
    print(f"  Estimated data points: {total_data_points:,}")
    print(f"  Estimated data size: {estimated_size_mb:.1f} MB ({estimated_size_mb/1024:.2f} GB)")
    print(f"  Threads: {len(DEVICES)}")
    print("-" * 60)
    
    # Start worker threads for each device
    threads = []
    for device in DEVICES:
        thread = threading.Thread(
            target=worker_thread,
            args=(device, start_date, end_date, BATCH_SIZE, mongodb_url, database_name, collection_name)
        )
        thread.daemon = True  # Set daemon to True so main program can exit if threads are still running
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Waiting for threads to complete...")
        print("Please wait to ensure data integrity.")
        # Let threads finish their current batch
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=10)
        print("Process terminated.")
        sys.exit(0)
    
    print(f"\nData generation complete! Total documents inserted: {total_inserted:,}")
    client.close()

# Call the main function if the script is run directly
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)
