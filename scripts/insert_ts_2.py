#!/usr/bin/env python3
import os
import random
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient, errors

# --- Configuration / Parameters ---
# Modify N_DAYS here to change how many days of data you want
N_DAYS = 4  # Generate 4 days of data to cover the 3.5 day display window

MONGODB_URI = os.environ.get("MONGODB_URI")          # e.g. "cluster0.mongodb.net"
MONGODB_USERNAME = os.environ.get("MONGODB_USERNAME") # e.g. "myUser"
MONGODB_PASSWORD = os.environ.get("MONGODB_PASSWORD") # e.g. "myPassword"

# Construct the connection string for MongoDB
connection_string = f"mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_URI}/?retryWrites=true&w=majority"
client = MongoClient(connection_string)

# Define database/collection - Changed from home_energy to smart_home
db = client["smart_home"]
collection_name = "sensor_readings"

# --- First drop the existing collection if it exists ---
try:
    db.drop_collection(collection_name)
    print(f"Dropped existing collection '{collection_name}' from smart_home database")
except Exception as e:
    print(f"Note: Could not drop collection: {e}")

# --- Create a time series collection (if it doesn't exist) ---
try:
    db.create_collection(
        collection_name,
        timeseries={
            "timeField": "Timestamp",  # field with datetime
            "metaField": "UserId",     # field containing metadata
            "granularity": "minutes"
        }
    )
    print(f"Created time series collection '{collection_name}' in smart_home database")
except errors.CollectionInvalid:
    print(f"Collection '{collection_name}' already exists (or creation not supported).")

collection = db[collection_name]

# --- Data Generation ---

USER_ID = "user123"  # single user; change or loop as needed

# We define the end date as "today at 00:00 UTC"
# and generate data going backwards for N_DAYS.
end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
start_date = end_date - timedelta(days=N_DAYS)

# Example devices for each category
devices = [
    {
        "category": "HEATER",
        "brand": "AcmeHeating",
        "model": "HeatMax1000",
        "name": "LivingRoomHeater"
    },
    {
        "category": "OVEN",
        "brand": "BakersDelight",
        "model": "OvenProX2",
        "name": "KitchenOven"
    },
    {
        "category": "TV",
        "brand": "ScreenMaster",
        "model": "TV-LCD55",
        "name": "LivingRoomTV"
    },
    {
        "category": "MISC_APPLIANCE",
        "brand": "GenericBrand",
        "model": "MiscModel42",
        "name": "RandomAppliance"
    }
]

def get_current_usage(category, t):
    """
    Return the current usage (kW) for a given category, at minute-level granularity.
    't' is a datetime object with hour/minute/second.
    """
    hour = t.hour
    minute = t.minute
    
    # Add day-based variability (some days have higher/lower baseline usage)
    day_of_week = t.weekday()  # 0 = Monday, 6 = Sunday
    day_factor = 0.8 + (day_of_week * 0.05)  # Weekends have higher baseline
    
    # Add random fluctuations throughout the day
    time_noise = random.uniform(0.7, 1.3)
    
    # Add some occasional random spikes (simulating random appliance usage)
    random_spike = 0
    if random.random() < 0.03:  # 3% chance of a random spike
        random_spike = random.uniform(0.5, 2.0)

    if category == "HEATER":
        # Big spike from 7:00 AM to 9:00 AM (2 hours)
        # Add more variability to the spike timing and intensity
        if 7 <= hour < 9:
            base_usage = random.uniform(4.2, 5.2)
            # Higher in the middle of the spike period, lower at the beginning/end
            spike_curve = 1.0
            if hour == 7 and minute < 20:
                # Ramp up at the beginning
                spike_curve = 0.7 + (minute / 30)
            elif hour == 8 and minute > 40:
                # Ramp down toward the end
                spike_curve = 1.0 - ((minute - 40) / 60)
                
            # Add the random variability
            return round((base_usage * spike_curve * time_noise * day_factor) + random_spike, 2)
        else:
            # Standby usage with more variability
            standby = random.uniform(0.08, 0.18) * day_factor * time_noise
            return round(standby + random_spike, 2)

    elif category == "OVEN":
        # Spike late afternoon / early evening (16:00 - 18:00)
        if 16 <= hour < 18:
            # Add variations in cooking time and intensity
            base_usage = random.uniform(1.8, 3.2) 
            
            # If it's a weekend, oven usage might be higher
            if day_of_week >= 5:  # Weekend
                base_usage *= 1.2
                
            # Cooking intensity varies during cooking cycle
            cooking_phase = (((hour - 16) * 60) + minute) / 120  # 0 to 1 over the 2 hour period
            phase_factor = 1.0
            
            # Preheating spike at the beginning
            if cooking_phase < 0.1:  
                phase_factor = 1.3
            # Cooling down at the end
            elif cooking_phase > 0.8:
                phase_factor = 0.7 + ((1 - cooking_phase) * 0.3)
                
            return round((base_usage * phase_factor * time_noise * day_factor) + random_spike, 2)
        else:
            # Low usage or off with more variability
            return round((random.uniform(0.03, 0.12) * day_factor * time_noise) + random_spike, 2)

    elif category == "TV":
        # Typical evening usage (18:00 - 22:00)
        if 18 <= hour < 22:
            # TV usage varies by show/program and day of week
            base_usage = random.uniform(0.6, 1.7)
            
            # Higher usage during prime time (8PM-9PM)
            if hour == 20:
                base_usage *= 1.2
                
            # Weekend TV watching tends to be higher
            if day_of_week >= 5:  # Weekend
                base_usage *= 1.15
                
            # Some people turn off TV during commercials
            if random.random() < 0.1:  # 10% chance of commercial breaks
                base_usage *= 0.7
                
            return round((base_usage * time_noise * day_factor) + random_spike, 2)
        else:
            # Standby power with occasional spikes (like automatic updates)
            standby = random.uniform(0.04, 0.12) * day_factor * time_noise
            return round(standby + random_spike, 2)

    elif category == "MISC_APPLIANCE":
        # Random small usage with occasional spikes (blenders, chargers, etc)
        base_usage = random.uniform(0.03, 0.25)
        
        # Morning and evening tend to have more misc appliance usage
        if (7 <= hour < 9) or (17 <= hour < 21):
            base_usage *= 1.3
            
        # Some days have more small appliance usage
        if day_of_week in [0, 3, 6]:  # Monday, Thursday, Sunday
            base_usage *= 1.2
            
        return round((base_usage * time_noise * day_factor) + random_spike, 2)

    return 0.0

# For storing all generated readings
all_readings = []

# Generate data for each day in [start_date, end_date)
current_day = start_date
while current_day < end_date:
    # Weather effect for the current day (affects heater usage)
    is_cold_day = random.random() < 0.4  # 40% chance of a cold day
    cold_factor = 1.3 if is_cold_day else 1.0
    
    # Some days devices might be off completely (e.g., nobody home)
    away_from_home = random.random() < 0.1  # 10% chance nobody's home
    
    # Generate data for each minute of the current day
    for minute_offset in range(24 * 60):  # for each minute of the day
        current_time = current_day + timedelta(minutes=minute_offset)

        # If we've reached or passed the end date, break
        if current_time >= end_date:
            break
        
        # Maybe skip some readings to simulate connectivity issues (creates gaps in the data)
        if random.random() < 0.005:  # 0.5% chance of missing a reading
            continue
            
        # Generate readings for each device
        for dev in devices:
            # If nobody's home, only report standby power for most devices 
            # (except MISC_APPLIANCE which might include automated systems)
            if away_from_home and dev["category"] != "MISC_APPLIANCE":
                usage = random.uniform(0.02, 0.1)  # minimal standby power
            else:
                # Get baseline usage for this device at this time
                usage = get_current_usage(dev["category"], current_time)
                
                # Apply cold weather factor to heater
                if dev["category"] == "HEATER" and is_cold_day:
                    usage *= cold_factor
            
            # Create the reading document
            reading = {
                # The timeField for the time series collection must be a datetime
                "Timestamp": current_time,
                
                # The metaField for the time series collection
                "UserId": USER_ID,

                # Device info
                "Device": {
                    "Brand": dev["brand"],
                    "Model": dev["model"],
                    "Name": dev["name"]
                },
                "Category": dev["category"],
                "current_usage": usage
            }
            all_readings.append(reading)

    # Move to the next day
    current_day += timedelta(days=1)

# Insert the generated documents in one bulk operation
try:
    if all_readings:
        result = collection.insert_many(all_readings)
        print(f"Inserted {len(result.inserted_ids)} documents into '{collection_name}'.")
    else:
        print("No readings generated (start_date >= end_date).")
except Exception as e:
    print(f"Error inserting documents: {e}")

client.close()