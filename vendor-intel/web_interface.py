from flask import Flask, render_template, jsonify, request
from location_manager import LocationManager
from parallel_processor import ParallelProcessor
from summarizer import summarize_vendor_site
from search_runner import search_vendors
from query_generator import generate_search_queries
import json
import os
import subprocess
import sys
import signal
from datetime import datetime
import threading
from flask_cors import CORS

# Global flag to control processing
processing_active = False
processing_lock = threading.Lock()

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
    
    return jsonify({
        'total_processed': total_processed,
        'successful': successful,
        'failed': failed,
        'overall_progress': overall_progress,
        'remaining': remaining,
        'total': total
    })

@app.route('/process_batch', methods=['POST'])
def process_batch():
    """Process a batch of locations with optional filters"""
    global processing_active
    
    with processing_lock:
        if processing_active:
            return jsonify({
                'status': 'error',
                'message': 'Processing is already in progress'
            })
        
        processing_active = True
    
    try:
        data = request.get_json()
        industry = data.get('industry', 'chiropractic')
        state = data.get('state')
        city = data.get('city')
        
        print(f"DEBUG: Processing batch with filters - industry={industry}, state={state}, city={city}")
        
        if industry not in INDUSTRIES:
            processing_active = False
            return jsonify({
                'status': 'error',
                'message': f'Invalid industry. Must be one of: {", ".join(INDUSTRIES)}'
            })
        
        # Validate location filters
        if state and not location_manager.get_states():
            processing_active = False
            return jsonify({
                'status': 'error',
                'message': 'Invalid state specified'
            })
        
        if city and not location_manager.get_cities(state):
            processing_active = False
            return jsonify({
                'status': 'error',
                'message': f'Invalid city specified for state {state}'
            })
        
        # Get next batch with filters
        try:
            batch = next(location_manager.get_location_batches(state, city))
            print(f"DEBUG: Retrieved batch of {len(batch)} locations to process")
        except StopIteration:
            processing_active = False
            return jsonify({
                'status': 'complete',
                'message': 'All locations have been processed'
            })
        
        # Process the batch
        results, errors = processor.process_batch(batch, lambda loc: process_location(loc, industry))
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if results:
            save_results(results, f"results_{industry}_{timestamp}.json")
            print(f"DEBUG: Saved {len(results)} results to results_{industry}_{timestamp}.json")
        
        # Save errors
        if errors:
            error_file = f"errors_{industry}_{timestamp}.json"
            with open(error_file, 'w') as f:
                json.dump(errors, f, indent=2)
            print(f"DEBUG: Saved {len(errors)} errors to {error_file}")
        
        return jsonify({
            'status': 'success',
            'processed': len(batch),
            'results': len(results),
            'errors': len(errors),
            'industry': industry
        })
        
    except Exception as e:
        processing_active = False
        error_msg = f"Error processing batch: {str(e)}"
        print(f"ERROR: {error_msg}")
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 500

@app.route('/stop_processing', methods=['POST'])
def stop_processing():
    global processing_active
    
    with processing_lock:
        if not processing_active:
            return jsonify({
                'status': 'error',
                'message': 'No processing is currently in progress'
            })
        
        processing_active = False
        return jsonify({
            'status': 'success',
            'message': 'Processing stopped successfully'
        })

def process_location(location_data, industry):
    """Process a single location for a specific industry"""
    if not processing_active:
        raise Exception("Processing stopped by user")
        
    location = location_data['location']
    print(f"DEBUG: Starting to process location: {location}")
    
    try:
        # Generate queries for this location and industry
        print(f"DEBUG: Generating queries for {location} in {industry} industry")
        queries = generate_search_queries(industry, location, 5)
        print(f"DEBUG: Generated queries: {queries}")
        
        # Search for vendors
        print(f"DEBUG: Searching for vendors using queries")
        urls = search_vendors(queries)
        print(f"DEBUG: Found {len(urls)} URLs: {urls}")
        
        # Process each vendor
        results = []
        for i, url in enumerate(urls):
            if not processing_active:
                raise Exception("Processing stopped by user")
                
            print(f"DEBUG: Processing URL {i+1}/{len(urls)}: {url}")
            summary = summarize_vendor_site(url, location)
            if summary:
                print(f"DEBUG: Successfully summarized URL: {url}")
                summary['industry'] = industry  # Add industry to the result
                results.append(summary)
            else:
                print(f"DEBUG: Failed to summarize URL: {url}")
        
        # Save the processed location
        print(f"DEBUG: Saving processed location: {location}")
        location_manager.save_processed_location(location)
        
        print(f"DEBUG: Completed processing location: {location}. Found {len(results)} results")
        return results
    except Exception as e:
        print(f"DEBUG: Error processing {location} for {industry}: {str(e)}")
        # Even if there's an error, mark the location as processed
        location_manager.save_processed_location(location)
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