import os
from flask import Flask, jsonify, send_from_directory
from pymongo import MongoClient, errors
from datetime import datetime, timedelta
from collections import defaultdict
from flask_cors import CORS

app = Flask(__name__)
# Allow all origins with more permissive CORS settings
CORS(app, resources={r"/api/*": {"origins": "*"}})

# --- MongoDB connection setup ---
# These should match what you're using in insert_ts_2.py
MONGODB_URI = os.environ.get("MONGODB_URI")          # e.g. "cluster0.mongodb.net"
MONGODB_USERNAME = os.environ.get("MONGODB_USERNAME") # e.g. "myUser"
MONGODB_PASSWORD = os.environ.get("MONGODB_PASSWORD") # e.g. "myPassword"

try:
    # Construct the connection string for MongoDB - SAME FORMAT as insert_ts_2.py
    connection_string = f"mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_URI}/?retryWrites=true&w=majority"
    print(f"Connecting to MongoDB with URI: {MONGODB_URI}")
    
    # Add timeout to fail faster if connection isn't working
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    
    # Test connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
    
    # Define database and collection
    db = client["smart_home"]
    collection = db["sensor_readings"]
except Exception as e:
    print(f"MongoDB connection error: {e}")
    print("Application will start but database operations will fail")
    # Create a client anyway to prevent app from crashing, but operations will fail
    connection_string = "mongodb://localhost:27017/"  # This won't be used
    client = MongoClient(connection_string)
    db = client["smart_home"]
    collection = db["sensor_readings"]

@app.route('/')
def serve_index():
    # Serve the index.html from the 'static' directory
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/usage')
def get_usage():
    """
    Returns the last 3 days of electricity usage.
    Groups data by minute (EST), sums current_usage for each minute.
    """
    try:
        # Calculate the cutoff (last 3 days)
        now_utc = datetime.utcnow()
        cutoff_utc = now_utc - timedelta(days=3)

        # Query for documents in the last 3 days
        docs = collection.find({"Timestamp": {"$gte": cutoff_utc}})

        # We will group by "year-month-day-hour-minute" in UTC, 
        # then convert to EST when returning. 
        usage_by_minute = defaultdict(float)

        for doc in docs:
            ts_utc = doc.get("Timestamp")
            current_usage = doc.get("current_usage", 0.0)

            if ts_utc:
                # Truncate to the minute in UTC
                truncated_utc = ts_utc.replace(second=0, microsecond=0)
                usage_by_minute[truncated_utc] += float(current_usage)

        # Sort the minutes in ascending order
        sorted_minutes = sorted(usage_by_minute.keys())

        # Prepare data for JSON response
        # Convert each minute to local EST time in 12-hour format with AM/PM
        import pytz
        est = pytz.timezone("US/Eastern")

        data_points = []
        for minute_utc in sorted_minutes:
            minute_est = minute_utc.astimezone(est)
            # Format: "03/19 08:15 PM"
            minute_label = minute_est.strftime("%m/%d %I:%M %p")
            # Alternatively, you can also separate date vs time for clarity

            data_points.append({
                "label": minute_label,
                "usage": usage_by_minute[minute_utc]
            })

        print(f"Returning {len(data_points)} data points")
        return jsonify(data_points)
    except Exception as e:
        print(f"Error in get_usage: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run the Flask app
    print("Starting Flask app on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)