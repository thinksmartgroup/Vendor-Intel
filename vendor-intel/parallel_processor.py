import concurrent.futures
import time
from typing import List, Dict, Any
import queue
import threading
from datetime import datetime
import json
import os

class RateLimiter:
    def __init__(self, max_requests_per_minute: int):
        self.max_requests = max_requests_per_minute
        self.requests = queue.Queue()
        self.lock = threading.Lock()
        
    def acquire(self):
        with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            while not self.requests.empty():
                if now - self.requests.queue[0] > 60:
                    self.requests.get()
                else:
                    break
            
            if self.requests.qsize() >= self.max_requests:
                # Wait until the oldest request expires
                sleep_time = 60 - (now - self.requests.queue[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            self.requests.put(now)

class ParallelProcessor:
    def __init__(self, max_workers: int = 10, max_requests_per_minute: int = 60):
        self.max_workers = max_workers
        self.rate_limiter = RateLimiter(max_requests_per_minute)
        self.results_queue = queue.Queue()
        self.error_queue = queue.Queue()
        self.progress_file = "progress.json"
        self._load_progress()
        
    def _load_progress(self):
        """Load progress from previous runs"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                self.progress = json.load(f)
        else:
            self.progress = {
                "total_processed": 0,
                "successful": 0,
                "failed": 0,
                "last_update": datetime.now().isoformat()
            }
    
    def _save_progress(self):
        """Save current progress"""
        self.progress["last_update"] = datetime.now().isoformat()
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def process_batch(self, batch: List[Dict], process_function) -> List[Any]:
        """Process a batch of items in parallel with rate limiting"""
        results = []
        errors = []
        
        def process_item(item):
            try:
                self.rate_limiter.acquire()
                result = process_function(item)
                if result:
                    self.results_queue.put(result)
                    self.progress["successful"] += 1
                else:
                    self.progress["failed"] += 1
            except Exception as e:
                self.error_queue.put((item, str(e)))
                self.progress["failed"] += 1
            finally:
                self.progress["total_processed"] += 1
                self._save_progress()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(process_item, item) for item in batch]
            concurrent.futures.wait(futures)
        
        # Collect results
        while not self.results_queue.empty():
            results.append(self.results_queue.get())
        
        # Collect errors
        while not self.error_queue.empty():
            errors.append(self.error_queue.get())
        
        return results, errors
    
    def get_progress(self) -> Dict:
        """Get current progress statistics"""
        return self.progress 