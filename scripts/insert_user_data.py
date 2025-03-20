import os
from pymongo import MongoClient
from datetime import datetime, timedelta

def calculate_age(birthday):
    birth_date = datetime.strptime(birthday, "%Y-%m-%d")
    today = datetime.now()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def main():
    print("Starting the MongoDB query script...")
    
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

    # Create indexes for better query performance
    print("\nCreating indexes...")
    users_collection.create_index([("location.region", 1)])
    users_collection.create_index([("birthday", 1)])
    users_collection.create_index([("devices.brand", 1)])
    print("Index creation complete!")

    # Query for users over 65 in SoCal
    print("\nExecuting query...")
    current_date = datetime.now()
    sixty_five_years_ago = current_date - timedelta(days=65*365)
    
    query = {
        "location.region": "SoCal",
        "birthday": {"$lt": sixty_five_years_ago}
    }

    results = users_collection.find(query)
    
    print("\nQuery Results:")
    print("-" * 50)
    
    result_count = 0
    for user_doc in results:
        age = calculate_age(user_doc["birthday"])
        result_count += 1
        print(
            f"User {user_doc['name']} "
            f"(Age: {age}, Region: {user_doc['location']['region']}) "
            f"Email: {user_doc['email']}"
        )
    
    print("-" * 50)
    print(f"Found {result_count} users over 65 in SoCal")

    # Clean up the connection
    print("\nClosing MongoDB connection...")
    client.close()
    print("Script completed successfully!")

if __name__ == "__main__":
    main()