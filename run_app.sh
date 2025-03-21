#!/bin/bash

# MongoDB Atlas connection settings
echo "=== Starting Flask app with MongoDB connection ==="
echo "MongoDB URI: ${MONGODB_URI}"
echo "MongoDB Username: ${MONGODB_USERNAME}"
echo "MongoDB Password: ********"
echo ""
echo "To correctly connect to MongoDB Atlas:"
echo "1. Edit this script with your actual MongoDB Atlas credentials"
echo "2. Make sure your IP address is whitelisted in MongoDB Atlas"
echo "3. Ensure your MongoDB user has the appropriate permissions"
echo ""

# Run the Flask app
cd app && python app.py 