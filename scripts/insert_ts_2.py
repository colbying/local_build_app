#!/usr/bin/env python3
import os
import random
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient, errors

# --- Configuration / Parameters ---
# Modify N_DAYS here to change how many days of data you want
N_DAYS = 1  # By default generate data for the last 1 day (24 hours)

MONGODB_URI = os.environ.get("MONGODB_URI")          # e.g. "cluster0.mongodb.net"
MONGODB_USERNAME = os.environ.get("MONGODB_USERNAME") # e.g. "myUser"
MONGODB_PASSWORD = os.environ.get("MONGODB_PASSWORD") # e.g. "myPassword"

# Construct the connection string for MongoDB
connection_string = f"mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_URI}/?retryWrites=true&w=majority"
client = MongoClient(connection_string)

# Define database/collection - Changed from home_energy to smart_home
db = client["smart_home"]
collection_name = "sensor_readings"

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

    if category == "HEATER":
        # Big spike around 7:00 AM for ~30 minutes
        if hour == 7 and minute < 30:
            return round(random.uniform(4.5, 5.0), 2)  # Large usage
        else:
            # Some small standby usage
            return round(random.uniform(0.1, 0.15), 2)

    elif category == "OVEN":
        # Spike late afternoon / early evening (16:00 - 18:00)
        if 16 <= hour < 18:
            return round(random.uniform(2.0, 3.0), 2)
        else:
            # Low usage or off
            return round(random.uniform(0.05, 0.1), 2)

    elif category == "TV":
        # Typical evening usage (18:00 - 22:00)
        if 18 <= hour < 22:
            return round(random.uniform(0.8, 1.5), 2)
        else:
            return round(random.uniform(0.05, 0.1), 2)

    elif category == "MISC_APPLIANCE":
        # Random small usage
        return round(random.uniform(0.05, 0.2), 2)

    return 0.0

# For storing all generated readings
all_readings = []

# Generate data for each day in [start_date, end_date)
current_day = start_date
while current_day < end_date:
    for minute_offset in range(24 * 60):  # for each minute of the day
        current_time = current_day + timedelta(minutes=minute_offset)

        # If we've reached or passed the end date, break
        if current_time >= end_date:
            break

        for dev in devices:
            usage = get_current_usage(dev["category"], current_time)

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