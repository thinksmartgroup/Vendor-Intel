from flask import Flask, render_template, jsonify, request
from location_manager import LocationManager
from parallel_processor import ParallelProcessor
from summarizer import summarize_vendor_site
from search_runner import search_vendors
from query_generator import generate_search_queries
from vendor_db import VendorDatabase
import importlib
import sys

# Force reload query_generator to ensure we're using the latest version
if 'query_generator' in sys.modules:
    del sys.modules['query_generator']
from query_generator import generate_search_queries

import json
import os
import subprocess
import signal
from datetime import datetime
import threading
from flask_cors import CORS
from sheets_exporter import export_to_sheets

# Initialize vendor database
vendor_db = VendorDatabase()

# Global variables for processing state
processing_active = False
processing_lock = threading.Lock()
current_progress = {
    "total": 0,
    "processed": 0,
    "successful": 0,
    "failed": 0,
    "current_location": "",
    "results": [],
    "new_vendors": 0,
    "urls_processed": 0,
    "total_urls": 0,
    "failure_reasons": {
        "timeout": 0,
        "parsing_error": 0,
        "invalid_response": 0,
        "not_vendor": 0,
        "other": 0
    }
}

def kill_port(port):
    """Kill any process using the specified port"""
    try:
        if sys.platform == 'darwin':  # macOS
            # Find the process ID using the port
            cmd = f"lsof -i :{port} -t"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            pid = process.stdout.read().decode().strip()
            
            if pid:
                # Kill the process
                subprocess.run(f"kill -9 {pid}", shell=True)
                print(f"✅ Killed process {pid} using port {port}")
        elif sys.platform == 'win32':  # Windows
            # Find the process ID using the port
            cmd = f"netstat -ano | findstr :{port}"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = process.stdout.read().decode()
            
            if output:
                # Extract PID from the output
                pid = output.strip().split()[-1]
                # Kill the process
                subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                print(f"✅ Killed process {pid} using port {port}")
        else:  # Linux
            # Find the process ID using the port
            cmd = f"fuser -n tcp {port}"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            pid = process.stdout.read().decode().strip()
            
            if pid:
                # Kill the process
                subprocess.run(f"kill -9 {pid}", shell=True)
                print(f"✅ Killed process {pid} using port {port}")
    except Exception as e:
        print(f"⚠️ Error killing process on port {port}: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\nShutting down gracefully...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

app = Flask(__name__,
    static_folder='static',
    template_folder='templates',
    static_url_path='/static'
)

# Configure CORS to allow all origins
CORS(app)

# Configure JSON encoding
app.json_encoder = json.JSONEncoder

# Configure template auto-reload
app.config['TEMPLATES_AUTO_RELOAD'] = True

location_manager = LocationManager(batch_size=100)
processor = ParallelProcessor(max_workers=10)

# Available industries
INDUSTRIES = ["chiropractic", "optometry", "auto-repair"]

@app.route('/')
def index():
    print("DEBUG: Serving index page")
    return render_template('index.html', industries=INDUSTRIES)

@app.route('/get_states')
def get_states():
    """Get list of available states"""
    return jsonify(location_manager.get_states())

@app.route('/get_cities')
def get_cities():
    """Get list of cities for a state"""
    state = request.args.get('state')
    return jsonify(location_manager.get_cities(state))

@app.route('/get_progress')
def get_progress():
    """Get progress with optional location filters"""
    state = request.args.get('state')
    city = request.args.get('city')
    
    progress = processor.get_progress()
    total_processed = progress['total_processed']
    successful = progress['successful']
    failed = progress['failed']
    
    # Get filtered counts
    total = location_manager.get_total_locations(state, city)
    remaining = location_manager.get_remaining_locations(state, city)
    overall_progress = location_manager.get_progress(state, city)
    
    with processing_lock:
        urls_progress = {
            'urls_processed': current_progress["urls_processed"],
            'total_urls': current_progress["total_urls"],
            'url_progress': (current_progress["urls_processed"] / current_progress["total_urls"] * 100) if current_progress["total_urls"] > 0 else 0
        }
    
    return jsonify({
        'total_processed': total_processed,
        'successful': successful,
        'failed': failed,
        'overall_progress': overall_progress,
        'remaining': remaining,
        'total': total,
        'urls': urls_progress
    })

@app.route('/process_batch', methods=['POST'])
def process_batch():
    """Process a batch of locations with optional filters"""
    global processing_active, current_progress
    
    try:
        data = request.get_json()
        industry = data.get('industry')
        state = data.get('state')
        city = data.get('city')
        locations = data.get('locations', [])
        
        if not industry:
            return jsonify({"error": "Missing industry"}), 400
            
        if not locations:
            # If no locations provided, get next batch from location manager
            try:
                locations = next(location_manager.get_location_batches(state=state, city=city))
            except StopIteration:
                return jsonify({"error": "No more locations to process"}), 400
            
        with processing_lock:
            if processing_active:
                return jsonify({"error": "Batch processing already in progress"}), 409
            processing_active = True
            current_progress = {
                "total": len(locations),
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "current_location": "",
                "results": [],
                "new_vendors": 0,
                "state": state,
                "city": city,
                "industry": industry  # Add industry to track it
            }
        
        def process_batch_async():
            global processing_active, current_progress
            
            try:
                print(f"Starting batch processing for {industry}")
                for location in locations:
                    if not processing_active:
                        print("Processing stopped by user")
                        # Save any remaining results before breaking
                        with processing_lock:
                            if current_progress["results"]:
                                try:
                                    new_vendors = vendor_db.filter_new_vendors(current_progress["results"], industry)
                                    if new_vendors:
                                        vendor_db.save_vendors(new_vendors, industry)
                                        print(f"Saved {len(new_vendors)} new vendors to database during stop")
                                except Exception as e:
                                    print(f"Error saving vendors during stop: {str(e)}")
                        break
                        
                    with processing_lock:
                        current_progress["current_location"] = location
                    
                    try:
                        print(f"Processing location: {location}")
                        results = process_location(location, industry)
                        
                        with processing_lock:
                            current_progress["processed"] += 1
                            if results:
                                current_progress["successful"] += 1
                                current_progress["results"].extend(results)
                                current_progress["new_vendors"] += len(results)
                                
                                # Periodically save to database if we have enough results
                                if len(current_progress["results"]) >= 50:
                                    try:
                                        new_vendors = vendor_db.filter_new_vendors(current_progress["results"], industry)
                                        if new_vendors:
                                            vendor_db.save_vendors(new_vendors, industry)
                                            print(f"Saved {len(new_vendors)} new vendors to database")
                                        current_progress["results"] = []  # Clear after saving
                                    except Exception as e:
                                        print(f"Error in periodic save: {str(e)}")
                            else:
                                current_progress["failed"] += 1
                    except Exception as e:
                        print(f"Error processing location {location}: {str(e)}")
                        with processing_lock:
                            current_progress["processed"] += 1
                            current_progress["failed"] += 1
                
            except Exception as e:
                print(f"Error in batch processing: {str(e)}")
            finally:
                with processing_lock:
                    # Save any remaining results
                    if current_progress["results"]:
                        try:
                            new_vendors = vendor_db.filter_new_vendors(current_progress["results"], industry)
                            if new_vendors:
                                vendor_db.save_vendors(new_vendors, industry)
                                print(f"Saved final {len(new_vendors)} vendors to database")
                            
                            # Save to JSON file
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"results_{industry}_{timestamp}.json"
                            save_results(current_progress["results"], filename)
                            print(f"Saved final results to {filename}")
                        except Exception as e:
                            print(f"Error in final save: {str(e)}")
                    
                    processing_active = False
        
        # Start processing in a background thread
        thread = threading.Thread(target=process_batch_async)
        thread.daemon = True
        thread.start()
        
        return jsonify({"message": "Batch processing started"}), 202
        
    except Exception as e:
        with processing_lock:
            processing_active = False
        return jsonify({"error": str(e)}), 500

@app.route('/stop_processing', methods=['POST'])
def stop_processing():
    """Stop the current batch processing and save gathered data"""
    global processing_active, current_progress
    
    with processing_lock:
        if not processing_active:
            return jsonify({"message": "No active processing to stop"}), 400
            
        print("Stopping batch processing...")
        processing_active = False
        
        # Save any gathered results to database
        if current_progress["results"]:
            try:
                # Get the industry from the first result
                industry = current_progress["results"][0].get("industry")
                if industry:
                    # Filter and save new vendors
                    new_vendors = vendor_db.filter_new_vendors(current_progress["results"], industry)
                    if new_vendors:
                        vendor_db.save_vendors(new_vendors, industry)
                        print(f"Saved {len(new_vendors)} new vendors to database")
                    
                    # Save to JSON file with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"results_{industry}_{timestamp}.json"
                    save_results(current_progress["results"], filename)
                    print(f"Saved results to {filename}")
                    
                    return jsonify({
                        "message": "Processing stopped",
                        "vendors_saved": len(new_vendors),
                        "results_file": filename
                    }), 200
            except Exception as e:
                print(f"Error saving results during stop: {str(e)}")
                return jsonify({
                    "message": "Processing stopped but error saving results",
                    "error": str(e)
                }), 200
    
    return jsonify({"message": "Processing stopped"}), 200

@app.route('/get_progress', methods=['GET'])
def get_progress_api():
    with processing_lock:
        return jsonify(current_progress)

@app.route('/get_vendor_count/<industry>', methods=['GET'])
def get_vendor_count(industry):
    """Get the total number of vendors for an industry"""
    count = vendor_db.get_vendor_count(industry)
    return jsonify({"industry": industry, "count": count})

@app.route('/get_vendors/<industry>', methods=['GET'])
def get_vendors(industry):
    """Get all vendors for an industry"""
    vendors = vendor_db.get_all_vendors(industry)
    return jsonify({"industry": industry, "vendors": vendors})

def process_location(location, industry):
    """Process a single location and return results"""
    try:
        print(f"DEBUG: Generating queries for industry: {industry}, location: {location}")
        # Generate more search queries to find at least 100 vendors
        queries = generate_search_queries(industry, location, quantity=20)
        print(f"DEBUG: Generated queries: {queries}")
        
        if not queries:
            raise Exception("Failed to generate search queries")

        # Run searches with increased results per query
        search_results = search_vendors(queries, results_per_query=10)
        print(f"DEBUG: Search results: {len(search_results) if search_results else 0} URLs found")
        
        if not search_results:
            raise Exception("No search results found")

        # Process each result
        location_results = []
        total_urls = len(search_results)
        
        with processing_lock:
            current_progress["total_urls"] = total_urls
            current_progress["urls_processed"] = 0
            # Reset failure counts
            current_progress["failure_reasons"] = {
                "timeout": 0,
                "parsing_error": 0,
                "invalid_response": 0,
                "not_vendor": 0,
                "other": 0
            }
        
        print(f"\nProcessing {total_urls} URLs for {location}:")
        print("=" * 50)
        
        for url in search_results:
            with processing_lock:
                current_progress["urls_processed"] += 1
                urls_done = current_progress["urls_processed"]
            
            print(f"\n[URL {urls_done}/{total_urls}] Processing: {url}")
            print(f"Progress: {(urls_done/total_urls*100):.1f}% complete")
            
            try:
                vendor_info = summarize_vendor_site(url, industry)
            except TimeoutError:
                with processing_lock:
                    current_progress["failure_reasons"]["timeout"] += 1
                print(f"⏱️ Timeout error for URL {urls_done}/{total_urls}")
                continue
            except json.JSONDecodeError:
                with processing_lock:
                    current_progress["failure_reasons"]["parsing_error"] += 1
                print(f"📝 JSON parsing error for URL {urls_done}/{total_urls}")
                continue
            except Exception as e:
                with processing_lock:
                    if "timeout" in str(e).lower():
                        current_progress["failure_reasons"]["timeout"] += 1
                    else:
                        current_progress["failure_reasons"]["other"] += 1
                print(f"❌ Error processing URL {urls_done}/{total_urls}: {str(e)}")
                continue
            
            if vendor_info:
                if not vendor_info.get('is_vendor', True):  # Check if site was identified as not a vendor
                    with processing_lock:
                        current_progress["failure_reasons"]["not_vendor"] += 1
                    print(f"🚫 Not a vendor website: URL {urls_done}/{total_urls}")
                    continue
                    
                vendor_info['industry'] = industry
                vendor_info['location'] = location
                location_results.append(vendor_info)
                print(f"✅ Successfully processed URL {urls_done}/{total_urls}")
                print(f"   Company: {vendor_info.get('company_name', 'Unknown')}")
                print(f"   Products: {', '.join(vendor_info.get('products', []))}")
            else:
                with processing_lock:
                    current_progress["failure_reasons"]["invalid_response"] += 1
                print(f"❌ Failed to extract information from URL {urls_done}/{total_urls}")

        # Print summary statistics
        with processing_lock:
            failures = current_progress["failure_reasons"]
            total_failures = sum(failures.values())
            success_count = len(location_results)
            
            print(f"\nProcessing Summary for {total_urls} URLs:")
            print("=" * 50)
            print(f"✅ Successful:     {success_count} ({(success_count/total_urls*100):.1f}%)")
            print(f"❌ Failed:         {total_failures} ({(total_failures/total_urls*100):.1f}%)")
            print("\nFailure Breakdown:")
            print(f"⏱️ Timeouts:       {failures['timeout']}")
            print(f"📝 Parsing Errors: {failures['parsing_error']}")
            print(f"🚫 Not Vendors:    {failures['not_vendor']}")
            print(f"❓ Invalid Data:    {failures['invalid_response']}")
            print(f"⚠️ Other Errors:   {failures['other']}")

        # Filter out duplicates
        if location_results:
            print(f"\nFound {len(location_results)} potential vendors")
            new_vendors = vendor_db.filter_new_vendors(location_results, industry)
            print(f"Filtered to {len(new_vendors)} new unique vendors")
            
            # Save new vendors to database
            if new_vendors:
                vendor_db.save_vendors(new_vendors, industry)
                print(f"✅ Saved {len(new_vendors)} new vendors to database")
            
            return new_vendors
        
        print(f"\nProcessed all {total_urls} URLs but found no valid vendors")
        return []

    except Exception as e:
        print(f"❌ Error processing location {location}: {str(e)}")
        return None

def save_results(results, filename):
    """Save results to a file"""
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    try:
        # Kill any process using port 5001
        kill_port(5001)
        
        # Run the app on port 5001 with debug mode off
        print("\nStarting Vendor Intelligence Collector...")
        print("Press Ctrl+C to stop the server")
        print(f"Server running at http://localhost:5001")
        app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1) 