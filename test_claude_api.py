import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    print("Error: ANTHROPIC_API_KEY not found in .env")
    exit(1)

url = "https://api.anthropic.com/v1/messages"
headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

data = {
    "model": "claude-sonnet-4-6",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "Hello, this is a test. Please reply with 'API is working'."}
    ]
}

req = urllib.request.Request(url, headers=headers, data=json.dumps(data).encode('utf-8'), method='POST')

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print("Success! The Claude API is working.")
        print("Response:", result['content'][0]['text'])
except urllib.error.HTTPError as e:
    print(f"Failed! HTTP Error: {e.code}")
    print("Error details:", e.read().decode('utf-8'))
except Exception as e:
    print(f"Exception occurred: {e}")
