import asyncio
from engine import ProxyWarEngine
from dotenv import load_dotenv

load_dotenv()

async def main():
    engine = ProxyWarEngine(
        {"id": "A", "name": "TestA", "mbti": "ENTP", "ng": "None"},
        {"id": "B", "name": "TestB", "mbti": "ISFJ", "ng": "None"}
    )
    result = await engine.run_simulation_cycle()
    print("SUCCESS:", result)

if __name__ == "__main__":
    asyncio.run(main())
