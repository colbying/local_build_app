#!/usr/bin/env python3
import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.encryption import ClientEncryption
from pymongo.encryption_options import AutoEncryptionOpts
from bson.binary import STANDARD
from bson.codec_options import CodecOptions

# MongoDB and AWS settings
MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_USERNAME = os.environ.get("MONGODB_USERNAME")
MONGODB_PASSWORD = os.environ.get("MONGODB_PASSWORD")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
AWS_KMS_KEY_ID = os.environ.get("AWS_KMS_KEY_ID")

# Collection names
KEY_VAULT = "encryption.__keyVault"
SOURCE_COLLECTION = "smart_home.users"
ENCRYPTED_COLLECTION = "smart_home.users_encrypted"

def setup_encryption():
    """Set up MongoDB client with encryption configuration"""
    # Connect to MongoDB
    connection_string = f"mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_URI}/?retryWrites=true&w=majority"
    client = MongoClient(connection_string)
    
    # Create key vault for storing encryption keys
    key_vault_db, key_vault_coll = KEY_VAULT.split(".")
    if key_vault_coll not in client[key_vault_db].list_collection_names():
        client[key_vault_db].create_collection(key_vault_coll)
        client[key_vault_db][key_vault_coll].create_index(
            [("keyAltNames", 1)],
            unique=True,
            partialFilterExpression={"keyAltNames": {"$exists": True}}
        )
    
    # Set up AWS KMS configuration
    kms_providers = {
        "aws": {
            "accessKeyId": AWS_ACCESS_KEY,
            "secretAccessKey": AWS_SECRET_KEY
        }
    }
    
    # Create encryption client
    client_encryption = ClientEncryption(
        kms_providers,
        KEY_VAULT,
        client,
        CodecOptions(uuid_representation=STANDARD)
    )
    
    # Create or get encryption keys for each field
    keys = {}
    for field in ["city", "region", "zipcode", "birthday", "email"]:
        key = client[key_vault_db][key_vault_coll].find_one({"keyAltNames": f"demo_{field}_key"})
        if not key:
            keys[field] = client_encryption.create_data_key(
                "aws",
                master_key={
                    "region": "us-east-1",
                    "key": AWS_KMS_KEY_ID,
                    "endpoint": "kms.us-east-1.amazonaws.com"
                },
                key_alt_names=[f"demo_{field}_key"]
            )
        else:
            keys[field] = key["_id"]
    
    # Define which fields to encrypt and how
    schema = {
        ENCRYPTED_COLLECTION: {
            "fields": [
                {
                    "path": "location.city",
                    "bsonType": "string",
                    "keyId": keys["city"],
                    "queries": [{"queryType": "equality"}]
                },
                {
                    "path": "location.region",
                    "bsonType": "string",
                    "keyId": keys["region"],
                    "queries": [{"queryType": "equality"}]
                },
                {
                    "path": "location.zipcode",
                    "bsonType": "string",
                    "keyId": keys["zipcode"],
                    "queries": [{"queryType": "equality"}]
                },
                {
                    "path": "birthday",
                    "bsonType": "date",
                    "keyId": keys["birthday"],
                    "queries": [{"queryType": "range"}]
                },
                {
                    "path": "email",
                    "bsonType": "string",
                    "keyId": keys["email"],
                    "queries": [{"queryType": "equality"}]
                }
            ]
        }
    }
    
    # Create client with automatic encryption
    encrypted_client = MongoClient(
        connection_string,
        auto_encryption_opts=AutoEncryptionOpts(
            kms_providers=kms_providers,
            key_vault_namespace=KEY_VAULT,
            encrypted_fields_map=schema
        )
    )
    
    return encrypted_client, client_encryption

def migrate_users():
    """Migrate users to an encrypted collection"""
    print("Starting migration to encrypted collection...")
    
    try:
        # Set up encryption
        client, client_encryption = setup_encryption()
        
        # Get source and destination collections
        source_db, source_coll = SOURCE_COLLECTION.split(".")
        dest_db, dest_coll = ENCRYPTED_COLLECTION.split(".")
        
        source = client[source_db][source_coll]
        destination = client[dest_db][dest_coll]
        
        # Clear any existing data
        client[dest_db].drop_collection(dest_coll)
        print("Preparing new encrypted collection")
        
        # Get users and convert birthdays to dates
        users = list(source.find({}))
        print(f"Found {len(users)} users to migrate")
        
        for user in users:
            if 'birthday' in user:
                user['birthday'] = datetime.strptime(user['birthday'], '%Y-%m-%d')
        
        # Migrate users to encrypted collection
        if users:
            result = destination.insert_many(users)
            print(f"Successfully migrated {len(result.inserted_ids)} users")
            
            # Show a sample encrypted document
            sample = destination.find_one({})
            print("\nSample migrated user:")
            print(f"Name: {sample.get('name')}")
            print(f"Email: {sample.get('email')} (encrypted)")
            print(f"Location: {sample.get('location')} (city, region, zipcode encrypted)")
            print(f"Birthday: {sample.get('birthday')} (encrypted)")
            
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        # Clean up
        if 'client_encryption' in locals():
            client_encryption.close()
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    migrate_users() 