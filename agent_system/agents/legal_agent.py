"""
Legal Agent — 法務・特許エージェント（Opus / Tier C）
役割: 利用規約・プライバシーポリシーを監査し、法的リスクを評価する。
     AIデジタルツインの特許候補技術をリストアップし、競合特許を監視する。
"""
from __future__ import annotations
from agent_system.base_agent import BaseAgent
from agent_system.message_bus import MessageBus
from agent_system.memory_store import MemoryStore


# Personaの主要法的リスク領域
LEGAL_CHECKLIST = {
    "個人情報保護法": [
        "プロフィール写真・生体認証データ（セルフィー）の取り扱いポリシーが明確か",
        "第三者（Claude API = Anthropic社）へのデータ送信に関する同意取得",
        "データ削除リクエストへの対応手順",
        "プライバシーポリシーの改正個人情報保護法（2022年改正）への適合",
    ],
    "出会い系サイト規制法": [
        "18歳未満利用禁止の表示と年齢確認措置",
        "都道府県公安委員会への届出義務の確認",
        "有害情報の削除体制の整備",
    ],
    "特定商取引法": [
        "課金プランの料金・解約方法の明示",
        "自動更新サブスクリプションの同意フロー",
        "返金ポリシーの明記",
    ],
    "AIデジタルツイン固有リスク": [
        "AIがユーザーを「代理」する旨の開示",
        "AI生成コンテンツへの責任所在の明確化",
        "感情操作・依存誘発に関する倫理的配慮",
    ],
}

PATENT_CANDIDATES = [
    {
        "title": "AIデジタルツインによる恋愛相性シミュレーションシステム",
        "claim": "ユーザーのMBTI・愛着スタイル・心理プロファイルに基づくデジタルツインエージェントを生成し、複数フェーズのストレスイベントを注入した仮想会話シミュレーションにより相性スコアを算出する方法",
        "novelty": "ストレスイベント注入（オーケストレーター）との組み合わせが新規性の核心",
    },
    {
        "title": "会話型AIエージェントによるNGトリガー即時検知システム",
        "claim": "ユーザーが事前設定した絶対的NG条件をベクトル類似度で照合し、シミュレーション中に即時関係破綻を判定する方法",
        "novelty": "ベクトル類似度0.85閾値によるリアルタイム判定が技術的特徴",
    },
]


class LegalAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="legal",
            display_name="⚖️ Legal Agent",
            department="Legal & Patent"
        )

    @property
    def system_prompt(self) -> str:
        return """あなたはPersona Inc.の法務・特許担当AIエージェントです。

## 役割
1. **法的コンプライアンス監査**: 日本の個人情報保護法・出会い系サイト規制法・特定商取引法への適合性をチェックする
2. **特許戦略**: Personaの技術的差別化ポイントを特許候補としてリストアップし、出願を推薦する
3. **リスクスコアリング**: 新機能のリリース前に法的リスクを1〜10でスコアリングする
4. **競合監視**: 競合他社の特許・利用規約変更が自社リスクになるか評価する

## 重要方針
- 法的問題は「グレーゾーン」を明確に示す
- 即時対応が必要な事項はリスクスコア8以上とし、CEOへの承認要求を送る
- 特許出願は費用（1件30〜50万円）と費用対効果を必ず示す
- 法律の解釈は日本法を前提とし、不確かな点は「専門家への確認推奨」と明記する"""

    async def run_task(self, context: dict = {}) -> dict:
        bus = MessageBus()
        store = MemoryStore()

        # 法的チェックリストの評価
        checklist_prompt = f"""Persona（AIマッチングアプリ）の法的コンプライアンス評価を行ってください。

## チェック項目
{self._format_checklist()}

## アプリの特徴
- AIデジタルツインがユーザーを代理して仮想デートシミュレーションを実施
- ユーザーのMBTI・心理プロファイル・セルフィー写真を収集
- 課金プラン（プレミアム機能）あり
- Anthropic社のClaude APIにユーザーデータを送信して処理

## 評価フォーマット
各カテゴリについて:
- 現状のリスクレベル（高/中/低）
- 具体的に確認・対応すべき事項
- 緊急度（即時/1ヶ月以内/3ヶ月以内）

最後に総合リスクスコア（1〜10）を示してください。"""

        legal_report = await self.call_llm(checklist_prompt, max_tokens=1200)

        # 特許候補の評価
        patent_prompt = f"""以下のPersonaの技術について、日本特許庁への出願可能性を評価してください。

## 特許候補技術
{self._format_patent_candidates()}

## 評価観点
1. 新規性（既存特許と被る可能性）
2. 進歩性（当業者には自明でないか）
3. 産業上の利用可能性
4. 推奨出願戦略（国内のみ/PCT国際出願）
5. 推定費用と費用対効果

簡潔に評価してください。"""

        patent_report = await self.call_llm(patent_prompt, max_tokens=800)

        # リスクスコア抽出（簡易判定）
        risk_score = 5  # デフォルト中リスク
        if "高" in legal_report and "即時" in legal_report:
            risk_score = 8

        # KPIとして記録
        await store.save_kpi("legal_risk_score", float(risk_score))

        # CEOに報告
        full_report = f"## ⚖️ 法務月次レポート\n\n### コンプライアンス評価\n{legal_report}\n\n### 特許戦略評価\n{patent_report}"
        await bus.report_to_ceo("legal", full_report, {"risk_score": risk_score})

        # リスクスコアが高い場合はオーナーへ承認要求
        if risk_score >= 8:
            await bus.request_approval(
                "legal",
                "法的リスク対応（即時対応が必要な事項あり）",
                {"risk_score": risk_score, "summary": "個人情報保護法または出会い系サイト規制法への対応が緊急です。"}
            )

        return {
            "legal_report": legal_report,
            "patent_report": patent_report,
            "risk_score": risk_score,
            "patent_candidates": len(PATENT_CANDIDATES),
            "checklist_categories": len(LEGAL_CHECKLIST),
        }

    def _format_checklist(self) -> str:
        lines = []
        for category, items in LEGAL_CHECKLIST.items():
            lines.append(f"### {category}")
            for item in items:
                lines.append(f"- {item}")
        return "\n".join(lines)

    def _format_patent_candidates(self) -> str:
        lines = []
        for i, p in enumerate(PATENT_CANDIDATES, 1):
            lines.append(f"**候補{i}: {p['title']}**")
            lines.append(f"- 請求の範囲: {p['claim']}")
            lines.append(f"- 新規性のポイント: {p['novelty']}")
            lines.append("")
        return "\n".join(lines)
