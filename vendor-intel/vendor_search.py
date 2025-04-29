import logging
import requests
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API key from environment variable
SERP_API_KEY = os.getenv('SERPAPI_API_KEY')

def search_vendors(query: str) -> List[Dict]:
    """
    Search for vendors using the provided query string.
    
    Args:
        query (str): The search query string
        
    Returns:
        List[Dict]: A list of vendor results, each containing url, title, and snippet
    """
    if not SERP_API_KEY:
        logger.error("SERP_API_KEY not found in environment variables")
        raise ValueError("SERP_API_KEY not configured")

    try:
        # SerpAPI endpoint
        url = "https://serpapi.com/search"
        
        # Parameters for the search
        params = {
            "api_key": SERP_API_KEY,
            "engine": "google",
            "q": query,
            "num": 10,  # Number of results
            "gl": "us"  # Country code for search
        }
        
        # Make the request
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        # Extract organic results
        results = []
        if "organic_results" in data:
            for result in data["organic_results"]:
                vendor = {
                    "url": result.get("link"),
                    "title": result.get("title"),
                    "snippet": result.get("snippet")
                }
                results.append(vendor)
                
        logger.info(f"Found {len(results)} results for query: {query}")
        return results
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making search request: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error processing search results: {str(e)}")
        raise 