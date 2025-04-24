import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import re
import time
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro-preview-03-25')
    logger.info(f"Using Gemini model: gemini-2.5-pro-preview-03-25")
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
    max_retries = 3
    retry_delay = 2  # seconds
    
    try:
        logger.info(f"Processing URL: {url}")
        logger.debug(f"Fetching content from {url}")
        response = requests.get(url, timeout=5)
        logger.debug(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch {url}: HTTP {response.status_code}")
            return None
            
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)[:8000]
        logger.debug(f"Extracted {len(text)} characters of text")
        
        # Extract phone numbers
        phone_numbers = extract_phone_numbers(text)
        logger.debug(f"Found {len(phone_numbers)} phone numbers")
        
        # Check if it's web-based by looking for specific indicators
        web_based_indicators = [
            'cloud-based', 'web-based', 'saas', 'software as a service',
            'cloud platform', 'web application', 'browser-based',
            'online portal', 'web portal', 'cloud software',
            'hosted solution', 'web-enabled', 'internet-based'
        ]
        is_web_based = any(indicator in text.lower() for indicator in web_based_indicators)
        logger.debug(f"Is web-based: {is_web_based}")
        
        prompt = f"""Analyze the following vendor page from {url} and extract detailed information.
        You MUST return a valid JSON object with EXACTLY the following structure and types:
        {{
            "company_name": "string",                    # Company's official name
            "products": ["string"],                      # List of product names
            "platform_type": "string",                   # One of: "web-based", "desktop", "mobile", "hybrid", or "unknown"
            "c_suite_people": [                          # List of executives/key people
                {{
                    "name": "string",                    # Full name
                    "title": "string",                   # Job title
                    "email": "string",                   # Email address or empty string
                    "phone": "string"                    # Phone number or empty string
                }}
            ],
            "company_phone_numbers": ["string"],         # List of company contact numbers
            "is_web_based": boolean,                    # true if web/cloud-based, false otherwise
            "location": "string",                        # Company's primary location
            "summary": "string",                         # Brief company/product description
            "pricing_model": "string",                   # One of: "subscription", "one-time", "hybrid", "unknown"
            "target_customer_size": "string",            # One of: "small", "medium", "enterprise", "all"
            "integration_options": ["string"],           # List of supported integrations
            "deployment_options": ["string"]             # List of deployment options (e.g., "cloud", "on-premise")
        }}
        
        Rules:
        1. ALL fields must be present
        2. Use empty string "" for unknown string values
        3. Use empty array [] for unknown array values
        4. Use false for unknown boolean values
        5. For enums (platform_type, pricing_model, target_customer_size), use "unknown" if not clear
        6. Do not include any text outside the JSON object
        7. Ensure the response is valid JSON that can be parsed by json.loads()

        Page content:
        {text}
        """
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1} to generate content for {url}")
                response = model.generate_content(prompt)
                if not response or not response.text:
                    raise ValueError("Empty response from Gemini API")
                    
                result = response.text.strip()
                result = result.replace('```json', '').replace('```', '').strip()
                logger.debug(f"Raw response length: {len(result)}")
                
                # Parse and validate JSON
                import json
                data = json.loads(result)
                logger.debug("Successfully parsed JSON response")
                
                # Validate required fields and types
                required_fields = {
                    'company_name': str,
                    'products': list,
                    'platform_type': str,
                    'c_suite_people': list,
                    'company_phone_numbers': list,
                    'is_web_based': bool,
                    'location': str,
                    'summary': str,
                    'pricing_model': str,
                    'target_customer_size': str,
                    'integration_options': list,
                    'deployment_options': list
                }
                
                for field, field_type in required_fields.items():
                    if field not in data:
                        raise ValueError(f"Missing required field: {field}")
                    if not isinstance(data[field], field_type):
                        raise ValueError(f"Invalid type for {field}: expected {field_type.__name__}, got {type(data[field]).__name__}")
                logger.debug("Validated all required fields and types")
                
                # Validate enum values
                platform_types = {"web-based", "desktop", "mobile", "hybrid", "unknown"}
                pricing_models = {"subscription", "one-time", "hybrid", "unknown"}
                customer_sizes = {"small", "medium", "enterprise", "all", "unknown"}
                
                if data['platform_type'] not in platform_types:
                    logger.warning(f"Invalid platform_type: {data['platform_type']}, setting to unknown")
                    data['platform_type'] = "unknown"
                if data['pricing_model'] not in pricing_models:
                    logger.warning(f"Invalid pricing_model: {data['pricing_model']}, setting to unknown")
                    data['pricing_model'] = "unknown"
                if data['target_customer_size'] not in customer_sizes:
                    logger.warning(f"Invalid target_customer_size: {data['target_customer_size']}, setting to unknown")
                    data['target_customer_size'] = "unknown"
                
                # Update with extracted data
                data['company_phone_numbers'] = phone_numbers
                data['is_web_based'] = is_web_based or data['platform_type'] == "web-based"
                data['location'] = location
                
                logger.info(f"Successfully processed {url}")
                return data
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for {url}: {str(e)}")
                logger.error(f"Raw response: {result[:500]}...")  # Log first 500 chars of response
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to parse JSON after {max_retries} attempts")
                    return None
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to process after {max_retries} attempts")
                    return None
                    
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        return None
