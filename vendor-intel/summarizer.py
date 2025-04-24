import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    raise ValueError(f"Failed to configure Gemini API: {str(e)}")

def extract_phone_numbers(text):
    # Common phone number patterns
    patterns = [
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # US format
        r'\b\+\d{1,3}[-.]?\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # International format
        r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b'  # US format with parentheses
    ]
    phone_numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        phone_numbers.extend(matches)
    return list(set(phone_numbers))

def summarize_vendor_site(url, location):
    try:
        html = requests.get(url, timeout=5).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)[:8000]
        
        # Extract phone numbers
        phone_numbers = extract_phone_numbers(text)
        
        # Check if it's web-based
        is_web_based = any(keyword in text.lower() for keyword in 
                          ['cloud-based', 'web-based', 'saas', 'software as a service'])
        
        prompt = f"""Analyze the following vendor page from {url} and extract detailed information.
        Return a JSON object with the following structure:
        {{
            "company_name": "string",
            "products": ["string"],
            "platform_type": "string",
            "c_suite_people": [
                {{
                    "name": "string",
                    "title": "string",
                    "email": "string",
                    "phone": "string"
                }}
            ],
            "company_phone_numbers": ["string"],
            "is_web_based": boolean,
            "location": "string",
            "summary": "string"
        }}

        Page content:
        {text}
        """
        
        response = model.generate_content(prompt)
        result = response.text
        
        # Parse the JSON response
        try:
            import json
            data = json.loads(result)
            data['company_phone_numbers'] = phone_numbers
            data['is_web_based'] = is_web_based
            data['location'] = location
            return data
        except json.JSONDecodeError:
            print(f"Error parsing JSON response for {url}")
            return None
            
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None
