import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import re
import time
import logging
import json
from dotenv import load_dotenv

# --- Setup Logging ---
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("summarizer")

# --- Load environment variables ---
load_dotenv()

# --- Configure Gemini ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found. Please set it in .env")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro-preview-03-25')
    logger.info(f"✅ Using Gemini model: gemini-2.5-pro-preview-03-25")
except Exception as e:
    raise ValueError(f"❌ Failed to configure Gemini API: {str(e)}")


def extract_phone_numbers(text):
    """Extract phone numbers from text"""
    patterns = [
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # US
        r'\b\+\d{1,3}[-.]?\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Intl
        r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b'  # (xxx) xxx-xxxx
    ]
    phones = []
    for pattern in patterns:
        phones += re.findall(pattern, text)
    return list(set(phones))


def summarize_vendor_site(url, location):
    """Summarize the vendor website into structured JSON"""
    max_retries = 3
    retry_delay = 2

    try:
        logger.info(f"🌐 Fetching: {url}")
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            logger.error(f"❌ Failed HTTP {response.status_code} for {url}")
            return None

        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)[:8000]

        phone_numbers = extract_phone_numbers(text)
        logger.debug(f"📞 {len(phone_numbers)} phone numbers found")

        web_based_indicators = [
            'cloud-based', 'web-based', 'saas', 'software as a service',
            'cloud platform', 'web application', 'browser-based', 'online portal'
        ]
        is_web_based = any(indicator in text.lower() for indicator in web_based_indicators)

        prompt = f"""Analyze the following vendor page from {url} and extract detailed information.
You MUST return exactly this JSON structure with types:

{{
  "company_name": "string",
  "products": ["string"],
  "platform_type": "string",
  "c_suite_people": [{{"name": "string", "title": "string", "email": "string", "phone": "string"}}],
  "company_phone_numbers": ["string"],
  "is_web_based": boolean,
  "location": "string",
  "summary": "string",
  "pricing_model": "string",
  "target_customer_size": "string",
  "integration_options": ["string"],
  "deployment_options": ["string"]
}}

Rules:
- No extra text outside JSON
- Empty string or [] for unknowns
- "unknown" if enum unclear
- Response must parse with json.loads()

Content:
{text}
"""

        for attempt in range(max_retries):
            try:
                logger.debug(f"🧪 Gemini generation attempt {attempt+1} for {url}")
                ai_response = model.generate_content(prompt)
                result = ai_response.text.strip().replace('```json', '').replace('```', '').strip()

                data = json.loads(result)
                logger.debug(f"✅ Successfully parsed AI response for {url}")

                # Validate enums
                if data.get('platform_type') not in {"web-based", "desktop", "mobile", "hybrid", "unknown"}:
                    logger.warning(f"⚠️ Invalid platform_type for {url}, setting to unknown")
                    data['platform_type'] = "unknown"

                if data.get('pricing_model') not in {"subscription", "one-time", "hybrid", "unknown"}:
                    logger.warning(f"⚠️ Invalid pricing_model for {url}, setting to unknown")
                    data['pricing_model'] = "unknown"

                if data.get('target_customer_size') not in {"small", "medium", "enterprise", "all", "unknown"}:
                    logger.warning(f"⚠️ Invalid target_customer_size for {url}, setting to unknown")
                    data['target_customer_size'] = "unknown"

                # Fill in additional fields
                data['company_phone_numbers'] = phone_numbers
                data['is_web_based'] = is_web_based or (data.get('platform_type') == "web-based")
                data['location'] = location

                logger.info(f"🏁 Finished summarizing {url}")
                return data

            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error for {url}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"❌ Abandoning {url} after {max_retries} failures")
                    return None
            except Exception as e:
                logger.error(f"❌ Other error for {url}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"❌ Abandoning {url} after {max_retries} failures")
                    return None

    except Exception as e:
        logger.error(f"❌ Fatal error fetching {url}: {str(e)}")
        return None
