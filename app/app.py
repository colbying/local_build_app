import os
from flask import Flask, jsonify, send_from_directory, render_template
from pymongo import MongoClient, errors
from datetime import datetime, timedelta
from collections import defaultdict
from flask_cors import CORS
from qe_utils import get_encryption_client, close_encryption_resources, QE_NAMESPACE

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
    Returns the last 3.5 days of electricity usage.
    Groups data by 5-minute intervals (EST), sums current_usage for each interval.
    """
    try:
        # Calculate the cutoff (last 3.5 days instead of 3)
        now_utc = datetime.utcnow()
        cutoff_utc = now_utc - timedelta(days=3.5)

        # Query for documents in the last 3.5 days
        docs = collection.find({"Timestamp": {"$gte": cutoff_utc}})

        # We will group by 5-minute intervals in UTC, 
        # then convert to EST when returning. 
        usage_by_interval = defaultdict(float)
        count_by_interval = defaultdict(int)

        for doc in docs:
            ts_utc = doc.get("Timestamp")
            current_usage = doc.get("current_usage", 0.0)

            if ts_utc:
                # Truncate to 5-minute intervals
                # First truncate to the minute
                truncated_minute = ts_utc.replace(second=0, microsecond=0)
                # Then calculate which 5-minute interval this belongs to
                minute_part = truncated_minute.minute
                interval_minute = (minute_part // 5) * 5
                interval_time = truncated_minute.replace(minute=interval_minute)
                
                # Accumulate usage and count for averaging
                usage_by_interval[interval_time] += float(current_usage)
                count_by_interval[interval_time] += 1

        # Calculate average usage for each 5-minute interval
        avg_usage_by_interval = {}
        for interval_time, total_usage in usage_by_interval.items():
            count = count_by_interval[interval_time]
            if count > 0:
                avg_usage_by_interval[interval_time] = total_usage / count
            else:
                avg_usage_by_interval[interval_time] = total_usage

        # Sort the intervals in ascending order
        sorted_intervals = sorted(avg_usage_by_interval.keys())

        # Prepare data for JSON response
        # Convert each interval to local EST time
        import pytz
        est = pytz.timezone("US/Eastern")

        data_points = []
        for interval_utc in sorted_intervals:
            interval_est = interval_utc.astimezone(est)
            # Format: "MM/DD hh:mm AM/PM" - Keep the date part for day separators
            interval_label = interval_est.strftime("%m/%d %I:%M %p")

            data_points.append({
                "label": interval_label,
                "usage": avg_usage_by_interval[interval_utc],
                # Add full date info for the frontend to use
                "fullDate": interval_est.strftime("%Y-%m-%d")
            })

        print(f"Returning {len(data_points)} data points (5-minute intervals)")
        return jsonify(data_points)
    except Exception as e:
        print(f"Error in get_usage: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/qe_demo')
def get_senior_citizens_west_coast():
    """Returns senior citizens in West Coast region using queryable encryption."""
    try:
        # Get encrypted client
        encrypted_client, client_encryption = get_encryption_client()
        
        # Query encrypted data
        db_name, coll_name = QE_NAMESPACE.split(".")
        results = list(encrypted_client[db_name][coll_name].find({
            "age": {"$gte": 65},
            "location.region": "West Coast"
        }))
        
        # Prepare results for JSON response
        for doc in results:
            doc["_id"] = str(doc["_id"])
            if "created_at" in doc:
                doc["created_at"] = doc["created_at"].isoformat()
        
        # Close resources
        close_encryption_resources(encrypted_client, client_encryption)
        
        return jsonify({
            "count": len(results),
            "message": "Senior citizens (age ≥ 65) in the West Coast region",
            "results": results
        })
    except Exception as e:
        print(f"QE demo error: {e}")
        return jsonify({
            "error": str(e),
            "message": "Failed to query encrypted data. Check AWS credentials and data setup."
        }), 500

@app.route('/qe_demo')
def qe_demo_page():
    """
    Render the Queryable Encryption demo page
    """
    return render_template('qe_demo.html')

if __name__ == '__main__':
    # Run the Flask app
    print("Starting Flask app on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)