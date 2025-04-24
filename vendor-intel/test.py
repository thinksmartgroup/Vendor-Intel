import os
from dotenv import load_dotenv
from serpapi import GoogleSearch

# Load .env file if it exists
load_dotenv()

# Try to get your actual key
api_key = os.getenv("SERPAPI_KEY", "demo")

params = {
    "q": "chiropractor software vendors",
    "location": "California, United States",
    "hl": "en",
    "gl": "us",
    "api_key": api_key
}

search = GoogleSearch(params)
results = search.get_dict()

print(f"\n🔑 Using API key: {'demo (fallback)' if api_key == 'demo' else 'your real key'}")
print("🔍 Search Results:")

organic = results.get("organic_results")

if not organic:
    print("⚠️ No results returned. Possibly due to demo key limits or a dry query.")
    if api_key == "demo":
        print("👉 Consider setting your real SERPAPI_API_KEY in a .env file.")
else:
    for result in organic:
        title = result.get("title")
        link = result.get("link")
        print(f"• {title} — {link}")
