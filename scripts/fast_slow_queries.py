#!/usr/bin/env python3
import os
import time
import datetime
import pymongo
from bson import json_util
import json

# MongoDB connection settings - modify these as needed
MONGODB_URL = "mongodb+srv://natreya:Levante123@democluster.ytvgm.mongodb.net/?retryWrites=true&w=majority&appName=DemoCluster"
DATABASE_NAME = "smart_home_data"
COLLECTION_NAME = "power_readings"

def connect_to_mongodb():
    """Connect to MongoDB and return the client and collection"""
    client = pymongo.MongoClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    return client, collection

def print_query_info(query_name, start_time, results):
    """Print information about a query execution"""
    execution_time = time.time() - start_time
    result_count = len(results) if isinstance(results, list) else 1
    
    print(f"\n--- {query_name} ---")
    print(f"Execution time: {execution_time:.4f} seconds")
    print(f"Results count: {result_count}")
    
    # Print a sample of results
    if result_count > 0:
        print("Sample result:")
        if isinstance(results, list):
            print(json.loads(json_util.dumps(results[0])))
        else:
            print(json.loads(json_util.dumps(results)))
    print("-" * 40)

def run_fast_queries(collection):
    """Run two very fast queries"""
    
    # Fast Query 1: Simple find with index on timestamp
    start_time = time.time()
    results = list(collection.find(
        {"timestamp": {"$gt": datetime.datetime(2024, 6, 1)}},
        {"device_id": 1, "current_power": 1, "timestamp": 1, "_id": 0}
    ).limit(10))
    print_query_info("FAST QUERY 1: Simple indexed find with limit", start_time, results)
    
    # Fast Query 2: Count by device category
    start_time = time.time()
    results = list(collection.aggregate([
        {"$group": {
            "_id": "$device_id.Category",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]))
    print_query_info("FAST QUERY 2: Simple group and count", start_time, results)

def run_slow_queries(collection):
    """Run two very slow, unoptimized and very expensive queries that would show up in query insights"""
    
    # Slow Query 1: Percentile calculation over large time range with complex joins
    start_time = time.time()
    print("\n--- SLOW QUERY 1: Complex percentile calculation with lookups ---")
    print("Starting execution - this may take a while...")
    
    results = list(collection.aggregate([
        # Match a large date range (potentially millions of documents)
        {"$match": {
            "timestamp": {"$gte": datetime.datetime(2024, 1, 1)}
        }},
        # First level grouping by device and day
        {"$group": {
            "_id": {
                "device": "$device_id.Device",
                "day": {"$dayOfMonth": "$timestamp"},
                "month": {"$month": "$timestamp"}
            },
            "deviceInfo": {"$first": "$device_id"},
            "dailyAvgPower": {"$avg": "$current_power"},
            "dailyMaxPower": {"$max": "$current_power"},
            "sampleTimestamp": {"$first": "$timestamp"}
        }},
        # Second level grouping to calculate percentiles by device
        {"$group": {
            "_id": "$_id.device",
            "deviceInfo": {"$first": "$deviceInfo"},
            "powerPercentiles": {
                "$percentile": {
                    "input": "$dailyAvgPower",
                    "p": [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99],
                    "method": "approximate"
                }
            },
            "maxPowerByDay": {"$push": {
                "day": {"$concat": [
                    {"$toString": "$_id.month"}, 
                    "-", 
                    {"$toString": "$_id.day"}
                ]},
                "maxPower": "$dailyMaxPower"
            }}
        }},
        # Join with itself to get additional data
        {"$lookup": {
            "from": COLLECTION_NAME,
            "let": {"deviceId": "$_id"},
            "pipeline": [
                {"$match": {
                    "$expr": {"$eq": ["$device_id.Device", "$$deviceId"]}
                }},
                {"$group": {
                    "_id": {
                        "hour": {"$hour": "$timestamp"}
                    },
                    "hourlyAvgPower": {"$avg": "$current_power"}
                }},
                {"$sort": {"_id.hour": 1}}
            ],
            "as": "hourlyPattern"
        }},
        # Additional processing
        {"$addFields": {
            "p50": {"$arrayElemAt": ["$powerPercentiles", 2]},
            "p95": {"$arrayElemAt": ["$powerPercentiles", 5]},
            "dayOverP95Count": {
                "$size": {
                    "$filter": {
                        "input": "$maxPowerByDay",
                        "as": "day",
                        "cond": {"$gt": ["$$day.maxPower", {"$arrayElemAt": ["$powerPercentiles", 5]}]}
                    }
                }
            }
        }},
        # Sort by abnormal days count
        {"$sort": {"dayOverP95Count": -1}},
        # Limit results
        {"$limit": 10}
    ]))
    
    print_query_info("SLOW QUERY 1 COMPLETED", start_time, results)
    
    # Slow Query 2: Unindexed text search with complex aggregation
    start_time = time.time()
    print("\n--- SLOW QUERY 2: Inefficient regex filter with complex calculations ---")
    print("Starting execution - this may take a while...")
    
    results = list(collection.aggregate([
        # Filter using regex on a non-indexed field (very slow)
        {"$match": {
            "$expr": {"$regexMatch": {
                "input": {"$toString": "$device_id.Name"},
                "regex": ".*[Hh]eat.*|.*[Ll]ight.*|.*[Oo]ven.*"
            }}
        }},
        # Expensive group operation
        {"$group": {
            "_id": {
                "device": "$device_id.Device",
                "hour": {"$hour": "$timestamp"},
                "dayOfWeek": {"$dayOfWeek": "$timestamp"}
            },
            "readings": {"$push": {
                "power": "$current_power", 
                "timestamp": "$timestamp",
                "voltage": "$voltage"
            }},
            "avgPower": {"$avg": "$current_power"},
            "count": {"$sum": 1}
        }},
        # Complex calculations
        {"$project": {
            "device": "$_id.device",
            "hour": "$_id.hour",
            "dayOfWeek": "$_id.dayOfWeek",
            "avgPower": 1,
            "count": 1,
            "stdDev": {"$stdDevPop": "$readings.power"},
            "voltageVariance": {"$stdDevPop": "$readings.voltage"},
            "anomalyScore": {
                "$divide": [
                    {"$stdDevPop": "$readings.power"},
                    {"$cond": [
                        {"$eq": [{"$avg": "$readings.power"}, 0]},
                        0.001,
                        {"$avg": "$readings.power"}
                    ]}
                ]
            }
        }},
        # More complex calculations
        {"$addFields": {
            "isWeekend": {"$in": ["$dayOfWeek", [1, 7]]},
            "timeCategory": {
                "$switch": {
                    "branches": [
                        {"case": {"$and": [{"$gte": ["$hour", 7]}, {"$lt": ["$hour", 10]}]}, "then": "morning"},
                        {"case": {"$and": [{"$gte": ["$hour", 10]}, {"$lt": ["$hour", 17]}]}, "then": "daytime"},
                        {"case": {"$and": [{"$gte": ["$hour", 17]}, {"$lt": ["$hour", 23]}]}, "then": "evening"}
                    ],
                    "default": "night"
                }
            }
        }},
        # Final grouping
        {"$group": {
            "_id": {
                "device": "$device",
                "timeCategory": "$timeCategory",
                "isWeekend": "$isWeekend"
            },
            "avgPower": {"$avg": "$avgPower"},
            "avgAnomalyScore": {"$avg": "$anomalyScore"},
            "sampleCount": {"$sum": "$count"}
        }},
        # Sort by anomaly score
        {"$sort": {"avgAnomalyScore": -1}},
        # Limit results
        {"$limit": 10}
    ]))
    
    print_query_info("SLOW QUERY 2 COMPLETED", start_time, results)

def main():
    """Main function to run the queries"""
    client, collection = connect_to_mongodb()
    
    print("\n========== RUNNING FAST QUERIES ==========")
    run_fast_queries(collection)
    
    print("\n========== RUNNING SLOW QUERIES ==========")
    print("WARNING: These queries are designed to be slow and resource-intensive")
    print("Check your MongoDB slow query log to see these queries")
    run_slow_queries(collection)
    
    print("\n========== ALL QUERIES COMPLETED ==========")
    client.close()

if __name__ == "__main__":
    main()
