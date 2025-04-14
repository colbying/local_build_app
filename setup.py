#!/usr/bin/env python3
import os
import subprocess
import json
from getpass import getpass

def install_requirements():
    """Install Python requirements from requirements.txt"""
    print("\n=== Installing Python Requirements ===")
    try:
        subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True)
        print("Requirements installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        return False
    return True

def load_secrets():
    """Load existing secrets from .secrets file if it exists"""
    if os.path.exists('.secrets'):
        try:
            with open('.secrets', 'r') as f:
                secrets = json.load(f)
                # Verify all required fields are present
                required_fields = ['MONGODB_URI', 'MONGODB_USERNAME', 'MONGODB_PASSWORD']
                if all(field in secrets for field in required_fields):
                    print("\nFound valid .secrets file with all required fields:")
                    for field in required_fields:
                        print(f"✓ {field} is set")
                    return secrets
                else:
                    print("\nWarning: .secrets file is missing some required fields")
                    missing_fields = [field for field in required_fields if field not in secrets]
                    for field in missing_fields:
                        print(f"✗ {field} is missing")
        except Exception as e:
            print(f"\nWarning: Could not read existing .secrets file: {e}")
    return None

def setup_secrets():
    """Create or update .secrets file with MongoDB credentials"""
    print("\n=== Setting up MongoDB Credentials ===")
    
    # Try to load existing secrets
    existing_secrets = load_secrets()
    if existing_secrets:
        print("\nUsing existing credentials from .secrets file")
        print("\nTo update credentials, delete the .secrets file and run this script again")
        return existing_secrets
    
    # Get MongoDB credentials
    print("\nPlease enter your MongoDB Atlas credentials:")
    mongodb_uri = input("MongoDB URI: ")
    mongodb_username = input("MongoDB Username: ")
    mongodb_password = getpass("MongoDB Password: ")
    
    # Create secrets dictionary
    secrets = {
        'MONGODB_URI': mongodb_uri,
        'MONGODB_USERNAME': mongodb_username,
        'MONGODB_PASSWORD': mongodb_password
    }
    
    # Save to .secrets file
    try:
        with open('.secrets', 'w') as f:
            json.dump(secrets, f, indent=2)
        print("\n.secrets file created successfully!")
        print("Make sure to add .secrets to your .gitignore file to keep credentials secure.")
        return secrets
    except Exception as e:
        print(f"Error creating .secrets file: {e}")
        return None

def export_to_environment(secrets):
    """Export secrets to environment variables"""
    print("\n=== Exporting to Environment ===")
    try:
        for key, value in secrets.items():
            os.environ[key] = value
            print(f"Exported {key} to environment")
        
        # Verify the exports
        print("\nVerifying environment variables:")
        for key in secrets.keys():
            if key in os.environ:
                print(f"✓ {key} is set")
            else:
                print(f"✗ {key} is not set")
        
        return True
    except Exception as e:
        print(f"Error exporting to environment: {e}")
        return False

def main():
    """Main setup function"""
    print("=== Smart Home App Setup ===")
    
    # Install requirements
    if not install_requirements():
        print("Failed to install requirements. Please check your Python environment.")
        return
    
    # Setup secrets
    secrets = setup_secrets()
    if not secrets:
        print("Failed to setup secrets. Please try again.")
        return
    
    # Export to environment
    if not export_to_environment(secrets):
        print("Failed to export secrets to environment. Please try again.")
        return
    
    print("\nSetup completed successfully!")
    print("\nTo run the app:")
    print("1. Make sure your MongoDB Atlas IP is whitelisted")
    print("2. Run: ./run_app.sh")
    print("\nTo update credentials later, delete the .secrets file and run this script again.")

if __name__ == "__main__":
    main() 