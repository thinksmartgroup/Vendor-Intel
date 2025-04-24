import pandas as pd
import numpy as np
from typing import List, Dict, Generator, Optional
import os

class LocationManager:
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.zip_codes = self._load_zip_codes()
        self.processed_locations = self._load_processed_locations()
        
    def _load_zip_codes(self) -> pd.DataFrame:
        """Load and process US zip codes data"""
        # Read CSV with proper data types and encoding
        df = pd.read_csv('uszips.csv', dtype={
            'zip': str,
            'city': str,
            'state_id': str,
            'state_name': str,
            'county_name': str,
            'timezone': str
        }, encoding='utf-8')
        
        # Clean and prepare data
        df['zip'] = df['zip'].str.zfill(5)  # Ensure 5-digit format
        df['city'] = df['city'].str.title()  # Proper case for cities
        df['location'] = df.apply(lambda x: f"{x['city']}, {x['state_id']}", axis=1)
        
        # Remove any invalid zip codes
        df = df[df['zip'].str.match(r'^\d{5}$')]
        
        return df
    
    def _load_processed_locations(self) -> set:
        """Load already processed locations from a file"""
        if os.path.exists('processed_locations.txt'):
            with open('processed_locations.txt', 'r') as f:
                return set(line.strip() for line in f)
        return set()
    
    def save_processed_location(self, location: str):
        """Save a processed location to track progress"""
        self.processed_locations.add(location)
        with open('processed_locations.txt', 'a') as f:
            f.write(f"{location}\n")
    
    def get_location_batches(self, state: Optional[str] = None, city: Optional[str] = None, zipcode: Optional[str] = None) -> Generator[List[Dict], None, None]:
        """Generate batches of locations to process with optional filters"""
        # Start with all locations
        remaining_locations = self.zip_codes
        
        # Apply filters if provided
        if state:
            remaining_locations = remaining_locations[remaining_locations['state_id'] == state.upper()]
        if city:
            remaining_locations = remaining_locations[remaining_locations['city'].str.lower() == city.lower()]
        if zipcode:
            remaining_locations = remaining_locations[remaining_locations['zip'] == zipcode]
        
        # Filter out already processed locations
        remaining_locations = remaining_locations[~remaining_locations['location'].isin(self.processed_locations)]
        
        # Shuffle to distribute load
        remaining_locations = remaining_locations.sample(frac=1)
        
        # Create batches
        for i in range(0, len(remaining_locations), self.batch_size):
            batch = remaining_locations.iloc[i:i + self.batch_size]
            yield batch[['location', 'zip', 'state_id', 'city']].to_dict('records')
    
    def get_states(self) -> List[str]:
        """Get list of unique states"""
        return sorted(self.zip_codes['state_id'].unique().tolist())
    
    def get_cities(self, state: Optional[str] = None) -> List[str]:
        """Get list of unique cities, optionally filtered by state"""
        if state:
            return sorted(self.zip_codes[self.zip_codes['state_id'] == state.upper()]['city'].unique().tolist())
        return sorted(self.zip_codes['city'].unique().tolist())
    
    def get_zipcodes(self, state: Optional[str] = None, city: Optional[str] = None) -> List[str]:
        """Get list of unique zipcodes, optionally filtered by state and/or city"""
        df = self.zip_codes
        
        # Apply filters
        if state:
            df = df[df['state_id'] == state.upper()]
        if city:
            # Case-insensitive city match
            df = df[df['city'].str.lower() == city.lower()]
            
        # Get unique zip codes and ensure 5-digit format
        zipcodes = df['zip'].astype(str).apply(lambda x: x.zfill(5)).unique().tolist()
        
        # Sort numerically but keep as strings
        return sorted(zipcodes, key=lambda x: int(x))
    
    def get_total_locations(self, state: Optional[str] = None, city: Optional[str] = None, zipcode: Optional[str] = None) -> int:
        """Get total number of locations to process with optional filters"""
        df = self.zip_codes
        if state:
            df = df[df['state_id'] == state.upper()]
        if city:
            df = df[df['city'].str.lower() == city.lower()]
        if zipcode:
            df = df[df['zip'] == zipcode]
        return len(df)
    
    def get_remaining_locations(self, state: Optional[str] = None, city: Optional[str] = None, zipcode: Optional[str] = None) -> int:
        """Get number of remaining locations to process with optional filters"""
        total = self.get_total_locations(state, city, zipcode)
        processed = len([loc for loc in self.processed_locations 
                        if (not state or loc.endswith(f", {state.upper()}")) and
                           (not city or loc.startswith(f"{city.title()}, "))])
        return total - processed
    
    def get_progress(self, state: Optional[str] = None, city: Optional[str] = None, zipcode: Optional[str] = None) -> float:
        """Get progress as a percentage with optional filters"""
        total = self.get_total_locations(state, city, zipcode)
        if total == 0:
            return 0.0
        return (total - self.get_remaining_locations(state, city, zipcode)) / total * 100 