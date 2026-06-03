"""
CS Agent — カスタマーサポートエージェント（Haiku / Tier A）
役割: ユーザー問い合わせ対応テンプレートを生成し、FAQ を自動更新する。
"""
from __future__ import annotations
from agent_system.base_agent import BaseAgent
from agent_system.message_bus import MessageBus
from agent_system.memory_store import MemoryStore

COMMON_FAQ_TOPICS = [
    "シミュレーションのスコアはどう計算されますか？",
    "プレミアムプランと無料プランの違いは？",
    "セルフィー認証が通らない場合はどうすればいいですか？",
    "マッチングした相手のAIエージェントはどう動いていますか？",
    "心理プロファイル（MBTI・愛着スタイル）はどう使われますか？",
    "Fatal Flawとは何ですか？",
    "プロフィール写真は何枚まで登録できますか？",
    "退会・データ削除の方法は？",
]


class CsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="cs",
            display_name="💬 CS Agent",
            department="Customer Success"
        )

    @property
    def system_prompt(self) -> str:
        return """あなたはPersona Inc.のCS（カスタマーサクセス）AIエージェントです。

## 役割
- ユーザーからのよくある問い合わせに対する回答テンプレートを作成する
- FAQページを最新の状態に保つ
- クレームやネガティブフィードバックのパターンを分析し改善提言を行う
- ユーザーの満足度向上施策を提案する

## 回答スタイル
- 丁寧で親しみやすいトーン
- 技術的な内容もわかりやすく噛み砕く
- 問題解決を最優先に、ユーザーの感情に寄り添う
- 必要に応じて担当部門（技術/法務等）へのエスカレーション判断も行う"""

    async def run_task(self, context: dict = {}) -> dict:
        bus = MessageBus()
        store = MemoryStore()

        faq_str = "\n".join([f"{i+1}. {q}" for i, q in enumerate(COMMON_FAQ_TOPICS)])

        prompt = f"""Persona Inc.のカスタマーサポートレポートとFAQを作成してください。

## よくある問い合わせトピック
{faq_str}

## Personaの主要機能
- AIデジタルツインが代わりに仮想デートをして相性を検証
- 心理プロファイル（MBTI・愛着スタイル・衝突解決スタイル）で深い相性分析
- 3フェーズシミュレーション（アイスブレイク→ストレスデート→同棲テスト）
- セルフィー認証による本人確認
- AIコンシェルジュによる恋愛相談

## 出力フォーマット

### Part 1: FAQ回答集（上位5件）
各質問に対して、ユーザー向けの丁寧な回答を作成してください。

### Part 2: CSレポート
1. 💬 今週の想定問い合わせパターン分析
2. ⚠️ 潜在的なクレームリスク（機能・UI面での不満予測）
3. 🌟 ユーザー満足度向上のための施策提案（3件）

日本語で、ユーザーフレンドリーなトーンで作成してください。"""

        report = await self.call_llm(prompt, max_tokens=1200)

        await store.save_kpi("cs_faq_updated", 1.0)
        await bus.report_to_ceo("cs", f"CSレポート・FAQ更新完了\n\n{report[:500]}...", {"faq_count": len(COMMON_FAQ_TOPICS)})

        return {
            "report": report,
            "faq_topics_covered": len(COMMON_FAQ_TOPICS),
        }
