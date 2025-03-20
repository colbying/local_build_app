import random
import os
from pymongo import MongoClient
from datetime import datetime, timedelta

def generate_user_data(num_users=1000000):
    """
    Generates sample user documents with an embedded 'devices' array.
    Each user will have 1-3 random devices.
    """
    print(f"\nGenerating data for {num_users} users...")
    brands = ["Samsung", "LG", "Philips", "GE", "Nest", "Ecobee"]
    device_types = ["Smart Speaker", "Smart Display", "Smart Thermostat", "Smart Light", "Smart Camera", "Space Heater"]
    
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
        # Each user will have 1-3 devices
        num_devices = random.randint(1, 3)
        print(f"Creating User {user_id} with {num_devices} devices")
        
        # Pick a random city and its corresponding data
        city = random.choice(list(location_data.keys()))
        region = location_data[city]["region"]
        zipcode = random.choice(location_data[city]["zipcodes"])
        
        devices = []
        # Create random devices for this user
        for _ in range(num_devices):
            brand = random.choice(brands)
            device_type = random.choice(device_types)
            
            # Energy consumption varies by device type
            if device_type == "Space Heater":
                energy_consumption = random.randint(80, 150)
            else:
                energy_consumption = random.randint(20, 100)
                
            model = f"{brand}-{device_type.replace(' ', '')}-{random.randint(1,5)}"

            device_doc = {
                "brand": brand,
                "location": region,
                "deviceType": device_type,
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

def calculate_age(birthday):
    birth_date = datetime.strptime(birthday, "%Y-%m-%d")
    today = datetime.now()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def main():
    print("Starting the MongoDB query script...")
    
    # Connect to MongoDB
    try:
        uri = os.getenv('MONGODB_URI')
        username = os.getenv('MONGODB_USERNAME')
        password = os.getenv('MONGODB_PASSWORD')
        
        if not all([uri, username, password]):
            raise ValueError("Missing required MongoDB environment variables")
            
        connection_string = f"mongodb+srv://{username}:{password}@{uri}"
        client = MongoClient(connection_string)
        client.admin.command('ping')
        print("Successfully connected to MongoDB!")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return

    db = client["smart_home"]
    users_collection = db["users"]

    # Generate and insert user data
    users_data = generate_user_data()
    
    # Clear existing data if needed
    users_collection.delete_many({})
    
    # Insert the new user data
    result = users_collection.insert_many(users_data)
    print(f"\nInserted {len(result.inserted_ids)} users")

    # Example query: Find users with Smart Thermostats
    print("\nExecuting sample query for users with Smart Thermostats...")
    
    query = {
        "devices.deviceType": "Smart Thermostat"
    }

    results = users_collection.find(query)
    
    print("\nQuery Results:")
    print("-" * 50)
    
    result_count = 0
    for user_doc in results:
        result_count += 1
        print(
            f"User {user_doc['name']} "
            f"(Region: {user_doc['location']['region']}) "
            f"Email: {user_doc['email']}"
        )
    
    print("-" * 50)
    print(f"Found {result_count} users with Smart Thermostats")

    # Example query 2: Find users in the Northeast region
    print("\nExecuting sample query for users in Northeast region...")
    
    query = {
        "location.region": "Northeast"
    }

    results = users_collection.find(query)
    
    print("\nQuery Results:")
    print("-" * 50)
    
    result_count = 0
    for user_doc in results:
        result_count += 1
        print(
            f"User {user_doc['name']} "
            f"(City: {user_doc['location']['city']}) "
            f"Email: {user_doc['email']}"
        )
    
    print("-" * 50)
    print(f"Found {result_count} users in the Northeast region")

    # Clean up the connection
    print("\nClosing MongoDB connection...")
    client.close()
    print("Script completed successfully!")

if __name__ == "__main__":
    main()