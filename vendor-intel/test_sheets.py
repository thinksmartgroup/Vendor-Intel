#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from sheets_exporter import setup_google_sheets, export_to_sheets
import json
from datetime import datetime

def test_sheets_connection():
    """Test basic Google Sheets connection"""
    print("\n🔍 Testing Google Sheets Connection...")
    try:
        client, user_email = setup_google_sheets()
        print("✅ Successfully connected to Google Sheets")
        return client
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return None

def test_spreadsheet_creation(client):
    """Test creating a new spreadsheet"""
    print("\n🔍 Testing Spreadsheet Creation...")
    try:
        test_name = f"Test_Spreadsheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        spreadsheet = client.create(test_name)
        print(f"✅ Successfully created spreadsheet: {test_name}")
        print(f"📊 Spreadsheet URL: {spreadsheet.url}")
        return spreadsheet
    except Exception as e:
        print(f"❌ Spreadsheet creation failed: {str(e)}")
        return None

def test_data_export():
    """Test exporting sample data"""
    print("\n🔍 Testing Data Export...")
    
    # Create sample test data
    test_data = [{
        "company_name": "Test Company Inc.",
        "products": ["Product A", "Product B"],
        "platform_type": "Web-based",
        "c_suite_people": [{
            "name": "John Doe",
            "title": "CEO",
            "email": "john@testcompany.com",
            "phone": "123-456-7890"
        }],
        "company_phone_numbers": ["987-654-3210"],
        "is_web_based": True,
        "location": "Test City, TS",
        "website": "https://testcompany.com",
        "industry": "chiropractic"
    }]
    
    try:
        spreadsheet_url = export_to_sheets(test_data, f"Test_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        if spreadsheet_url:
            print("✅ Successfully exported test data")
            print(f"📊 Export URL: {spreadsheet_url}")
            return True
    except Exception as e:
        print(f"❌ Data export failed: {str(e)}")
        return False

def verify_credentials():
    """Verify that necessary credentials are set"""
    print("\n🔍 Verifying Credentials...")
    
    # Load environment variables
    load_dotenv()
    
    # Check for Google credentials file
    creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE')
    if not creds_file:
        print("❌ GOOGLE_CREDENTIALS_FILE environment variable not set")
        return False
    
    if not os.path.exists(creds_file):
        print(f"❌ Credentials file not found at: {creds_file}")
        return False
    
    print("✅ Credentials file found")
    return True

def create_sample_data():
    """Create sample data for all industries"""
    return [
        # Chiropractic Sample
        {
            "company_name": "Wellness Chiropractic Center",
            "products": ["Chiropractic Care", "Physical Therapy"],
            "platform_type": "Web-based",
            "c_suite_people": [{
                "name": "Dr. Jane Smith",
                "title": "Chief Medical Officer",
                "email": "jane@wellnesschiro.com",
                "phone": "123-456-7890"
            }],
            "company_phone_numbers": ["987-654-3210"],
            "is_web_based": True,
            "location": "San Francisco, CA",
            "website": "https://wellnesschiro.com",
            "industry": "chiropractic"
        },
        # Auto-Repair Sample
        {
            "company_name": "Premium Auto Care",
            "products": ["Auto Repair", "Maintenance", "Diagnostics"],
            "platform_type": "Hybrid",
            "c_suite_people": [{
                "name": "Mike Johnson",
                "title": "Owner",
                "email": "mike@premiaumauto.com",
                "phone": "321-654-0987"
            }],
            "company_phone_numbers": ["321-654-0988"],
            "is_web_based": True,
            "location": "Chicago, IL",
            "website": "https://premiumautocare.com",
            "industry": "auto-repair"
        },
        # Optometry Sample
        {
            "company_name": "Clear Vision Eye Care",
            "products": ["Eye Exams", "Contact Lenses", "Eyewear"],
            "platform_type": "Web-based",
            "c_suite_people": [{
                "name": "Dr. Sarah Chen",
                "title": "Chief Optometrist",
                "email": "sarah@clearvision.com",
                "phone": "456-789-0123"
            }],
            "company_phone_numbers": ["456-789-0124"],
            "is_web_based": True,
            "location": "Boston, MA",
            "website": "https://clearvisioncare.com",
            "industry": "optometry"
        }
    ]

def create_main_database():
    """Create and populate the main vendor database"""
    print("\n🚀 Creating Main Vendor Database\n" + "="*40)
    
    # Step 1: Verify credentials
    if not verify_credentials():
        print("\n❌ Database creation failed: Missing or invalid credentials")
        return
    
    # Step 2: Create sample data
    print("\n🔍 Preparing sample data for all industries...")
    test_data = create_sample_data()
    print("✅ Sample data prepared")
    
    # Step 3: Export to sheets
    print("\n🔍 Creating and populating database...")
    try:
        spreadsheet_url = export_to_sheets(
            test_data, 
            f"Vendor_Intelligence_Database_{datetime.now().strftime('%Y%m%d')}"
        )
        if spreadsheet_url:
            print("✅ Successfully created and populated database")
            print(f"📊 Database URL: {spreadsheet_url}")
            print("""
Next steps:
1. Access the database using the URL above
2. Verify data for all three industries (Chiropractic, Auto-Repair, Optometry)
3. Check formatting and structure
4. Share the database with team members as needed
            """)
        else:
            print("❌ Database creation failed")
    except Exception as e:
        print(f"❌ Database creation failed: {str(e)}")

if __name__ == "__main__":
    create_main_database() 