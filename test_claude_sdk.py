import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    print("Error: ANTHROPIC_API_KEY not found in .env")
    exit(1)

print(f"Testing with API Key ending in: {api_key[-4:]}")

client = Anthropic(api_key=api_key)

try:
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Hello, this is a test. Please reply with 'API is working'."}
        ]
    )
    print("Success! The Claude API is working.")
    print("Response:", message.content[0].text)
except Exception as e:
    print(f"Exception occurred: {e}")
