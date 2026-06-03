"""CEO週次報告書を直接生成するスクリプト"""
import asyncio
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    from agent_system.agents.ceo_agent import CeoAgent
    from agent_system.memory_store import MemoryStore

    # DBを初期化
    store = MemoryStore()
    await store.initialize()

    print("=== CEOエージェント 週次報告書生成中... ===")
    ceo = CeoAgent()
    result = await ceo.execute()

    r = result.get("result", {})
    report = r.get("report", "（レポートなし）")
    week = r.get("week_label", "不明")

    print(f"\n【週次報告書 {week}】\n")
    print(report)
    print("\n=== 保存完了 ===")
    print(f"ログ確認: http://localhost:8000/api/v1/agents/reports")

asyncio.run(main())
