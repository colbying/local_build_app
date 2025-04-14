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
            "metaField": "metadata",   # single field that will contain both userId and deviceId
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
        "deviceId": "HEAT001",
        "category": "HEATER",
        "brand": "AcmeHeating",
        "model": "HeatMax1000",
        "name": "LivingRoomHeater"
    },
    {
        "deviceId": "OVEN001",
        "category": "OVEN",
        "brand": "BakersDelight",
        "model": "OvenProX2",
        "name": "KitchenOven"
    },
    {
        "deviceId": "TV001",
        "category": "TV",
        "brand": "ScreenMaster",
        "model": "TV-LCD55",
        "name": "LivingRoomTV"
    },
    {
        "deviceId": "MISC001",
        "category": "MISC_APPLIANCE",
        "brand": "GenericBrand",
        "model": "MiscModel42",
        "name": "RandomAppliance"
    }
]

def get_device_state(category, usage, time):
    """Determine the device state based on category, usage and time"""
    hour = time.hour
    
    if usage < 0.1:
        return "standby"
    elif usage < 0.5:
        return "idle"
    else:
        # For TVs during evening hours, they're more likely to be in active state
        if category == "TV" and 18 <= hour < 22:
            return random.choices(["active", "idle"], weights=[0.8, 0.2])[0]
        # For heaters in morning, they're more likely to be active
        elif category == "HEATER" and 7 <= hour < 9:
            return random.choices(["active", "idle"], weights=[0.9, 0.1])[0]
        # For ovens during dinner prep time
        elif category == "OVEN" and 16 <= hour < 18:
            return random.choices(["active", "idle"], weights=[0.85, 0.15])[0]
        # Default probabilities for other cases
        else:
            return random.choices(["active", "idle", "standby"], weights=[0.6, 0.3, 0.1])[0]

def get_temperature(category, device_state, time):
    """Generate a realistic temperature reading based on device category and state"""
    base_temp = 21.0  # baseline room temperature in Celsius
    
    if category == "HEATER":
        if device_state == "active":
            return round(random.uniform(40.0, 60.0), 1)  # Operating temperature
        elif device_state == "idle":
            return round(random.uniform(30.0, 39.9), 1)  # Warming up or cooling down
        else:  # standby
            return round(random.uniform(base_temp - 2, base_temp + 2), 1)  # Room temperature
    
    elif category == "OVEN":
        if device_state == "active":
            return round(random.uniform(150.0, 250.0), 1)  # High operating temperature
        elif device_state == "idle":
            return round(random.uniform(50.0, 100.0), 1)  # Residual heat
        else:  # standby
            return round(random.uniform(base_temp, base_temp + 5), 1)  # Slightly above room temp
    
    elif category == "TV":
        if device_state == "active":
            return round(random.uniform(35.0, 45.0), 1)  # Operating temperature
        elif device_state == "idle":
            return round(random.uniform(25.0, 34.9), 1)  # Display on but not fully used
        else:  # standby
            return round(random.uniform(base_temp - 1, base_temp + 3), 1)  # Near room temp
    
    else:  # MISC_APPLIANCE
        if device_state == "active":
            return round(random.uniform(30.0, 40.0), 1)
        elif device_state == "idle":
            return round(random.uniform(22.0, 29.9), 1)
        else:  # standby
            return round(random.uniform(base_temp - 1, base_temp + 1), 1)

def get_pressure(category, device_state, time):
    """Generate a realistic pressure reading (hPa) based on device type and state"""
    # Most home devices don't actually measure pressure, so this is somewhat fictional
    # Standard atmospheric pressure is around 1013.25 hPa
    base_pressure = 1013.25
    
    # Environmental daily variation (weather effects)
    day_factor = (time.day % 4) * 2.5  # 0, 2.5, 5, or 7.5 variation by day
    
    if category == "HEATER" or category == "OVEN":
        if device_state == "active":
            # Heating can slightly increase local pressure
            return round(base_pressure + day_factor + random.uniform(1.0, 5.0), 1)
        else:
            return round(base_pressure + day_factor + random.uniform(-1.0, 1.0), 1)
    else:
        # Other devices don't affect pressure significantly
        return round(base_pressure + day_factor + random.uniform(-2.0, 2.0), 1)

def get_battery_level(category, time, device_id):
    """Generate a battery level for devices that might have batteries
    (this is fictional for many home appliances but useful for the data model)"""
    
    # For this simulation, we'll pretend some devices have batteries that discharge over time
    # and get recharged occasionally
    
    # Use device_id as a seed for consistent battery patterns
    seed_value = sum(ord(c) for c in device_id) + time.day
    random.seed(seed_value)
    
    # Generate a base level that decreases throughout the day
    hour_factor = time.hour / 24.0  # 0.0 to 1.0 throughout the day
    
    if category == "TV" or category == "MISC_APPLIANCE":
        # These might have backup batteries or remote controls with batteries
        base_level = 100 - (hour_factor * 15)  # Lose ~15% throughout day
        
        # Occasionally gets recharged
        day_of_year = time.timetuple().tm_yday
        if day_of_year % 3 == 0 and time.hour >= 20:  # Every 3 days, evening recharge
            base_level = random.uniform(90, 100)
    else:
        # These typically don't have batteries, but we'll add a high fixed value for data completeness
        base_level = random.uniform(95, 100)
    
    # Add some random variation
    battery_level = base_level + random.uniform(-5, 5)
    
    # Ensure within bounds
    return max(0, min(100, round(battery_level, 1)))

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
                device_state = "standby"
            else:
                # Get baseline usage for this device at this time
                usage = get_current_usage(dev["category"], current_time)
                
                # Apply cold weather factor to heater
                if dev["category"] == "HEATER" and is_cold_day:
                    usage *= cold_factor
                
                # Determine device state based on usage and time
                device_state = get_device_state(dev["category"], usage, current_time)
            
            # Get additional metrics
            temperature = get_temperature(dev["category"], device_state, current_time)
            pressure = get_pressure(dev["category"], device_state, current_time)
            battery_level = get_battery_level(dev["category"], current_time, dev["deviceId"])
            
            # Create the reading document with flattened structure (no Device object)
            reading = {
                # The timeField for the time series collection must be a datetime
                "Timestamp": current_time,
                
                # Combine metadata fields into a single field
                "metadata": {
                    "UserId": USER_ID,
                    "deviceId": dev["deviceId"]
                },

                # Device properties at root level
                "brand": dev["brand"],
                "model": dev["model"],
                "device_name": dev["name"],
                "category": dev["category"],
                "current_usage": usage,
                
                # New metrics
                "temperature": temperature,
                "pressure": pressure,
                "device_state": device_state,
                "battery_level": battery_level
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