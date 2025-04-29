from serpapi import GoogleSearch
import os
import time
from shared_state import state
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Read the SerpAPI key safely
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
if not SERPAPI_API_KEY:
    raise ValueError("❌ SERPAPI_API_KEY not found in environment variables! Please check .env file.")

def search_vendors(queries, results_per_query=5):
    """Search for vendor URLs using the provided queries"""
    all_urls = set()
    total_queries = len(queries)
    search_active = True

    print(f"\n🔍 Starting vendor search with {total_queries} queries")
    print("=" * 50)

    for i, query in enumerate(queries, 1):
        if not state.active:
            print("\n🛑 Processing stopped by user")
            break
        if not search_active:
            print("\n🛑 Search stopped")
            break

        print(f"\n📝 Query {i}/{total_queries}: {query}")
        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": SERPAPI_API_KEY,
                "num": results_per_query,
                "gl": "us",
                "hl": "en",
                "output": "json",
                "source": "python"
            }

            print("🌐 Sending search request to SerpAPI...")
            search = GoogleSearch(params)
            results = search.get_dict()

            if "organic_results" in results:
                new_urls = 0
                for result in results["organic_results"]:
                    url = result.get("link")
                    if url and url not in all_urls:
                        all_urls.add(url)
                        new_urls += 1
                        print(f"✨ New URL found: {url}")
                print(f"📊 Found {new_urls} new URLs in this query")
            else:
                print("⚠️ No organic results found in this query")

            print(f"📈 Search Progress: {(i/total_queries*100):.1f}% complete")
            print(f"📊 Total unique URLs found: {len(all_urls)}")

            time.sleep(2)  # Delay to avoid rate limiting

        except Exception as e:
            print(f"❌ Error executing query: {str(e)}")
            if "rate limit" in str(e).lower():
                print("⚠️ Rate limit detected, pausing for 5 seconds...")
                time.sleep(5)
                continue
            elif "quota" in str(e).lower():
                print("⚠️ API quota exceeded, stopping search.")
                search_active = False
                break
            else:
                print("⚠️ Unknown error, skipping...")
                continue

    print(f"\n🏁 Vendor search complete. Found {len(all_urls)} unique URLs.")
    return list(all_urls)
