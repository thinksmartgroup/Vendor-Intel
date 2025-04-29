import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
from location_manager import location_manager

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

def get_location_context(city, state):
    """Get ZIP codes and generate location context for the search"""
    zip_codes = location_manager.get_zip_codes(state, city)
    
    # Get a sample of ZIP codes (max 3) to avoid overloading the query
    sample_zips = zip_codes[:3] if zip_codes else []
    
    # Create location context prompt
    context = f"""Location Details:
    - City: {city}
    - State: {state}
    - Sample ZIP codes: {', '.join(sample_zips)}
    
    Consider:
    1. Downtown/business districts
    2. Technology parks/hubs
    3. Commercial areas
    4. Local business communities
    5. Nearby metropolitan areas
    """
    return context

def generate_search_queries(domain, location, quantity=5):
    max_retries = 3
    retry_delay = 2  # seconds
    
    # Parse location into city and state
    if ',' in location:
        city, state = [part.strip() for part in location.split(',')]
    else:
        city, state = location, None
    
    # Get location context
    location_context = get_location_context(city, state) if state else ""
    
    for attempt in range(max_retries):
        try:
            prompt = f"""Generate {quantity} intelligent Google search queries to find software vendors in or near {location}.
            Focus on {domain} industry software providers.
            
            {location_context}
            
            Create diverse queries that include:
            1. General area searches
            2. ZIP code specific searches
            3. Business district searches
            4. Industry-specific locations
            5. Local technology hubs
            
            Use variations like:
            - "software vendors"
            - "technology companies"
            - "software solutions providers"
            - "tech firms"
            - "{domain} software"
            - "enterprise software"
            
            Return only the search queries, one per line.
            Do not include numbers or prefixes.
            Make each query unique and specific.
            """
            
            response = model.generate_content(prompt)
            if response and response.text:
                # Clean and validate the response
                queries = []
                for line in response.text.strip().split("\n"):
                    # Skip empty lines, numbered items, and lines that look like headers
                    line = line.strip()
                    if line and not line.startswith(('Here are', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '0.')):
                        # Remove any remaining numbers and dots from the start
                        while line and (line[0].isdigit() or line[0] == '.'):
                            line = line[1:].strip()
                        if line:
                            queries.append(line)
                
                if len(queries) >= quantity:
                    return queries[:quantity]
                else:
                    # If we got fewer queries than requested, generate intelligent fallbacks
                    fallback_queries = [
                        f"{domain} software vendors in {city} {state}",
                        f"enterprise software companies near {location}",
                        f"technology firms {domain} solutions {city}",
                        f"{domain} software providers downtown {city}",
                        f"business software companies {location}"
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
                # Return intelligent fallback queries
                return [
                    f"{domain} software vendors in {city} {state}",
                    f"enterprise software companies near {location}",
                    f"technology firms {domain} solutions {city}",
                    f"{domain} software providers downtown {city}",
                    f"business software companies {location}"
                ]
