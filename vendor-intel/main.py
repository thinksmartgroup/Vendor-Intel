from prompt_parser import parse_prompt
from query_generator import generate_search_queries
from search_runner import search_vendors
from summarizer import summarize_vendor_site
from logger import save_results
from sheets_exporter import export_to_sheets
from location_manager import LocationManager
from parallel_processor import ParallelProcessor
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Available industries
INDUSTRIES = ["chiropractic", "optometry", "auto-repair"]

def process_location(location_data, industry):
    """Process a single location for a specific industry"""
    location = location_data['location']
    
    try:
        # Generate queries for this location and industry
        queries = generate_search_queries(industry, location, 5)
        
        # Search for vendors
        urls = search_vendors(queries)
        
        # Process each vendor
        results = []
        for url in urls:
            summary = summarize_vendor_site(url, location)
            if summary:
                summary['industry'] = industry  # Add industry to the result
                results.append(summary)
        
        return results
    except Exception as e:
        print(f"Error processing {location} for {industry}: {e}")
        return None

def run_large_scale_collection(industry: str = None, batch_size: int = 100, max_workers: int = 10):
    """Run large-scale data collection across the US for specified industry"""
    if industry and industry not in INDUSTRIES:
        raise ValueError(f"Invalid industry. Must be one of: {', '.join(INDUSTRIES)}")
    
    # If no industry specified, process all industries
    industries_to_process = [industry] if industry else INDUSTRIES
    
    location_manager = LocationManager(batch_size=batch_size)
    processor = ParallelProcessor(max_workers=max_workers)
    
    print(f"Starting large-scale data collection")
    if industry:
        print(f"Industry: {industry}")
    else:
        print(f"Industries: {', '.join(industries_to_process)}")
    print(f"Total locations to process: {location_manager.get_total_locations()}")
    print(f"Remaining locations: {location_manager.get_remaining_locations()}")
    
    # Process in batches
    for batch in location_manager.get_location_batches():
        print(f"\nProcessing batch of {len(batch)} locations...")
        
        # Process each industry
        all_results = []
        all_errors = []
        
        for current_industry in industries_to_process:
            print(f"\nProcessing {current_industry}...")
            results, errors = processor.process_batch(batch, lambda loc: process_location(loc, current_industry))
            
            if results:
                all_results.extend(results)
            if errors:
                all_errors.extend(errors)
            
            # Save industry-specific results
            if results:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_results(results, f"results_{current_industry}_{timestamp}.json")
            
            # Save industry-specific errors
            if errors:
                with open(f"errors_{current_industry}_{timestamp}.json", 'w') as f:
                    json.dump(errors, f, indent=2)
        
        # Save combined results
        if all_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_results(all_results, f"results_combined_{timestamp}.json")
        
        # Update progress
        progress = processor.get_progress()
        print(f"\nProgress: {progress['total_processed']} locations processed")
        print(f"Successful: {progress['successful']}")
        print(f"Failed: {progress['failed']}")
        print(f"Overall progress: {location_manager.get_progress():.2f}%")
        
        # Optional: Export to Google Sheets periodically
        if progress['total_processed'] % 1000 == 0:
            sheets_url = export_to_sheets(all_results)
            if sheets_url:
                print(f"\n📊 Intermediate results exported to Google Sheets: {sheets_url}")
        
        # Small delay between batches to prevent overwhelming APIs
        time.sleep(5)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run vendor intelligence collection')
    parser.add_argument('--industry', choices=INDUSTRIES, help='Specific industry to process')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of locations per batch')
    parser.add_argument('--max-workers', type=int, default=10, help='Maximum number of parallel workers')
    
    args = parser.parse_args()
    
    run_large_scale_collection(
        industry=args.industry,
        batch_size=args.batch_size,
        max_workers=args.max_workers
    )
