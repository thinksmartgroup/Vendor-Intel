import google.generativeai as genai
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

try:
    genai.configure(api_key=api_key)
    
    # Use the exact model name
    model = genai.GenerativeModel('gemini-2.5-pro-preview-03-25')
    print(f"Using Gemini model: gemini-2.5-pro-preview-03-25")
        
except Exception as e:
    raise ValueError(f"Failed to configure Gemini API: {str(e)}")

def generate_search_queries(domain, location, quantity):
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            prompt = f"""Generate {quantity} Google search queries to find software vendors in or near {location} that offer billing and management software for the {domain} industry.
            Return each query on a new line.
            Make the queries specific and targeted to find relevant vendors.
            Example format:
            chiropractic practice management software vendors in New York
            best chiropractic billing software companies near Los Angeles
            top-rated chiropractic EHR systems in Chicago
            """
            
            response = model.generate_content(prompt)
            if response and response.text:
                # Clean and validate the response
                queries = [q.strip() for q in response.text.strip().split("\n") if q.strip()]
                if len(queries) >= quantity:
                    return queries[:quantity]
                else:
                    # If we got fewer queries than requested, pad with fallback queries
                    fallback_queries = [
                        f"{domain} software vendors in {location}",
                        f"{domain} practice management software {location}",
                        f"{domain} billing software companies near {location}",
                        f"best {domain} EHR systems in {location}",
                        f"top-rated {domain} software solutions {location}"
                    ]
                    return queries + fallback_queries[:quantity - len(queries)]
            else:
                raise ValueError("Empty response from Gemini API")
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"All attempts failed. Last error: {str(e)}")
                # Return fallback queries
                return [
                    f"{domain} software vendors in {location}",
                    f"{domain} practice management software {location}",
                    f"{domain} billing software companies near {location}",
                    f"best {domain} EHR systems in {location}",
                    f"top-rated {domain} software solutions {location}"
                ]
