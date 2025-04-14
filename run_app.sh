#!/bin/bash

# Function to load secrets from JSON file
load_secrets() {
    local file=$1
    if [ -f "$file" ]; then
        echo "Loading environment variables from $file..."
        while IFS='=' read -r key value; do
            if [[ $key != "" && $value != "" ]]; then
                export "$key=$value"
            fi
        done < <(python3 -c "import json; f=open('$file'); d=json.load(f); [print(f'{k}={v}') for k,v in d.items()]")
        return 0
    fi
    return 1
}

# Try to load from various locations
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
elif load_secrets ".secrets"; then
    : # Secrets loaded successfully
elif load_secrets "../.secrets"; then
    : # Secrets loaded successfully
elif load_secrets "$HOME/.secrets"; then
    : # Secrets loaded successfully
else
    echo "Warning: No credentials file found in any of these locations:"
    echo "- .env"
    echo "- .secrets"
    echo "- ../.secrets"
    echo "- $HOME/.secrets"
    echo "Please create one using create_env_file.py"
fi

echo "=== Starting Flask app with MongoDB connection ==="
echo "MongoDB URI: $MONGODB_URI"
echo "MongoDB Username: $MONGODB_USERNAME"
echo "MongoDB Password: ********"
echo ""
echo "To correctly connect to MongoDB Atlas:"
echo "1. Edit this script with your actual MongoDB Atlas credentials"
echo "2. Make sure your IP address is whitelisted in MongoDB Atlas"
echo "3. Ensure your MongoDB user has the appropriate permissions"
echo ""

# Start the Flask app
python app/app.py 