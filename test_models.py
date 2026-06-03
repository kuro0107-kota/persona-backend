import os
import asyncio
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    print("Base URL:", client.base_url)
    
    models_to_test = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620"
    ]
    for model in models_to_test:
        print(f"Testing {model}...")
        try:
            res = await client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role":"user", "content":"hi"}]
            )
            print("  SUCCESS!")
        except Exception as e:
            print("  ERROR:", str(e))

asyncio.run(main())
