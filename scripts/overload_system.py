#!/usr/bin/env python3
import os
import time
import datetime
import pymongo
from bson import json_util
import json
import concurrent.futures
import threading
import random

# MongoDB connection settings from environment variables
MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_USERNAME = os.environ.get("MONGODB_USERNAME")
MONGODB_PASSWORD = os.environ.get("MONGODB_PASSWORD")

# Construct the connection string
MONGODB_URL = f"mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_URI}/?retryWrites=true&w=majority"

# Database and collection names
DATABASE_NAME = "smart_home"
COLLECTION_NAME = "users"

# Thread-local storage for MongoDB connections
thread_local = threading.local()

# Global flag to control when threads should stop
STOP_THREADS = False

def get_mongodb_connection():
    """Get a thread-local MongoDB connection"""
    if not hasattr(thread_local, "client"):
        thread_local.client = pymongo.MongoClient(MONGODB_URL)
    return thread_local.client, thread_local.client[DATABASE_NAME][COLLECTION_NAME]

def print_full_query(query_params):
    """Print the full aggregation pipeline"""
    print("Aggregation Pipeline:")
    print(json.dumps(query_params['pipeline'], default=str, indent=2))

def print_query_info(query_name, start_time, results, thread_id, query_params):
    """Print information about a query execution"""
    execution_time = time.time() - start_time
    result_count = len(results) if isinstance(results, list) else 1
    
    print(f"\n--- Thread {thread_id} - {query_name} ---")
    print_full_query(query_params)
    print(f"Execution time: {execution_time:.4f} seconds")
    print(f"Results count: {result_count}")

def generate_unoptimized_query():
    """Generate a complex, unoptimized query with consistent shape but random parameters"""
    # Random date range
    year = random.randint(1960, 2000)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    start_date = f"{year}-{month:02d}-{day:02d}"
    
    # Random energy consumption threshold
    energy_threshold = random.randint(50, 150)
    
    # Random sample size
    sample_size = random.randint(8000, 15000)
    
    # Random limit
    result_limit = random.randint(500, 1000)
    
    pipeline = [
        # Start with a large sample
        {"$sample": {"size": sample_size}},
        
        # Unwind the devices array
        {"$unwind": "$devices"},
        
        # Complex matching conditions
        {"$match": {
            "birthday": {"$gte": start_date},
            "devices.energyConsumption": {"$gt": energy_threshold},
            "location.region": {"$in": ["West Coast", "Northeast", "Southeast", "Midwest"]}
        }},
        
        # Group by multiple fields with complex calculations
        {"$group": {
            "_id": {
                "region": "$location.region",
                "city": "$location.city",
                "device_type": "$devices.deviceType",
                "brand": "$devices.brand"
            },
            "total_users": {"$addToSet": "$user_id"},
            "total_consumption": {"$sum": "$devices.energyConsumption"},
            "devices": {"$push": {
                "model": "$devices.model",
                "consumption": "$devices.energyConsumption"
            }}
        }},
        
        # Project with expensive operations
        {"$project": {
            "region": "$_id.region",
            "city": "$_id.city",
            "device_type": "$_id.device_type",
            "brand": "$_id.brand",
            "unique_user_count": {"$size": "$total_users"},
            "avg_consumption": {"$divide": ["$total_consumption", {"$size": "$total_users"}]},
            "device_models": "$devices",
            "consumption_stats": {
                "total": "$total_consumption",
                "per_user": {"$divide": ["$total_consumption", {"$size": "$total_users"}]},
                "per_device": {"$divide": ["$total_consumption", {"$size": "$devices"}]}
            }
        }},
        
        # Sort by multiple fields
        {"$sort": {
            "unique_user_count": -1,
            "avg_consumption": -1
        }},
        
        # Large limit to ensure significant data transfer
        {"$limit": result_limit}
    ]

    return {
        "type": "complex_analysis",
        "pipeline": pipeline,
        "parameters": {
            "start_date": start_date,
            "energy_threshold": energy_threshold,
            "sample_size": sample_size,
            "result_limit": result_limit
        }
    }

def run_continuous_queries(thread_id, duration_seconds):
    """Run queries continuously for the specified duration"""
    global STOP_THREADS
    
    _, collection = get_mongodb_connection()
    
    print(f"Thread {thread_id} starting continuous queries")
    query_count = 0
    error_count = 0
    thread_start_time = time.time()
    
    try:
        while not STOP_THREADS:
            query_params = generate_unoptimized_query()
            
            start_time = time.time()
            try:
                results = list(collection.aggregate(
                    query_params['pipeline'],
                    allowDiskUse=True  # Allow queries to use disk for large operations
                ))
                
                query_count += 1
                print_query_info(f"Query {query_count} ({query_params['type']})", 
                               start_time, results, thread_id, query_params)
                
                elapsed = time.time() - thread_start_time
                print(f"Thread {thread_id} has been running for {elapsed:.1f} seconds, "
                      f"completed {query_count} queries, {error_count} errors")
                
            except Exception as query_error:
                error_count += 1
                execution_time = time.time() - start_time
                print(f"\n--- Thread {thread_id} - QUERY ERROR ---")
                print("Failed Query:")
                print_full_query(query_params)
                print(f"Time spent before error: {execution_time:.4f} seconds")
                print(f"Error details: {str(query_error)[:200]}")
                print(f"Thread {thread_id} has encountered {error_count} errors so far")
                
                if "connection" in str(query_error).lower() or "network" in str(query_error).lower():
                    try:
                        print(f"Thread {thread_id} attempting to reconnect...")
                        thread_local.client = pymongo.MongoClient(MONGODB_URL)
                        _, collection = get_mongodb_connection()
                        print(f"Thread {thread_id} reconnection successful")
                    except Exception as reconnect_error:
                        print(f"Thread {thread_id} reconnection failed: {str(reconnect_error)[:100]}")
            
    except Exception as thread_error:
        print(f"Thread {thread_id} encountered a fatal error: {str(thread_error)[:150]}...")
    finally:
        try:
            thread_duration = time.time() - thread_start_time
            print(f"Thread {thread_id} ending after {thread_duration:.2f} seconds, "
                  f"completed {query_count} queries, encountered {error_count} errors")
            
            if hasattr(thread_local, "client"):
                thread_local.client.close()
        except:
            pass
    
    return thread_id, query_count, error_count

def main():
    """Main function to run continuous load test"""
    global STOP_THREADS
    
    # Configuration
    num_threads = 35       # Number of parallel threads
    duration_minutes = 10  # Total duration in minutes
    
    print("\n========== STARTING CONTINUOUS LOAD TEST ==========")
    print(f"Running {num_threads} parallel threads continuously for {duration_minutes} minutes")
    print(f"Each thread will run queries non-stop with no pauses")
    
    total_start_time = time.time()
    total_end_time = total_start_time + (duration_minutes * 60)
    
    # Reset the stop flag
    STOP_THREADS = False
    
    try:
        # Start the threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Submit all threads to run continuously 
            future_to_thread = {
                executor.submit(run_continuous_queries, i, duration_minutes * 60): i 
                for i in range(num_threads)
            }
            
            # Main thread monitors and reports overall progress
            while time.time() < total_end_time and not STOP_THREADS:
                elapsed = time.time() - total_start_time
                remaining = total_end_time - time.time()
                
                if elapsed % 30 < 1:  # Print status every ~30 seconds
                    print(f"\n--- STATUS UPDATE: {elapsed:.0f} seconds elapsed, {remaining:.0f} seconds remaining ---")
                
                time.sleep(1)  # Brief sleep to prevent main thread from consuming CPU
            
            # Signal all threads to stop
            print("\n--- TIME'S UP: Signaling threads to stop ---")
            STOP_THREADS = True
            
            # Wait for all threads to complete with a timeout
            print("Waiting for threads to complete... (max 30 seconds)")
            done, not_done = concurrent.futures.wait(
                future_to_thread.keys(), 
                timeout=30,
                return_when=concurrent.futures.ALL_COMPLETED
            )
            
            if not_done:
                print(f"{len(not_done)} threads did not complete gracefully")
            
            # Process results
            total_queries = 0
            total_errors = 0
            for future in done:
                try:
                    thread_id, query_count, error_count = future.result()
                    total_queries += query_count
                    total_errors += error_count
                    print(f"Thread {thread_id} completed {query_count} queries, encountered {error_count} errors")
                except Exception as e:
                    print(f"Thread result error: {str(e)[:100]}...")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Shutting down...")
        STOP_THREADS = True
    except Exception as e:
        print(f"\n\nAn error occurred: {str(e)[:200]}...")
        STOP_THREADS = True
    finally:
        # Set the stop flag to make sure all threads exit
        STOP_THREADS = True
        
        # Attempt to close any remaining connections
        try:
            client = pymongo.MongoClient(MONGODB_URL)
            client.close()
        except:
            pass
    
    # Calculate final statistics
    total_duration = time.time() - total_start_time
    print("\n========== CONTINUOUS LOAD TEST COMPLETED ==========")
    print(f"Total execution time: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
    print(f"Approximate queries executed: {total_queries}")
    print(f"Total errors encountered: {total_errors}")

if __name__ == "__main__":
    main() 