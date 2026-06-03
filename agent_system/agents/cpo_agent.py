"""
CPO Agent — プロダクト責任者エージェント（Sonnet / Tier B）
役割: ユーザー行動・シミュレーション品質を分析し、プロダクト改善提案を生成する。
"""
from __future__ import annotations
import json
from agent_system.base_agent import BaseAgent
from agent_system.message_bus import MessageBus
from agent_system.memory_store import MemoryStore


class CpoAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="cpo",
            display_name="📊 CPO Agent",
            department="Product"
        )

    @property
    def system_prompt(self) -> str:
        return """あなたはPersona Inc.のCPO（最高プロダクト責任者）AIエージェントです。

## 役割
- シミュレーションのスコア分布・Fatal Flaw検知率などのプロダクトKPIを分析する
- ユーザー体験の課題を特定し、改善提案（機能追加・UI改善）をロードマップ形式で提示する
- 競合プロダクト（Tinder/Pairs/Hinge/with）との機能比較から差別化ポイントを強化する提案をする

## 提案スタイル
- 実装難易度（Easy/Medium/Hard）を必ず付ける
- 期待される効果（ユーザー満足度向上・収益増加・コスト削減）を定量的に示す
- 優先度（P0/P1/P2）で分類する"""

    async def run_task(self, context: dict = {}) -> dict:
        bus = MessageBus()
        store = MemoryStore()

        # KPIデータ取得
        sim_scores = await store.get_kpis(metric_name="simulation_score", limit=50)
        fatal_rates = await store.get_kpis(metric_name="fatal_flaw_rate", limit=50)
        qa_scores = await store.get_kpis(metric_name="qa_engine_score_stable_pair", limit=10)

        avg_score = round(sum(k["metric_value"] for k in sim_scores) / max(len(sim_scores), 1), 1)
        fatal_rate = round(sum(k["metric_value"] for k in fatal_rates) / max(len(fatal_rates), 1) * 100, 1)
        qa_avg = round(sum(k["metric_value"] for k in qa_scores) / max(len(qa_scores), 1), 1)
        sim_count = len(sim_scores)

        prompt = f"""Persona Inc.のプロダクト分析レポートと改善提案を作成してください。

## プロダクトKPI
- シミュレーション実行数: {sim_count}件
- 平均相性スコア: {avg_score}点/100点
- Fatal Flaw検知率: {fatal_rate}%
- QA基準スコア（安定型ペア）: {qa_avg}点

## Persona の現在の主要機能
1. AIデジタルツインによる恋愛相性シミュレーション（3フェーズ：アイスブレイク・ストレスデート・同棲テスト）
2. 心理プロファイル（MBTI・愛着スタイル・衝突スタイル）による相性スコアリング
3. セルフィー写真認証
4. AIコンシェルジュ（恋愛相談）
5. マッチング・チャット機能

## レポートフォーマット
1. 📊 プロダクトヘルスサマリー
2. 🔍 課題・ボトルネック分析
3. 🚀 改善提案ロードマップ（P0/P1/P2別、Easy/Medium/Hard付き）
4. 💡 差別化強化アイデア（競合との比較）

CPOとして戦略的・具体的に記述してください。"""

        report = await self.call_llm(prompt, max_tokens=1000)

        # KPI記録
        await store.save_kpi("product_sim_count", float(sim_count))
        await store.save_kpi("product_avg_score", avg_score)
        await store.save_kpi("product_fatal_rate", fatal_rate)

        # CEOに報告
        await bus.report_to_ceo("cpo", report, {
            "sim_count": sim_count,
            "avg_score": avg_score,
            "fatal_rate": fatal_rate,
        })

        return {
            "report": report,
            "sim_count": sim_count,
            "avg_score": avg_score,
            "fatal_rate": fatal_rate,
        }
