#!/usr/bin/env python3

import os
import sys
import json
from dotenv import load_dotenv

def load_existing_secrets():
    """Load existing secrets from .secrets file if it exists."""
    secrets = {}
    if os.path.exists('.secrets'):
        try:
            with open('.secrets', 'r') as f:
                secrets = json.load(f)
        except json.JSONDecodeError:
            # If file exists but isn't JSON, try to load as env file
            load_dotenv('.secrets')
            secrets = {
                'MONGODB_URI': os.getenv('MONGODB_URI'),
                'MONGODB_USERNAME': os.getenv('MONGODB_USERNAME'),
                'MONGODB_PASSWORD': os.getenv('MONGODB_PASSWORD'),
                'AWS_ACCESS_KEY': os.getenv('AWS_ACCESS_KEY'),
                'AWS_SECRET_KEY': os.getenv('AWS_SECRET_KEY'),
                'AWS_KMS_KEY_ID': os.getenv('AWS_KMS_KEY_ID'),
                'AWS_KMS_ARN': os.getenv('AWS_KMS_ARN')
            }
    return secrets

def check_existing_aws_credentials(secrets):
    """Check if AWS credentials already exist in secrets."""
    required_creds = ['AWS_ACCESS_KEY', 'AWS_SECRET_KEY', 'AWS_KMS_KEY_ID', 'AWS_KMS_ARN']
    return all(secrets.get(cred) for cred in required_creds)

def setup_aws_credentials():
    """Set up AWS credentials for Queryable Encryption."""
    print("\n=== Setting up AWS Credentials for Queryable Encryption ===")
    
    # Load existing secrets
    existing_secrets = load_existing_secrets()
    
    # Check if AWS credentials already exist
    if check_existing_aws_credentials(existing_secrets):
        print("Found existing AWS credentials in .secrets file:")
        print("✓ AWS_ACCESS_KEY is set")
        print("✓ AWS_SECRET_KEY is set")
        print("✓ AWS_KMS_KEY_ID is set")
        print("✓ AWS_KMS_ARN is set")
        print("\nTo update credentials, delete the .secrets file and run this script again")
        return True
    
    # Get AWS credentials
    aws_access_key = input(f"AWS Access Key [{existing_secrets.get('AWS_ACCESS_KEY', '')}]: ") or existing_secrets.get('AWS_ACCESS_KEY')
    aws_secret_key = input(f"AWS Secret Key [{existing_secrets.get('AWS_SECRET_KEY', '')}]: ") or existing_secrets.get('AWS_SECRET_KEY')
    aws_kms_key_id = input(f"AWS KMS Key ID [{existing_secrets.get('AWS_KMS_KEY_ID', '')}]: ") or existing_secrets.get('AWS_KMS_KEY_ID')
    aws_kms_arn = input(f"AWS KMS ARN [{existing_secrets.get('AWS_KMS_ARN', '')}]: ") or existing_secrets.get('AWS_KMS_ARN')
    
    # Validate inputs
    if not all([aws_access_key, aws_secret_key, aws_kms_key_id, aws_kms_arn]):
        print("Error: All AWS credentials are required.")
        return False
    
    # Update existing secrets with new AWS credentials
    existing_secrets.update({
        'AWS_ACCESS_KEY': aws_access_key,
        'AWS_SECRET_KEY': aws_secret_key,
        'AWS_KMS_KEY_ID': aws_kms_key_id,
        'AWS_KMS_ARN': aws_kms_arn
    })
    
    # Write back to .secrets file in JSON format
    with open('.secrets', 'w') as f:
        json.dump(existing_secrets, f, indent=2)
    
    print("\nAWS credentials added to .secrets file")
    return True

def export_to_environment():
    """Export all secrets to the environment."""
    print("\n=== Exporting to Environment ===")
    secrets = load_existing_secrets()
    
    for key, value in secrets.items():
        if value:  # Only export non-empty values
            os.environ[key] = value
            print(f"Exported {key} to environment")
    
    # Verify AWS credentials are set
    aws_creds = ['AWS_ACCESS_KEY', 'AWS_SECRET_KEY', 'AWS_KMS_KEY_ID', 'AWS_KMS_ARN']
    missing = [cred for cred in aws_creds if not os.getenv(cred)]
    
    if missing:
        print("\nWarning: Some AWS credentials are not set in the environment:")
        for cred in missing:
            print(f"✗ {cred} is not set")
        return False
    
    print("\nVerifying environment variables:")
    for cred in aws_creds:
        print(f"✓ {cred} is set")
    return True

def main():
    """Main function to set up Queryable Encryption credentials."""
    if not os.path.exists('.secrets'):
        print("Error: .secrets file not found. Please run setup.py first.")
        sys.exit(1)
    
    if setup_aws_credentials():
        if export_to_environment():
            print("\nSetup completed successfully!")
            print("To use Queryable Encryption:")
            print("1. Make sure your AWS credentials have the necessary KMS permissions")
            print("2. Verify your MongoDB Atlas cluster supports Queryable Encryption")
            print("3. Run your application with the updated credentials")
        else:
            print("\nWarning: Some environment variables were not set correctly.")
            print("Please manually export the required AWS credentials.")
    else:
        print("\nSetup failed. Please try again.")
        sys.exit(1)

if __name__ == "__main__":
    main() 