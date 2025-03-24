import os
import boto3
from pymongo import MongoClient
from pymongo.encryption import ClientEncryption
from pymongo.encryption_options import AutoEncryptionOpts
from bson.binary import STANDARD, Binary, UUID_SUBTYPE
from bson.codec_options import CodecOptions

# Configuration from environment variables
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
AWS_KMS_KEY_ID = os.environ.get("AWS_KMS_KEY_ID")
MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_USERNAME = os.environ.get("MONGODB_USERNAME")
MONGODB_PASSWORD = os.environ.get("MONGODB_PASSWORD")

# Collection names
KEY_VAULT_NAMESPACE = "encryption.__keyVault"
QE_NAMESPACE = "smart_home.users_encrypted"

def get_encryption_client():
    """Get a MongoDB client configured for automatic encryption."""
    # Connection string
    connection_string = f"mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_URI}/?retryWrites=true&w=majority"
    client = MongoClient(connection_string)
    
    # Setup key vault collection with index
    key_vault_db, key_vault_coll = KEY_VAULT_NAMESPACE.split(".")
    if key_vault_coll not in client[key_vault_db].list_collection_names():
        client[key_vault_db].create_collection(key_vault_coll)
    
    client[key_vault_db][key_vault_coll].create_index(
        [("keyAltNames", 1)],
        unique=True,
        partialFilterExpression={"keyAltNames": {"$exists": True}}
    )
    
    # KMS provider configuration
    kms_providers = {
        "aws": {
            "accessKeyId": AWS_ACCESS_KEY,
            "secretAccessKey": AWS_SECRET_KEY
        }
    }
    
    # Create ClientEncryption for key management
    client_encryption = ClientEncryption(
        kms_providers,
        KEY_VAULT_NAMESPACE,
        client,
        CodecOptions(uuid_representation=STANDARD),
    )
    
    # Get or create data key
    data_key = client[key_vault_db][key_vault_coll].find_one({"keyAltNames": "qe_demo_data_key"})
    
    if not data_key:
        # Create a new data key
        data_key_id = client_encryption.create_data_key(
            "aws",
            master_key={
                "region": "us-east-1",
                "key": AWS_KMS_KEY_ID,
                "endpoint": "kms.us-east-1.amazonaws.com"
            },
            key_alt_names=["qe_demo_data_key"]
        )
    else:
        data_key_id = data_key["_id"]
    
    # Define encryption schema
    encrypted_fields_map = {
        QE_NAMESPACE: {
            "fields": [
                {
                    "path": "age",
                    "bsonType": "int",
                    "keyId": data_key_id,
                    "queries": [{"queryType": "equality"}, {"queryType": "range"}]
                },
                {
                    "path": "location.region",
                    "bsonType": "string",
                    "keyId": data_key_id,
                    "queries": [{"queryType": "equality"}]
                }
            ]
        }
    }
    
    # Create encrypted client
    encrypted_client = MongoClient(
        connection_string,
        auto_encryption_opts=AutoEncryptionOpts(
            kms_providers=kms_providers,
            key_vault_namespace=KEY_VAULT_NAMESPACE,
            encrypted_fields_map=encrypted_fields_map
        )
    )
    
    return encrypted_client, client_encryption

def close_encryption_resources(encrypted_client, client_encryption):
    """Close encryption resources to prevent memory leaks."""
    if client_encryption:
        client_encryption.close()
    
    if encrypted_client:
        encrypted_client.close() 