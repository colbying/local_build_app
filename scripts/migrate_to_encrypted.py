#!/usr/bin/env python3
import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.encryption import ClientEncryption
from pymongo.encryption_options import AutoEncryptionOpts
from bson.binary import STANDARD
from bson.codec_options import CodecOptions

# MongoDB and AWS settings
kms_provider_name = "aws"  # Using AWS KMS instead of "local"
uri = os.environ.get("MONGODB_URI")
mongodb_username = os.environ.get("MONGODB_USERNAME")
mongodb_password = os.environ.get("MONGODB_PASSWORD")
aws_access_key = os.environ.get("AWS_ACCESS_KEY")
aws_secret_key = os.environ.get("AWS_SECRET_KEY")
aws_kms_key_id = os.environ.get("AWS_KMS_KEY_ID")

# Collection names
key_vault_database_name = "encryption"
key_vault_collection_name = "__keyVault"
key_vault_namespace = f"{key_vault_database_name}.{key_vault_collection_name}"

# For demo purposes, we're using different names than medicalRecords.patients
encrypted_database_name = "smart_home"
encrypted_collection_name = "users_encrypted"
encrypted_namespace = f"{encrypted_database_name}.{encrypted_collection_name}"

# Source collection
source_database = "smart_home"
source_collection = "users"
source_namespace = f"{source_database}.{source_collection}"

def setup_encryption():
    """Set up MongoDB client with encryption configuration"""
    # Connect to MongoDB
    connection_string = f"mongodb+srv://{mongodb_username}:{mongodb_password}@{uri}/?retryWrites=true&w=majority"
    client = MongoClient(connection_string)
    
    # Create key vault for storing encryption keys
    if key_vault_collection_name not in client[key_vault_database_name].list_collection_names():
        client[key_vault_database_name].create_collection(key_vault_collection_name)
        client[key_vault_database_name][key_vault_collection_name].create_index(
            [("keyAltNames", 1)],
            unique=True,
            partialFilterExpression={"keyAltNames": {"$exists": True}}
        )
    
    # Set up KMS configuration
    kms_providers = {
        kms_provider_name: {
            "accessKeyId": aws_access_key,
            "secretAccessKey": aws_secret_key
        }
    }
    
    # Create encryption client
    client_encryption = ClientEncryption(
        kms_providers,
        key_vault_namespace,
        client,
        CodecOptions(uuid_representation=STANDARD)
    )
    
    # Create or get encryption keys for each field
    keys = {}
    for field in ["city", "region", "zipcode", "birthday", "email"]:
        key = client[key_vault_database_name][key_vault_collection_name].find_one(
            {"keyAltNames": f"demo_{field}_key"}
        )
        if not key:
            keys[field] = client_encryption.create_data_key(
                kms_provider_name,
                master_key={
                    "region": "us-east-1",
                    "key": aws_kms_key_id,
                    "endpoint": "kms.us-east-1.amazonaws.com"
                },
                key_alt_names=[f"demo_{field}_key"]
            )
        else:
            keys[field] = key["_id"]
    
    # Define which fields to encrypt and how
    encrypted_fields_map = {
        encrypted_namespace: {
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
                    "queries": [{"queryType": "rangePreview"}]
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
            key_vault_namespace=key_vault_namespace,
            encrypted_fields_map=encrypted_fields_map
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
        source = client[source_database][source_collection]
        destination = client[encrypted_database_name][encrypted_collection_name]
        
        # Clear any existing data
        client[encrypted_database_name].drop_collection(encrypted_collection_name)
        print(f"Preparing new encrypted collection: {encrypted_namespace}")
        
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
            
            # Show that queries still work on encrypted fields
            print("\nDemonstrating query on encrypted fields:")
            count = destination.count_documents({"location.region": "West Coast"})
            print(f"Found {count} users in the West Coast region")
            
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