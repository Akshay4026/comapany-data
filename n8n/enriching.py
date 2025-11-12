import requests
from dotenv import load_dotenv
import json
import os
import re

load_dotenv()

API_KEY = os.getenv("PERPLEXITY_API_KEY", "XXXXXXXXXXX")
API_URL = "https://api.perplexity.ai/chat/completions"

def clean_json_response(content: str) -> str:
    # Remove code block markers if present
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content.strip())
        content = re.sub(r"```$", "", content.strip())
    
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        return match.group(0).strip()
    
    return content.strip()
def query_perplexity(cin: str):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "user",
                "content": f"""Do a deep research and provide a concise JSON output for [{cin}] with only these fields. 
Return the response *strictly* in this JSON format without extra explanation:
{{
    "size": "employee count or classification (small, medium, large)",
    "L&D_active": "yes or no",
    "services_provided": ["list of main services the company offers, e.g., software development, cloud, consulting, product-based"],
    "decision_makers": ["3 members list of names and roles"]
}}"""
            }
        ],
        "temperature": 0.0,
        "max_output_tokens": 200
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        # Extract only model output
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Clean and parse JSON
        cleaned = clean_json_response(content)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            print("Failed to parse JSON. Raw cleaned output:", cleaned)
            return None

    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return None

# if __name__ == "__main__":
#     company_cin = "U72200TG2003PTC041835" # its my testing code
#     data = query_perplexity(company_cin)
#     print("Final parsed response:", json.dumps(data, indent=2) if data else None)


