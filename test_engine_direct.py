import asyncio
from engine import ProxyWarEngine
from dotenv import load_dotenv
import os

load_dotenv()

async def main():
    engine = ProxyWarEngine(
        {"id": "A", "name": "TestA", "mbti": "ENTP", "summary": "test", "ng": ""},
        {"id": "B", "name": "TestB", "mbti": "ISFJ", "summary": "test", "ng": ""}
    )
    # ここで内部的に呼ばれるモデルを無理やりパッチしてテストする
    import anthropic
    engine.call_agent_model = lambda u, h, n, m: "MOCKED RESPONSE"
    result = await engine.run_simulation_cycle()
    for msg in engine.conversation_history:
        print(msg)

if __name__ == "__main__":
    asyncio.run(main())
