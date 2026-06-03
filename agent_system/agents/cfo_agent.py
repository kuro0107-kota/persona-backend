"""
CFO Agent — KPI・財務分析エージェント（Sonnet / Tier B）
役割: KPIを集計・分析しCEOに週次財務レポートを送る。コスト最適化提案も行う。
"""
from __future__ import annotations
import json
from agent_system.base_agent import BaseAgent
from agent_system.message_bus import MessageBus
from agent_system.memory_store import MemoryStore


class CfoAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="cfo",
            display_name="📈 CFO Agent",
            department="Finance & Strategy"
        )

    @property
    def system_prompt(self) -> str:
        return """あなたはPersona Inc.のCFO（最高財務責任者）AIエージェントです。

## 役割
- KPIデータを収集・分析し、経営判断に必要な財務インサイトを提供する
- APIコストを監視し、ROIを最大化する提案をする
- シミュレーション実行数・スコア分布・ユーザー登録数などの指標を週次でレポートする
- 月間固定費と変動費のバランスを保ち、損益分岐点を常に意識する

## レポートトーン
- 数字に基づいた根拠ある分析
- リスクと機会を両面から提示
- CEOへの提言は具体的・実行可能なアクションで記述"""

    async def run_task(self, context: dict = {}) -> dict:
        bus = MessageBus()
        store = MemoryStore()

        # KPIデータ収集
        kpis = await store.get_kpis(limit=100)
        logs = await store.get_logs(limit=50)

        # KPIをメトリクス名でグループ化
        kpi_groups: dict = {}
        for k in kpis:
            name = k.get("metric_name", "")
            val = k.get("metric_value", 0)
            if name not in kpi_groups:
                kpi_groups[name] = []
            kpi_groups[name].append(val)

        # 統計サマリー
        kpi_summary = {}
        for name, vals in kpi_groups.items():
            kpi_summary[name] = {
                "count": len(vals),
                "avg": round(sum(vals) / len(vals), 2),
                "min": round(min(vals), 2),
                "max": round(max(vals), 2),
                "latest": round(vals[0], 2),
            }

        # エージェント実行コスト概算
        model_counts = {}
        for log in logs:
            m = log.get("model_used", "unknown")
            model_counts[m] = model_counts.get(m, 0) + 1

        total_runs = len(logs)

        prompt = f"""Persona Inc.の財務・KPIレポートを作成してください。

## KPIサマリー
{json.dumps(kpi_summary, ensure_ascii=False, indent=2)}

## エージェント実行統計
- 総実行回数: {total_runs}
- モデル別実行数: {json.dumps(model_counts, ensure_ascii=False)}

## レポートフォーマット
1. 📊 KPIハイライト（重要指標3つ）
2. 💰 コスト効率分析
3. 📈 トレンド分析（改善/悪化している指標）
4. 🎯 CFOからの提言（CEOへのアクション推奨）

日本語で簡潔に（400字以内）まとめてください。"""

        report = await self.call_llm(prompt, max_tokens=800)

        # KPI記録
        await store.save_kpi("kpi_metrics_count", float(len(kpi_groups)))
        await store.save_kpi("total_agent_runs", float(total_runs))

        # CEOに報告
        await bus.report_to_ceo("cfo", report, {
            "kpi_summary": kpi_summary,
            "total_runs": total_runs,
            "model_counts": model_counts,
        })

        return {
            "report": report,
            "kpi_metrics": len(kpi_groups),
            "total_runs": total_runs,
            "kpi_summary": kpi_summary,
        }
