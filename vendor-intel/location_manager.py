import json
import os
import threading
import logging
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field

# --- Setup Logging ---
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("location_manager")

@dataclass
class Location:
    city: str
    state: str
    zip_code: str

    def __str__(self) -> str:
        return f"{self.city}, {self.state} {self.zip_code}"

    def __hash__(self) -> int:
        return hash((self.city, self.state))

    def __eq__(self, other) -> bool:
        if not isinstance(other, Location):
            return False
        return self.city == other.city and self.state == other.state

class LocationManager:
    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self.locations: List[Location] = []
        self.location_data: Dict[str, Dict[str, List[str]]] = {}
        self.processed_locations: Set[str] = set()
        self.lock = threading.Lock()
        self._load_locations()

    def _load_locations(self):
        """Load locations from state_city_zip.json file"""
        possible_paths = [
            'state_city_zip.json',  # Current directory
            os.path.join('vendor-intel', 'state_city_zip.json'),  # vendor-intel subdirectory
        ]

        json_path = None
        for path in possible_paths:
            if os.path.exists(path):
                json_path = path
                break

        if not json_path:
            logger.error(f"❌ state_city_zip.json not found in: {', '.join(possible_paths)}")
            raise FileNotFoundError(f"state_city_zip.json not found")

        logger.info(f"📂 Loading locations from: {json_path}")
        with open(json_path, 'r') as f:
            self.location_data = json.load(f)

        # Build Location objects - only one per city/state combination
        seen_locations = set()
        for state, cities in self.location_data.items():
            for city, zip_codes in cities.items():
                # Use the first ZIP code for the city
                if zip_codes:
                    location = Location(city=city, state=state, zip_code=zip_codes[0])
                    if location not in seen_locations:
                        self.locations.append(location)
                        seen_locations.add(location)

        logger.info(f"✅ Loaded {len(self.locations)} unique city/state combinations")
        logger.info(f"📊 States available: {len(self.get_states())}")

    def get_states(self) -> Set[str]:
        """Get all states"""
        return set(self.location_data.keys())

    def get_cities(self, state: Optional[str] = None) -> Set[str]:
        """Get cities in a given state"""
        if state and state in self.location_data:
            return set(self.location_data[state].keys())
        return set()

    def get_zip_codes(self, state: Optional[str] = None, city: Optional[str] = None) -> List[str]:
        """Get zipcodes for a city"""
        if state and city:
            return self.location_data.get(state, {}).get(city, [])
        return []

    def get_next_batch(self, state_filter: Optional[str] = None, city_filter: Optional[str] = None) -> List[Location]:
        """Get next batch of unprocessed locations"""
        with self.lock:
            filtered = [
                loc for loc in self.locations
                if (not state_filter or loc.state == state_filter)
                and (not city_filter or loc.city == city_filter)
                and str(loc) not in self.processed_locations
            ]
            batch = filtered[:self.batch_size]
            logger.debug(f"📦 Providing batch of {len(batch)} locations (State filter: {state_filter}, City filter: {city_filter})")
            return batch

    def mark_location_processed(self, location: Location):
        """Mark a location as processed"""
        with self.lock:
            self.processed_locations.add(str(location))
            logger.debug(f"✅ Marked as processed: {location}")

    def get_filtered_locations(self, state_filter=None, city_filter=None) -> List[Location]:
        """Get locations filtered by state and city."""
        filtered = [
            loc for loc in self.locations
            if (not state_filter or loc.state == state_filter) and
               (not city_filter or loc.city == city_filter)
        ]
        return filtered

# --- Global instance ---
location_manager = LocationManager()
