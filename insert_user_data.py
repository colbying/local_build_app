import random
import os
from pymongo import MongoClient
from datetime import datetime, timedelta

def generate_user_data(num_users=1000000):
    """
    Generates sample user documents with an embedded 'devices' array.
    Each user will have between 1 to 3 devices.
    """
    print(f"\nGenerating data for {num_users} users...")
    brands = ["Samsung", "LG", "Philips", "GE", "Nest", "Ecobee"]
    
    # Define location data
    location_data = {
        "New York": {"region": "Northeast", "zipcodes": ["10001", "10002", "10003", "10004", "10005"]},
        "Chicago": {"region": "Midwest", "zipcodes": ["60601", "60602", "60603", "60604", "60605"]},
        "Los Angeles": {"region": "West Coast", "zipcodes": ["90001", "90002", "90003", "90004", "90005"]},
        "San Francisco": {"region": "West Coast", "zipcodes": ["94101", "94102", "94103", "94104", "94105"]},
        "Miami": {"region": "Southeast", "zipcodes": ["33101", "33102", "33103", "33104", "33105"]}
    }

    # Function to generate a random birthday between 1960 and 2000
    def generate_birthday():
        start_date = datetime(1960, 1, 1)
        end_date = datetime(2000, 12, 31)
        time_between = end_date - start_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        return (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d")

    users = []
    for user_id in range(num_users):
        # Generate between 1 and 3 random devices for each user
        num_devices = random.randint(1, 3)
        print(f"Creating User {user_id} with {num_devices} devices")
        devices = []
        
        # Pick a random city and its corresponding data
        city = random.choice(list(location_data.keys()))
        region = location_data[city]["region"]
        zipcode = random.choice(location_data[city]["zipcodes"])
        
        for _ in range(num_devices):
            brand = random.choice(brands)
            energy_consumption = random.randint(20, 100)
            model = f"{brand}-Model-{random.randint(1,5)}"

            device_doc = {
                "brand": brand,
                "location": region,
                "energyConsumption": energy_consumption,
                "model": model
            }
            devices.append(device_doc)

        user_doc = {
            "user_id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
            "location": {
                "city": city,
                "region": region,
                "zipcode": zipcode
            },
            "birthday": generate_birthday(),
            "devices": devices
        }
        users.append(user_doc)

    return users

def main():
    print("Starting the MongoDB data insertion script...")
    
    # Connect to MongoDB
    try:
        uri = os.getenv('MONGODB_URI', 'mongodb+srv://admin:password!@cluster0.avge5.mongodb.net')
        client = MongoClient(uri)
        client.admin.command('ping')
        print("Successfully connected to MongoDB!")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return

    db = client["smart_home"]
    users_collection = db["users"]

    # Generate and insert data
    print("\nClearing existing data from users collection...")
    users_collection.delete_many({})
    user_data = generate_user_data()
    print(f"Inserting {len(user_data)} new user documents...")
    users_collection.insert_many(user_data)
    print("Data insertion complete!")

    # Clean up the connection
    print("\nClosing MongoDB connection...")
    client.close()
    print("Script completed successfully!")

if __name__ == "__main__":
    main()