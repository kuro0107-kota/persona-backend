"""
Research Agent — 競合・市場調査エージェント（Sonnet / Tier B）
役割: 競合アプリの動向を監視し、差別化戦略をCEOに提言する。
"""
from __future__ import annotations
from agent_system.base_agent import BaseAgent
from agent_system.message_bus import MessageBus
from agent_system.memory_store import MemoryStore


COMPETITORS = [
    {"name": "Tinder",    "model": "写真スワイプ型・世界最大規模・ゲーミフィケーション"},
    {"name": "Pairs",     "model": "日本最大・コミュニティ型・真剣婚活"},
    {"name": "Hinge",     "model": "プロフィール深掘り型・'designed to be deleted'"},
    {"name": "with",      "model": "趣味・価値観マッチング・デート提案型"},
    {"name": "タップル",   "model": "趣味マッチング・10〜20代向け"},
    {"name": "ゼクシィ縁結び", "model": "婚活特化・高課金モデル"},
]

PERSONA_STRENGTHS = [
    "AIデジタルツインによる事前シミュレーション（業界初）",
    "3フェーズのストレスイベント注入で深い相性検証",
    "心理プロファイル（MBTI・愛着スタイル）ベースのスコアリング",
    "Fatal Flaw（絶対NG条件）による即時排除機能",
    "AIコンシェルジュによるパーソナライズ恋愛相談",
]


class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="research",
            display_name="🔬 Research Agent",
            department="Competitive Intelligence"
        )

    @property
    def system_prompt(self) -> str:
        return """あなたはPersona Inc.の競合・市場調査AIエージェントです。

## 役割
- 競合マッチングアプリの戦略・機能・ユーザー評価を分析する
- Personaの差別化優位性を整理し、CEOに戦略提言を行う
- 業界トレンド（AI×マッチング・アプリ内課金モデル等）を把握する

## 分析の視点
- 競合の弱点＝Personaの機会として捉える
- 日本市場特有のニーズ（真剣婚活・安全性・個人情報保護）を重視
- 技術的差別化（AI）を競合優位性として最大活用する提言をする

## アウトプット形式
- 競合マップ（ポジショニング分析）
- Personaの強み・弱み・機会・脅威（SWOT）
- 具体的な差別化アクション提言"""

    async def run_task(self, context: dict = {}) -> dict:
        bus = MessageBus()
        store = MemoryStore()

        competitors_str = "\n".join([
            f"- **{c['name']}**: {c['model']}" for c in COMPETITORS
        ])
        strengths_str = "\n".join([f"- {s}" for s in PERSONA_STRENGTHS])

        prompt = f"""Personaの競合分析・市場調査レポートを作成してください。

## 主要競合
{competitors_str}

## Personaの主要強み
{strengths_str}

## レポートフォーマット
1. 🗺️ 競合ポジショニング分析（カジュアル〜真剣婚活 / AI活用度の2軸で整理）
2. ⚔️ 競合の弱点とPersonaの機会
3. 📊 SWOT分析（簡潔に箇条書き）
4. 🎯 今週の差別化強化アクション提言（3件、具体的に）
5. 📈 注目すべき業界トレンド（AI×マッチング領域）

日本語で、戦略的かつ具体的に記述してください（500字程度）。"""

        report = await self.call_llm(prompt, max_tokens=1000)

        await store.save_kpi("research_report_generated", 1.0)
        await bus.report_to_ceo("research", report, {"competitors_analyzed": len(COMPETITORS)})

        return {
            "report": report,
            "competitors_analyzed": len(COMPETITORS),
            "persona_strengths": len(PERSONA_STRENGTHS),
        }
