#!/usr/bin/env python3
import os
import sys
import random
from datetime import datetime

# Add the app directory to the path to import qe_utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.qe_utils import get_encryption_client, close_encryption_resources, QE_NAMESPACE

def generate_users(num_users=20):
    """Generate sample user data with encrypted fields."""
    regions = ["West Coast", "Northeast", "Midwest", "Southeast", "Southwest"]
    cities = {
        "West Coast": ["Los Angeles", "San Francisco", "Seattle", "Portland", "San Diego"],
        "Northeast": ["New York", "Boston", "Philadelphia", "Washington DC"],
        "Midwest": ["Chicago", "Detroit", "Minneapolis", "Cleveland"],
        "Southeast": ["Miami", "Atlanta", "Charlotte", "Orlando"],
        "Southwest": ["Phoenix", "Houston", "Dallas", "San Antonio"]
    }
    
    users = []
    senior_west_count = 0
    
    for i in range(num_users):
        # Generate age - 20% chance of senior citizen
        is_senior = random.random() < 0.20
        age = random.randint(65, 90) if is_senior else random.randint(18, 64)
        
        # Pick a region - bias toward West Coast for demo purposes
        region = "West Coast" if random.random() < 0.3 else random.choice(regions)
        city = random.choice(cities[region])
        
        # Track seniors in West Coast for verification
        if age >= 65 and region == "West Coast":
            senior_west_count += 1
            print(f"Added senior in West Coast: User {i}, Age: {age}")
        
        users.append({
            "name": f"User {i}",
            "email": f"user{i}@example.com",
            "age": age,
            "location": {
                "city": city,
                "region": region,
                "zipcode": f"{random.randint(10000, 99999)}"
            },
            "created_at": datetime.now()
        })
    
    print(f"Generated {num_users} users ({senior_west_count} seniors in West Coast)")
    return users

def main():
    print("Generating MongoDB Queryable Encryption demo data...")
    
    try:
        # Get encrypted client
        encrypted_client, client_encryption = get_encryption_client()
        
        # Get collection reference
        db_name, coll_name = QE_NAMESPACE.split(".")
        users_collection = encrypted_client[db_name][coll_name]
        
        # Clear existing data
        encrypted_client[db_name].drop_collection(coll_name)
        
        # Generate and insert data
        users = generate_users(25)
        result = users_collection.insert_many(users)
        
        print(f"Inserted {len(result.inserted_ids)} users with encrypted fields")
        
        # Verify with query
        senior_count = users_collection.count_documents({
            "age": {"$gte": 65},
            "location.region": "West Coast"
        })
        
        print(f"Verified query found {senior_count} senior citizens in West Coast")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'encrypted_client' in locals() and 'client_encryption' in locals():
            close_encryption_resources(encrypted_client, client_encryption)

if __name__ == "__main__":
    main() 