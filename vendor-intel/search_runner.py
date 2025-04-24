from serpapi.google_search import GoogleSearch
import os
import json
import time

def search_vendors(queries, results_per_query=10):
    urls = []
    api_key = os.getenv("SERPAPI_KEY")
    
    if not api_key:
        print("Warning: SERPAPI_KEY not found in environment variables")
        return urls
    
    for query in queries:
        try:
            print(f"Searching for: {query}")
            params = {
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "num": results_per_query,  # Use the provided parameter
                "gl": "us",  # Restrict to US results
                "hl": "en"   # English language
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "error" in results:
                print(f"SerpAPI error for query '{query}': {results['error']}")
                continue
                
            if "organic_results" in results:
                for result in results["organic_results"]:
                    if "link" in result:
                        url = result["link"]
                        # Filter out irrelevant URLs
                        if any(domain in url.lower() for domain in ["google.com", "youtube.com", "facebook.com", "twitter.com", "linkedin.com"]):
                            continue
                        urls.append(url)
                        print(f"Found URL: {url}")
            
            # Add a small delay between searches to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"Error searching for query '{query}': {e}")
            continue
    
    # Remove duplicates while preserving order
    unique_urls = list(dict.fromkeys(urls))
    print(f"Found {len(unique_urls)} unique URLs")
    return unique_urls
