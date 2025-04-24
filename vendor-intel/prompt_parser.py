import re

def parse_prompt(prompt):
    qty = int(re.search(r'\b\d+\b', prompt).group())
    domain = next((x for x in ["chiropractic", "optometry", "auto repair"] if x in prompt.lower()), None)
    location_match = re.findall(r'\d{5}|\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*,?\s?[A-Z]{2}\b', prompt)
    location = ", ".join(location_match)
    return {"quantity": qty, "domain": domain, "location": location}
