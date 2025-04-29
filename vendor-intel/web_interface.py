from flask import Flask, render_template, jsonify, request
from location_manager import LocationManager, location_manager, Location
from parallel_processor import ParallelProcessor
from summarizer import summarize_vendor_site
from search_runner import search_vendors
import query_generator
from vendor_db import VendorDatabase
from shared_state import state
import sys
import json
import os
import subprocess
import signal
from datetime import datetime
import threading
from flask_cors import CORS
from sheets_exporter import export_to_sheets
from dataclasses import dataclass, field
from typing import Dict, Set, Optional
import time
import logging
from query_generator import generate_search_queries
from vendor_search import search_vendors

# Initialize vendor database
vendor_db = VendorDatabase()

# --- Setup Logging ---
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("web_interface")

def kill_port(port):
    try:
        if sys.platform == 'darwin':
            cmd = f"lsof -i :{port} -t"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            pid = process.stdout.read().decode().strip()
            if pid:
                subprocess.run(f"kill -9 {pid}", shell=True)
                print(f"✅ Killed process {pid} using port {port}")
        elif sys.platform == 'win32':
            cmd = f"netstat -ano | findstr :{port}"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = process.stdout.read().decode()
            if output:
                pid = output.strip().split()[-1]
                subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                print(f"✅ Killed process {pid} using port {port}")
        else:
            cmd = f"fuser -n tcp {port}"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            pid = process.stdout.read().decode().strip()
            if pid:
                subprocess.run(f"kill -9 {pid}", shell=True)
                print(f"✅ Killed process {pid} using port {port}")
    except Exception as e:
        print(f"⚠️ Error killing process on port {port}: {e}")

def signal_handler(signum, frame):
    print("\nShutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

app = Flask(__name__, static_folder='static', template_folder='templates', static_url_path='/static')
CORS(app)
app.json_encoder = json.JSONEncoder
app.config['TEMPLATES_AUTO_RELOAD'] = True

location_manager = LocationManager()
processor = ParallelProcessor(max_workers=10)
INDUSTRIES = ["chiropractic", "optometry", "auto-repair"]

@app.route('/')
def index():
    print("DEBUG: Serving index page")
    return render_template('index.html', industries=INDUSTRIES)

@app.route('/api/states', methods=['GET'])
def get_states():
    try:
        states = location_manager.get_states()
        return jsonify({"states": sorted(states)})
    except Exception as e:
        logger.error(f"Error getting states: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cities', methods=['GET'])
def get_cities():
    try:
        state_filter = request.args.get('state')
        cities = location_manager.get_cities(state_filter)
        return jsonify({"cities": sorted(cities)})
    except Exception as e:
        logger.error(f"Error getting cities: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_zipcodes')
def get_zipcodes():
    state = request.args.get('state')
    city = request.args.get('city')
    print(f"DEBUG: Getting zip codes for {city}, {state}")
    zip_codes = location_manager.get_zip_codes(state, city)
    print(f"DEBUG: Found zip codes: {zip_codes}")
    return jsonify(zip_codes)

@app.route('/get_progress', methods=['GET'])
def get_progress():
    """Get current processing progress."""
    total = getattr(state, 'total', 0)
    if total == 0:
        return jsonify({
            "is_processing": state.active,
            "overall_progress": 0,
            "total": 0,
            "total_processed": 0,
            "remaining": 0,
            "successful": 0,
            "failed": 0
        })
    
    percentage = (state.total_processed / total * 100) if total > 0 else 0
    remaining = total - state.total_processed
    
    return jsonify({
        "is_processing": state.active,
        "overall_progress": round(percentage, 1),
        "total": total,
        "total_processed": state.total_processed,
        "remaining": remaining,
        "successful": state.successful,
        "failed": state.failed
    })

@app.route('/start', methods=['POST'])
def start():
    """Start processing locations."""
    if state.active:
        return jsonify({"error": "Processing already in progress"}), 400

    try:
        data = request.get_json()
        state_filter = data.get('state')
        city_filter = data.get('city')
        
        # Reset state
        state.active = True
        state.total_processed = 0
        state.successful = 0
        state.failed = 0
        
        # Start processing in a new thread
        thread = threading.Thread(target=process_locations, args=(state_filter, city_filter))
        thread.daemon = True
        thread.start()
        
        return jsonify({"status": "Processing started"})
    except Exception as e:
        logger.error(f"Error starting processing: {str(e)}")
        state.active = False
        return jsonify({"error": str(e)}), 500

@app.route('/get_latest_results', methods=['GET'])
def get_latest_results():
    """Get the latest processing results."""
    results = state.results if hasattr(state, 'results') else []
    return jsonify({
        "results": results[-10:] if results else []  # Return last 10 results
    })

@app.route('/get_vendor_count/<industry>', methods=['GET'])
def get_vendor_count(industry):
    count = vendor_db.get_vendor_count(industry)
    return jsonify({"industry": industry, "count": count})

@app.route('/get_vendors/<industry>', methods=['GET'])
def get_vendors(industry):
    vendors = vendor_db.get_all_vendors(industry)
    return jsonify({"industry": industry, "vendors": vendors})

def process_locations(state_filter=None, city_filter=None):
    """Process locations based on filters."""
    try:
        # Handle "All States" selection
        if state_filter == "All States":
            state_filter = None
        if city_filter == "All Cities":
            city_filter = None

        # Get total locations to process for progress tracking
        total_locations = len(location_manager.get_filtered_locations(state_filter, city_filter))
        if total_locations == 0:
            logger.info("No locations found matching the filters")
            state.active = False
            return

        logger.info(f"Starting to process {total_locations} locations")
        state.total = total_locations
        state.results = []  # Reset results for new batch
        
        while state.active and state.total_processed < total_locations:
            batch = location_manager.get_next_batch(state_filter, city_filter)
            if not batch:
                break

            for location in batch:
                if not state.active:
                    logger.info("Processing stopped by user")
                    break

                try:
                    logger.info(f"Processing location: {location.city}, {location.state}")
                    
                    # Generate search queries for this location
                    queries = generate_search_queries(
                        domain="software vendors",
                        location=f"{location.city}, {location.state}",
                        quantity=3
                    )
                    
                    if not queries:
                        logger.warning(f"No queries generated for {location.city}, {location.state}")
                        state.failed += 1
                        continue

                    # Search for vendors using the generated queries
                    success = False
                    for query in queries:
                        if not state.active:
                            break
                            
                        try:
                            vendors = search_vendors(query)  # Pass query as string
                            if vendors:
                                # Store results
                                for vendor in vendors:
                                    result = {
                                        "title": vendor.get("title", "Unknown"),
                                        "snippet": vendor.get("snippet", ""),
                                        "url": vendor.get("url", ""),
                                        "location": f"{location.city}, {location.state}"
                                    }
                                    state.results.append(result)
                                
                                state.successful += 1
                                logger.info(f"Found vendors for {location.city}, {location.state}")
                                success = True
                                break
                        except Exception as e:
                            logger.error(f"Error searching vendors: {str(e)}")
                    
                    if not success:
                        state.failed += 1
                    
                    state.total_processed += 1
                    location_manager.mark_location_processed(location)
                    
                    # Add a small delay between locations
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing location {location.city}, {location.state}: {str(e)}")
                    state.failed += 1
                    state.total_processed += 1

    except Exception as e:
        logger.error(f"Error in process_locations: {str(e)}")
    finally:
        state.active = False
        logger.info(f"Processing complete. Processed: {state.total_processed}/{state.total}, "
                   f"Successful: {state.successful}, Failed: {state.failed}")

def save_results(results: list, state_filter: Optional[str] = None, city_filter: Optional[str] = None):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    location_str = ""
    if state_filter:
        location_str += f"_{state_filter}"
        if city_filter:
            location_str += f"_{city_filter}"

    filename = f"results/batch_results{location_str}_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    return filename

if __name__ == '__main__':
    try:
        kill_port(5001)
        print("\nStarting Vendor Intelligence Collector...")
        print("Press Ctrl+C to stop the server")
        print("Server running at http://localhost:5001")
        app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)
