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

# MongoDB connection settings - modify these as needed
MONGODB_URL = "mongodb+srv://admin:password!@cluster0.avge5.mongodb.net/?retryWrites=true&w=majority&appName=DemoCluster"
DATABASE_NAME = "smart_home_data"
COLLECTION_NAME = "power_readings"

# Thread-local storage for MongoDB connections
thread_local = threading.local()

# Global flag to control when threads should stop
STOP_THREADS = False

def get_mongodb_connection():
    """Get a thread-local MongoDB connection"""
    if not hasattr(thread_local, "client"):
        thread_local.client = pymongo.MongoClient(MONGODB_URL)
    return thread_local.client, thread_local.client[DATABASE_NAME][COLLECTION_NAME]

def print_query_info(query_name, start_time, results, thread_id):
    """Print information about a query execution"""
    execution_time = time.time() - start_time
    result_count = len(results) if isinstance(results, list) else 1
    
    print(f"\n--- Thread {thread_id} - {query_name} ---")
    print(f"Execution time: {execution_time:.4f} seconds")
    print(f"Results count: {result_count}")

def run_continuous_queries(thread_id, duration_seconds):
    """Run queries continuously for the specified duration"""
    global STOP_THREADS
    
    # Get thread-local MongoDB connection
    _, collection = get_mongodb_connection()
    
    print(f"Thread {thread_id} starting continuous queries")
    query_count = 0
    error_count = 0
    thread_start_time = time.time()
    
    try:
        # Run queries until told to stop
        while not STOP_THREADS:
            # Generate random parameters
            year = 2024
            month = random.randint(1, 6)
            day = random.randint(1, 25)
            
            # Generate random date range
            range_type = random.choice(["short", "medium", "long"])
            if range_type == "short":
                start_date = datetime.datetime(year, month, day)
                end_date = start_date + datetime.timedelta(days=random.randint(1, 3))
            elif range_type == "medium":
                start_date = datetime.datetime(year, month, day)
                end_date = start_date + datetime.timedelta(days=random.randint(4, 10))
            else:
                start_date = datetime.datetime(year, month, day)
                end_date = start_date + datetime.timedelta(days=random.randint(11, 30))
            
            # Vary the parameters
            sample_size = random.choice([1000, 2000, 5000])
            limit_size = random.choice([20, 50, 100])
            
            # Execute the standard query with error handling for individual queries
            start_time = time.time()
            try:
                results = list(collection.aggregate([
                    {"$match": {
                        "timestamp": {"$gte": start_date, "$lte": end_date}
                    }},
                    {"$sample": {"size": sample_size}},
                    {"$group": {
                        "_id": "$device_id.Device",
                        "avgPower": {"$avg": "$current_power"},
                        "maxPower": {"$max": "$current_power"},
                        "minPower": {"$min": "$current_power"},
                        "count": {"$sum": 1}
                    }},
                    {"$match": {
                        "count": {"$gt": random.randint(2, 5)}
                    }},
                    {"$sort": {"avgPower": -1}},
                    {"$limit": limit_size}
                ]))
                
                query_count += 1
                # Report success for every query
                print_query_info(f"Query {query_count}", start_time, results, thread_id)
                
                # Also report elapsed time with each query
                elapsed = time.time() - thread_start_time
                print(f"Thread {thread_id} has been running for {elapsed:.1f} seconds, completed {query_count} queries, {error_count} errors")
                
            except Exception as query_error:
                error_count += 1
                execution_time = time.time() - start_time
                print(f"\n--- Thread {thread_id} - QUERY ERROR ---")
                print(f"Time spent before error: {execution_time:.4f} seconds")
                print(f"Error details: {str(query_error)[:200]}")
                print(f"Parameters: {range_type} range, {sample_size} samples, {limit_size} limit")
                print(f"Thread {thread_id} has encountered {error_count} errors so far")
                
                # Try to reconnect if connection-related error
                if "connection" in str(query_error).lower() or "network" in str(query_error).lower():
                    try:
                        print(f"Thread {thread_id} attempting to reconnect...")
                        thread_local.client = pymongo.MongoClient(MONGODB_URL)
                        _, collection = get_mongodb_connection()
                        print(f"Thread {thread_id} reconnection successful")
                    except Exception as reconnect_error:
                        print(f"Thread {thread_id} reconnection failed: {str(reconnect_error)[:100]}")
            
            # No deliberate sleep or pause - go straight to the next query
            
    except Exception as thread_error:
        print(f"Thread {thread_id} encountered a fatal error: {str(thread_error)[:150]}...")
    finally:
        try:
            # Get the total run time for this thread
            thread_duration = time.time() - thread_start_time
            print(f"Thread {thread_id} ending after {thread_duration:.2f} seconds, completed {query_count} queries, encountered {error_count} errors")
            
            # Close this thread's connection
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