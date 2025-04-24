import os
import json
from datetime import datetime

class VendorDatabase:
    def __init__(self):
        self.db_dir = "vendor_data"
        self.ensure_db_directory()
        
    def ensure_db_directory(self):
        """Ensure the database directory exists"""
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)
            
    def get_industry_file(self, industry):
        """Get the JSON file path for an industry"""
        return os.path.join(self.db_dir, f"{industry}_vendors.json")
    
    def load_existing_vendors(self, industry):
        """Load existing vendors for an industry"""
        try:
            file_path = self.get_industry_file(industry)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading vendors for {industry}: {e}")
            return []
    
    def is_duplicate(self, vendor, existing_vendors):
        """Check if a vendor already exists in the database"""
        if not existing_vendors:
            return False
            
        for existing in existing_vendors:
            # Check for duplicate based on company name or website
            if (vendor.get('company_name') and vendor['company_name'] == existing.get('company_name')) or \
               (vendor.get('website') and vendor['website'] == existing.get('website')):
                return True
        return False
    
    def filter_new_vendors(self, vendors, industry):
        """Filter out vendors that already exist in the database"""
        existing_vendors = self.load_existing_vendors(industry)
        new_vendors = []
        
        for vendor in vendors:
            if not self.is_duplicate(vendor, existing_vendors):
                vendor['added_date'] = datetime.now().isoformat()
                new_vendors.append(vendor)
                
        return new_vendors
    
    def save_vendors(self, vendors, industry):
        """Save new vendors to the database"""
        if not vendors:
            return 0
            
        try:
            file_path = self.get_industry_file(industry)
            existing_vendors = self.load_existing_vendors(industry)
            
            # Add new vendors
            existing_vendors.extend(vendors)
            
            # Save updated vendor list
            with open(file_path, 'w') as f:
                json.dump(existing_vendors, f, indent=2)
            
            return len(vendors)
        except Exception as e:
            print(f"Error saving vendors for {industry}: {e}")
            return 0
    
    def get_vendor_count(self, industry):
        """Get the total number of vendors for an industry"""
        vendors = self.load_existing_vendors(industry)
        return len(vendors)
    
    def get_all_vendors(self, industry):
        """Get all vendors for an industry"""
        return self.load_existing_vendors(industry) 