"""
cost_monitor.py — APIコスト監視スクリプト（AUTO-05）
cron: 0 9 * * * python /path/to/cost_monitor.py

毎日9時に実行。月額コストが上限の80%に達したらSlackに通知する。
あなたが承認するだけで、投稿頻度の調整は自動で行う。
"""

import asyncio
import aiohttp
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
FAL_KEY = os.environ.get("FAL_KEY", "")

# フェーズ別コスト上限（円）
MONTHLY_COST_LIMITS = {
    "phase1": 5_000,     # n8nのみ: ¥3,000 + バッファ¥2,000
    "phase2": 30_000,    # n8n + fal.ai: ¥11,400 + バッファ
    "phase3": 150_000,   # フルスタック
    "warning_threshold": 0.8,  # 80%でアラート
}


def detect_current_phase() -> str:
    """現在のフェーズを自動判定（FAL_KEY有無で判定）"""
    if os.environ.get("HEYGEN_API_KEY"):
        return "phase3"
    elif FAL_KEY:
        return "phase2"
    return "phase1"


async def check_fal_usage() -> dict:
    """fal.aiの今月の使用量を確認"""
    if not FAL_KEY:
        return {"total_cost_jpy": 0, "total_cost_usd": 0, "details": {}}

    headers = {"Authorization": f"Key {FAL_KEY}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://fal.run/v1/billing/usage",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return {"total_cost_jpy": 0, "total_cost_usd": 0, "details": {}}

                data = await resp.json()
                usd_cost = data.get("total_cost_usd", 0)
                jpy_cost = int(usd_cost * 150)  # ¥150/USD

                return {
                    "total_cost_jpy": jpy_cost,
                    "total_cost_usd": usd_cost,
                    "details": data.get("model_breakdown", {}),
                }
    except Exception:
        return {"total_cost_jpy": 0, "total_cost_usd": 0, "details": {}}


async def send_cost_alert(usage: dict, phase: str, limit: int) -> None:
    """コスト状況をSlackに報告"""
    if not SLACK_WEBHOOK_URL:
        return

    current = usage["total_cost_jpy"]
    # n8nコストを加算
    n8n_cost = 3_000 if phase == "phase1" else (8_000 if phase == "phase3" else 3_000)
    total_current = current + n8n_cost

    percentage = (total_current / limit) * 100

    if percentage >= 80:
        emoji = "🚨"
        urgency = "緊急"
    elif percentage >= 60:
        emoji = "⚠️"
        urgency = "注意"
    else:
        emoji = "✅"
        urgency = "正常"

    message = (
        f"{emoji} *月額APIコスト状況（{urgency}）* — {datetime.now().strftime('%Y/%m/%d')}\n\n"
        f"今月の使用額（推定）: ¥{total_current:,}\n"
        f"  └ n8n Cloud: ¥{n8n_cost:,}\n"
        f"  └ fal.ai: ¥{current:,}\n"
        f"月額上限: ¥{limit:,}（{phase}）\n"
        f"使用率: {percentage:.1f}%\n"
    )

    if percentage >= 80:
        message += (
            f"\n🔴 *上限の80%に達しました*\n"
            f"以下のいずれかを承認してください:\n"
            f"  1. 上限を¥{int(limit*1.5):,}に引き上げる\n"
            f"  2. 投稿頻度を1日1本に削減\n"
            f"  3. より安価なFLUX Schnellに切り替え"
        )
    elif percentage < 40:
        message += f"\n💡 予算に余裕があります。投稿頻度を増やすことも検討できます。"

    async with aiohttp.ClientSession() as session:
        await session.post(SLACK_WEBHOOK_URL, json={"text": message})
    print(f"📊 コストレポートをSlackに送信: {percentage:.1f}%使用")


async def main():
    phase = detect_current_phase()
    usage = await check_fal_usage()
    limit = MONTHLY_COST_LIMITS[phase]
    await send_cost_alert(usage, phase, limit)
    print(f"✅ コスト監視完了（{phase}: ¥{usage['total_cost_jpy']:,}）")


if __name__ == "__main__":
    asyncio.run(main())
