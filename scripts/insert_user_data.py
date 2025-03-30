import random
import os
import argparse
from pymongo import MongoClient
from datetime import datetime, timedelta

def generate_user_data(num_users=1000, global_region=None):
    """
    Generates sample user documents with an embedded 'devices' array.
    Each user will have 1-3 random devices.
    """
    print(f"\nGenerating data for {num_users} users in {global_region if global_region else 'default regions'}...")
    brands = ["Samsung", "LG", "Philips", "GE", "Nest", "Ecobee"]
    device_types = ["Smart Speaker", "Smart Display", "Smart Thermostat", "Smart Light", "Smart Camera", "Space Heater"]
    
    # Define location data based on global region
    location_data = {
        "North America": {
            "New York": {"region": "Northeast", "zipcodes": ["10001", "10002", "10003", "10004", "10005"]},
            "Chicago": {"region": "Midwest", "zipcodes": ["60601", "60602", "60603", "60604", "60605"]},
            "Los Angeles": {"region": "West Coast", "zipcodes": ["90001", "90002", "90003", "90004", "90005"]},
            "San Francisco": {"region": "West Coast", "zipcodes": ["94101", "94102", "94103", "94104", "94105"]},
            "Miami": {"region": "Southeast", "zipcodes": ["33101", "33102", "33103", "33104", "33105"]}
        },
        "Europe": {
            "London": {"region": "UK", "zipcodes": ["E1", "EC1", "N1", "NW1", "SE1"]},
            "Paris": {"region": "France", "zipcodes": ["75001", "75002", "75003", "75004", "75005"]},
            "Berlin": {"region": "Germany", "zipcodes": ["10115", "10117", "10119", "10178", "10179"]},
            "Madrid": {"region": "Spain", "zipcodes": ["28001", "28002", "28003", "28004", "28005"]},
            "Rome": {"region": "Italy", "zipcodes": ["00100", "00121", "00122", "00123", "00124"]}
        }
    }

    # Select appropriate location data based on global_region
    if global_region:
        active_locations = location_data[global_region]
    else:
        active_locations = location_data["North America"]  # Default to North America

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
        city = random.choice(list(active_locations.keys()))
        region = active_locations[city]["region"]
        zipcode = random.choice(active_locations[city]["zipcodes"])
        
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
            "global_region": global_region if global_region else "North America",
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
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Generate and insert user data into MongoDB')
    parser.add_argument('--global-region', choices=['North America', 'Europe'], 
                      help='Specify the global region for the users (North America or Europe)')
    parser.add_argument('--num-users', type=int, default=1000,
                      help='Number of users to generate (default: )')
    
    args = parser.parse_args()
    
    print("Starting the MongoDB query script...")
    print(f"Global Region: {args.global_region if args.global_region else 'North America (default)'}")
    
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

    # Generate and insert user data with specified global region
    users_data = generate_user_data(args.num_users, args.global_region)
    
    # Clear existing data if needed
    users_collection.delete_many({})
    
    # Insert the new user data
    result = users_collection.insert_many(users_data)
    print(f"\nInserted {len(result.inserted_ids)} users")

    # Example queries
    print("\nExecuting sample queries...")
    
    # Query by global region
    if args.global_region:
        query = {"global_region": args.global_region}
        results = users_collection.find(query).limit(5)
        
        print(f"\nSample users from {args.global_region}:")
        print("-" * 50)
        for user_doc in results:
            print(
                f"User {user_doc['name']} "
                f"(City: {user_doc['location']['city']}, "
                f"Region: {user_doc['location']['region']}) "
                f"Email: {user_doc['email']}"
            )

    # Clean up the connection
    print("\nClosing MongoDB connection...")
    client.close()
    print("Script completed successfully!")

if __name__ == "__main__":
    main()