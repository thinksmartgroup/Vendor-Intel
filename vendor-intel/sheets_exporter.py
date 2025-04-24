import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime

# Available industries
INDUSTRIES = ["chiropractic", "optometry", "auto-repair"]

def setup_google_sheets():
    # Use creds to create a client to interact with the Google Drive API
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    # Path to your service account credentials file
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        os.getenv('GOOGLE_CREDENTIALS_FILE'), scope)
    client = gspread.authorize(creds)
    return client

def create_worksheet(spreadsheet, title, headers):
    """Create a new worksheet with headers"""
    try:
        worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=20)
    except gspread.exceptions.APIError:
        # If worksheet already exists, get it
        worksheet = spreadsheet.worksheet(title)
        worksheet.clear()
    
    # Format headers
    worksheet.update('A1:L1', [headers])
    worksheet.format('A1:L1', {
        'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2},
        'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
        'horizontalAlignment': 'CENTER'
    })
    
    # Freeze header row
    worksheet.freeze(rows=1)
    
    return worksheet

def export_to_sheets(results, spreadsheet_name=None):
    try:
        client = setup_google_sheets()
        
        # Create spreadsheet name with timestamp if not provided
        if not spreadsheet_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            spreadsheet_name = f"Vendor Intelligence {timestamp}"
        
        # Create or open the spreadsheet
        try:
            spreadsheet = client.open(spreadsheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            spreadsheet = client.create(spreadsheet_name)
        
        # Define headers for each industry
        headers = [
            "Company Name", "Products", "Platform Type", "C-Suite Name",
            "C-Suite Title", "C-Suite Email", "C-Suite Phone", "Company Phone",
            "Web-Based", "Location", "Website", "Last Updated"
        ]
        
        # Create summary worksheet
        summary_ws = create_worksheet(spreadsheet, "Summary", headers)
        
        # Group results by industry
        industry_results = {industry: [] for industry in INDUSTRIES}
        for result in results:
            industry = result.get('industry', 'unknown')
            if industry in INDUSTRIES:
                industry_results[industry].append(result)
        
        # Process each industry
        for industry, industry_data in industry_results.items():
            if not industry_data:
                continue
                
            # Create industry-specific worksheet
            ws = create_worksheet(spreadsheet, industry.title(), headers)
            
            # Add data to industry worksheet
            rows = []
            for data in industry_data:
                for person in data.get("c_suite_people", []):
                    row = [
                        data.get("company_name", ""),
                        ", ".join(data.get("products", [])),
                        data.get("platform_type", ""),
                        person.get("name", ""),
                        person.get("title", ""),
                        person.get("email", ""),
                        person.get("phone", ""),
                        ", ".join(data.get("company_phone_numbers", [])),
                        "Yes" if data.get("is_web_based") else "No",
                        data.get("location", ""),
                        data.get("website", ""),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    rows.append(row)
            
            if rows:
                ws.update(f'A2:L{len(rows)+1}', rows)
                
                # Add summary row to summary worksheet
                summary_row = [
                    f"{industry.title()} Summary",
                    f"{len(industry_data)} companies",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
                summary_ws.append_row(summary_row)
        
        # Format all worksheets
        for ws in spreadsheet.worksheets():
            # Auto-resize columns
            ws.columns_auto_resize(0, len(headers))
            
            # Add alternating row colors
            ws.format(f'A2:L{ws.row_count}', {
                'backgroundColor': {
                    'red': 0.1, 'green': 0.1, 'blue': 0.1
                }
            })
            
            # Format even rows
            ws.format(f'A2:L{ws.row_count}:even', {
                'backgroundColor': {
                    'red': 0.15, 'green': 0.15, 'blue': 0.15
                }
            })
        
        print(f"✅ Data exported to Google Sheets: {spreadsheet.url}")
        return spreadsheet.url
        
    except Exception as e:
        print(f"Error exporting to Google Sheets: {e}")
        return None 