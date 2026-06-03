"""
CMO Agent — マーケティング責任者エージェント（Sonnet / Tier B）
役割: SNS投稿コンテンツを自動生成し、ユーザー獲得戦略を立案する。
"""
from __future__ import annotations
from agent_system.base_agent import BaseAgent
from agent_system.message_bus import MessageBus
from agent_system.memory_store import MemoryStore


class CmoAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="cmo",
            display_name="📣 CMO Agent",
            department="Marketing"
        )

    @property
    def system_prompt(self) -> str:
        return """あなたはPersona Inc.のCMO（最高マーケティング責任者）AIエージェントです。

## Personaのブランドポジション
「AIが本気で相性を調べる、次世代マッチングアプリ」
- ターゲット: 20〜35歳、真剣な出会いを求めるリテラシーの高いユーザー
- 差別化: AIデジタルツインが仮想デートして相性99%を見極める
- トーン: スマート・クール・少し辛口・知的ユーモア

## 役割
- X（Twitter）・Instagram・TikTok向けのSNS投稿コンテンツを毎週生成する
- ユーザー獲得施策（キャンペーン・インフルエンサー戦略）を提案する
- A/Bテスト案を設計する

## コンテンツ作成ルール
- X投稿: 140字以内、絵文字あり、ハッシュタグ2〜3個
- Instagram: キャプション200字以内 + ビジュアル説明
- バズる可能性の高いフック（最初の一文）を意識する"""

    async def run_task(self, context: dict = {}) -> dict:
        bus = MessageBus()
        store = MemoryStore()

        # 今週のコンテンツテーマ（KPIから引っ張る）
        sim_scores = await store.get_kpis(metric_name="product_avg_score", limit=3)
        avg_score = sim_scores[0]["metric_value"] if sim_scores else 72.0

        prompt = f"""Persona Inc.の今週のSNSコンテンツを生成してください。

## 今週のデータ
- 今週のシミュレーション平均相性スコア: {avg_score:.0f}点

## 生成するコンテンツ

### 1. X（Twitter）投稿 × 3本
異なるフックで3本作成。それぞれ:
- バズ狙いの刺さる一文から始める
- Personaの「AIが仮想デートして相性を見極める」機能を自然に訴求
- ハッシュタグ: #Persona #AIマッチング #恋愛工学 の中から2〜3個

### 2. Instagram キャプション × 1本
- 「AIと恋愛の融合」というテーマで知的に訴求
- 行動喚起（「プロフィールにあなたのデジタルツインを設定してみて」など）

### 3. 今週の獲得施策アイデア × 1件
- インフルエンサー/SNS広告/プレスリリースなど、具体的な施策案
- 予算感と期待効果を添える

日本語で、ブランドトーンを守って作成してください。"""

        content = await self.call_llm(prompt, max_tokens=1200)

        # KPI記録
        await store.save_kpi("cmo_content_generated", 1.0)

        # CEOに報告
        await bus.report_to_ceo("cmo", content, {"avg_sim_score": avg_score})

        return {"content": content, "avg_sim_score": avg_score}
