"""
Accounting Agent — 経理エージェント（Haiku / Tier A）
役割: APIコスト・サーバー費用を集計し、月次損益レポートを生成する。
     損益分岐点のシミュレーションもCFOに提供する。
"""
from __future__ import annotations
import json
import aiosqlite
import os
from datetime import datetime, timezone
from agent_system.base_agent import BaseAgent
from agent_system.message_bus import MessageBus
from agent_system.memory_store import MemoryStore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AGENT_DB_PATH = os.path.join(BASE_DIR, "agent_memory.db")

# Claudeモデル単価（$/1M tokens、2025年時点の概算）
MODEL_PRICING = {
    "claude-haiku-4-5":   {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-6":  {"input": 3.00,  "output": 15.00},
    "claude-opus-4-5":    {"input": 15.00, "output": 75.00},
}

# 月間固定費（概算）
MONTHLY_FIXED_COSTS = {
    "server_render":   7.0,   # Render.com Starter
    "db_supabase":     0.0,   # Free tier
    "qdrant_cloud":    0.0,   # Free tier
    "domain":          1.5,   # ドメイン代（月割）
}


class AccountingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="accounting",
            display_name="💰 Accounting Agent",
            department="Finance & Accounting"
        )

    @property
    def system_prompt(self) -> str:
        return """あなたはPersona Inc.の経理AIエージェントです。

## 役割
- Claude API利用コストを月次で集計する
- 固定費・変動費を分析して損益レポートを生成する
- 損益分岐点（何ユーザーが課金すれば黒字になるか）を試算する
- 異常なコスト増加を検知してCEOに警告する

## 報告書トーン
- 数字は具体的に（¥単位、$単位を混在させない）
- グラフは使えないので、テキストで傾向を表現する（例: ↑20%増）
- 結論を最初に書き、詳細は後に記述する"""

    async def _count_agent_runs(self) -> dict:
        """エージェントログからモデル別実行回数を集計"""
        counts = {}
        try:
            async with aiosqlite.connect(AGENT_DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT model_used, COUNT(*) as cnt FROM agent_logs GROUP BY model_used"
                )
                rows = await cursor.fetchall()
                for row in rows:
                    counts[row["model_used"]] = row["cnt"]
        except Exception:
            pass
        return counts

    async def _get_total_log_count(self) -> int:
        try:
            async with aiosqlite.connect(AGENT_DB_PATH) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM agent_logs")
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception:
            return 0

    async def run_task(self, context: dict = {}) -> dict:
        bus = MessageBus()
        store = MemoryStore()

        now = datetime.now(timezone.utc)
        month_label = f"{now.year}-{now.month:02d}"

        # モデル別実行回数を取得
        model_runs = await self._count_agent_runs()
        total_runs = await self._get_total_log_count()

        # API費用推定（1回あたり平均200 input + 400 output tokens と仮定）
        avg_input_tokens  = 200
        avg_output_tokens = 400
        estimated_api_cost_usd = 0.0

        cost_breakdown = []
        for model, count in model_runs.items():
            pricing = MODEL_PRICING.get(model, {"input": 3.0, "output": 15.0})
            cost = (
                (avg_input_tokens  * pricing["input"]  / 1_000_000) +
                (avg_output_tokens * pricing["output"] / 1_000_000)
            ) * count
            estimated_api_cost_usd += cost
            cost_breakdown.append({
                "model": model,
                "runs": count,
                "estimated_cost_usd": round(cost, 4)
            })

        # 固定費合計
        total_fixed_usd = sum(MONTHLY_FIXED_COSTS.values())
        total_cost_usd = estimated_api_cost_usd + total_fixed_usd
        total_cost_jpy = total_cost_usd * 150  # 概算レート

        # KPIとして記録
        await store.save_kpi("monthly_api_cost_usd", round(estimated_api_cost_usd, 4))
        await store.save_kpi("monthly_total_cost_usd", round(total_cost_usd, 4))
        await store.save_kpi("agent_total_runs", float(total_runs))

        # 損益分岐点試算（月額980円課金と仮定）
        price_per_user_jpy = 980
        breakeven_users = int(total_cost_jpy / price_per_user_jpy) + 1

        # AI分析レポート生成
        prompt = f"""以下のPersona Inc.の{month_label}月次経理データをもとに報告書を作成してください。

## データ
- エージェント総実行回数: {total_runs}回
- モデル別コスト内訳: {json.dumps(cost_breakdown, ensure_ascii=False, indent=2)}
- 推定API費用: ${estimated_api_cost_usd:.4f}
- 固定費合計: ${total_fixed_usd:.2f}（サーバー代等）
- 月間総コスト: ${total_cost_usd:.4f} ≈ ¥{total_cost_jpy:.0f}
- 損益分岐点: 課金ユーザー {breakeven_users}名（月額¥{price_per_user_jpy}仮定）

## 報告書フォーマット
1. 💴 今月のコストサマリー（1行）
2. 📊 モデル別コスト分析
3. 🎯 損益分岐点試算
4. ⚠️ 注意事項または改善提案
簡潔に3〜4段落でまとめてください。"""

        report = await self.call_llm(prompt, max_tokens=600)

        # CEOにレポート送信
        await bus.report_to_ceo(
            "accounting",
            report,
            {
                "month": month_label,
                "total_cost_usd": round(total_cost_usd, 4),
                "total_cost_jpy": round(total_cost_jpy),
                "breakeven_users": breakeven_users,
                "agent_runs": total_runs,
            }
        )

        # コストが日次上限（$5）を超えそうな場合はアラート
        daily_estimate = total_cost_usd / 30
        if daily_estimate > 5.0:
            await bus.alert_owner(
                "accounting",
                "⚠️ APIコスト警告",
                f"日次推定コストが$5を超えています（現在: ${daily_estimate:.2f}/日）。エージェント稼働を見直してください。"
            )

        return {
            "month": month_label,
            "total_api_cost_usd": round(estimated_api_cost_usd, 4),
            "total_fixed_usd": total_fixed_usd,
            "total_cost_usd": round(total_cost_usd, 4),
            "total_cost_jpy": round(total_cost_jpy),
            "breakeven_users": breakeven_users,
            "agent_runs": total_runs,
            "cost_breakdown": cost_breakdown,
            "report": report,
        }
