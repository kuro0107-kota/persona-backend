"""
CTO Agent — 技術責任者エージェント（Sonnet / Tier B）
役割: コード品質・セキュリティ・パフォーマンスを監視し技術提言をする。
"""
from __future__ import annotations
import os
from agent_system.base_agent import BaseAgent
from agent_system.message_bus import MessageBus
from agent_system.memory_store import MemoryStore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

TECH_CHECKLIST = {
    "セキュリティ": [
        "APIキーが.envに格納され、コードにハードコードされていないか",
        "CORSがホワイトリスト制限されているか（ワイルドカード禁止）",
        "SQLインジェクション対策（SQLAlchemy ORM使用）",
        "入力バリデーション（Pydanticによるスキーマ検証）",
        "セルフィー認証画像のサイズ制限（5MB上限）",
    ],
    "パフォーマンス": [
        "非同期処理（asyncio）の適切な使用",
        "データベースN+1クエリの回避",
        "並列シミュレーション実行（asyncio.gather）",
        "ベクトル検索のキャッシュ戦略",
    ],
    "コード品質": [
        "型ヒントの使用（Python typing）",
        "エラーハンドリングの網羅性",
        "モジュール分離（engine/main/models/agent_system）",
        "テストカバレッジ",
    ],
    "インフラ": [
        "Docker Composeによるコンテナ化",
        "環境変数管理（.env/.env.example）",
        "ログ出力の適切性",
        "ヘルスチェックエンドポイントの存在",
    ],
}


class CtoAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="cto",
            display_name="🛡️ CTO Agent",
            department="Technology"
        )

    @property
    def system_prompt(self) -> str:
        return """あなたはPersona Inc.のCTO（最高技術責任者）AIエージェントです。

## 役割
- バックエンド・フロントエンドのコード品質を評価する
- セキュリティリスクを検知して即時対応を提言する
- パフォーマンスボトルネックを特定し最適化案を提示する
- 技術的負債を可視化しリファクタリング優先度を示す

## 評価基準
- セキュリティ: OWASP Top 10への対応状況
- パフォーマンス: レスポンスタイム・スループット
- 可用性: エラー率・リトライ機構・グレースフルデグラデーション
- 保守性: コードの可読性・テスト容易性・モジュール性

## アウトプット形式
- リスクスコア（1〜10）付きの技術評価
- 即時対応事項（Critical）と改善推奨事項（Recommended）を分けて記述"""

    async def run_task(self, context: dict = {}) -> dict:
        bus = MessageBus()
        store = MemoryStore()

        checklist_str = ""
        for category, items in TECH_CHECKLIST.items():
            checklist_str += f"\n### {category}\n"
            for item in items:
                checklist_str += f"- {item}\n"

        prompt = f"""Persona Inc.（FastAPI + Next.js + Claude API + SQLite + Qdrant）の技術評価レポートを作成してください。

## アーキテクチャ概要
- バックエンド: Python FastAPI + SQLAlchemy(非同期) + aiosqlite
- フロントエンド: Next.js 16 + TypeScript
- AI: Anthropic Claude API（Haiku/Sonnet/Opus 3層制）
- Vector DB: Qdrant（ユーザープロフィールの意味検索）
- 認証: セルフィー写真 × プロフィール画像のAI比較認証
- エージェント: APSchedulerによる自律稼働 + SQLiteメモリストア

## 技術チェックリスト
{checklist_str}

## 評価フォーマット
1. 🔒 セキュリティ評価（スコア/10・Critical事項）
2. ⚡ パフォーマンス評価（ボトルネック指摘）
3. 🏗️ アーキテクチャ評価（強み・改善点）
4. 🚨 即時対応が必要な技術的問題（あれば）
5. 📋 来週の技術的アクションアイテム（3件）

CTOとして具体的・技術的に記述してください（500字程度）。"""

        report = await self.call_llm(prompt, max_tokens=1000)

        # リスクスコア推定
        risk_score = 3  # デフォルト低リスク
        if "Critical" in report or "即時" in report:
            risk_score = 6

        await store.save_kpi("tech_risk_score", float(risk_score))
        await bus.report_to_ceo("cto", report, {"tech_risk_score": risk_score})

        if risk_score >= 7:
            await bus.request_approval(
                "cto",
                "技術的リスク対応（即時対応が必要な事項あり）",
                {"risk_score": risk_score}
            )

        return {"report": report, "tech_risk_score": risk_score}
