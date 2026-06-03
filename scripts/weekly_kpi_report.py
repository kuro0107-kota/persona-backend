"""
weekly_kpi_report.py — 週次KPIレポート自動生成スクリプト

毎週月曜 7:00 (JST) にcron実行する想定。
1. /api/v1/admin/kpi-summary からKPIデータを取得
2. Gemini Flash API でKPIを分析しレポートを生成
3. Slack Webhook で週次レポートを送信

crontab例:
  0 7 * * 1 cd /path/to/backend && /path/to/venv/bin/python scripts/weekly_kpi_report.py

環境変数(.env):
  GOOGLE_API_KEY  — Gemini API キー
  SLACK_WEBHOOK_URL — Slack Incoming Webhook URL
"""
from __future__ import annotations

import os
import sys
import json
import httpx
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# .envの読み込み（backendディレクトリ基準）
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ============================================================
# 設定
# ============================================================
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
KPI_ENDPOINT = f"{API_BASE_URL}/api/v1/admin/kpi-summary"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# Gemini Flash APIエンドポイント
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


# ============================================================
# 1. KPIデータ取得
# ============================================================
def fetch_kpi() -> dict:
    """KPIサマリーAPIからデータを取得する"""
    print(f"📊 KPIデータ取得中... ({KPI_ENDPOINT})")
    try:
        resp = httpx.get(KPI_ENDPOINT, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        print("✅ KPIデータ取得成功")
        return data
    except httpx.HTTPError as e:
        print(f"❌ KPIデータ取得失敗: {e}")
        sys.exit(1)


# ============================================================
# 2. Gemini Flash APIでレポート生成
# ============================================================
def generate_report(kpi: dict) -> str:
    """Gemini Flash APIを使ってKPI分析レポートを生成する"""
    if not GOOGLE_API_KEY:
        print("⚠️  GOOGLE_API_KEY未設定 — テンプレートレポートを使用します")
        return _fallback_report(kpi)

    prompt = f"""あなたはマッチングアプリ「Persona」の経営分析AIです。
以下のKPIデータを分析し、日本語で経営者向け週次レポートを作成してください。

## KPIデータ
```json
{json.dumps(kpi, ensure_ascii=False, indent=2)}
```

## レポート要件
1. **サマリー**: 今週のハイライトを3行で
2. **ユーザー成長**: 登録数・認証率の評価
3. **エンゲージメント**: シミュレーション利用・マッチ・メッセージの分析
4. **ヘルススコア**: DAU/MAU比率やチャットアクティブ率の評価
5. **改善提案**: 具体的なアクション3つ
6. **来週の注目指標**: 重点的に見るべきKPI

Slack投稿用にmrkdwn形式で出力してください。絵文字を適度に使い、読みやすくしてください。
レポートは800文字以内に収めてください。"""

    print("🤖 Gemini Flash APIでレポート生成中...")
    try:
        resp = httpx.post(
            f"{GEMINI_API_URL}?key={GOOGLE_API_KEY}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1024,
                },
            },
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()

        # Gemini APIレスポンスからテキスト抽出
        text = (
            result.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        if text:
            print("✅ レポート生成成功")
            return text
        else:
            print("⚠️  Geminiレスポンスが空 — テンプレートレポートを使用します")
            return _fallback_report(kpi)

    except Exception as e:
        print(f"⚠️  Gemini API エラー: {e} — テンプレートレポートを使用します")
        return _fallback_report(kpi)


def _fallback_report(kpi: dict) -> str:
    """Gemini APIが利用不可の場合のテンプレートレポート"""
    users = kpi.get("users", {})
    wl = kpi.get("waitlist", {})
    eng = kpi.get("engagement", {})
    health = kpi.get("health", {})
    details = health.get("details", {})

    return (
        f"📊 *Persona 週次KPIレポート*\n"
        f"_{kpi.get('timestamp', 'N/A')}_\n\n"
        f"*👥 ユーザー*\n"
        f"• 総ユーザー数: *{users.get('total', 0)}*人\n"
        f"• 認証済み: *{users.get('verified', 0)}*人（{users.get('verification_rate', 0)}%）\n\n"
        f"*📋 ウェイティングリスト*\n"
        f"• 総登録数: *{wl.get('total', 0)}*人\n"
        f"• 女性比率: *{wl.get('female_ratio', 0)}*%（女性: {wl.get('female', 0)}, 男性: {wl.get('male', 0)}）\n\n"
        f"*💡 エンゲージメント*\n"
        f"• シミュレーション: 累計 *{eng.get('simulations_total', 0)}*回（7日間: {eng.get('simulations_7d', 0)}回）\n"
        f"• 平均相性スコア: *{eng.get('avg_compatibility_score', 0)}*%\n"
        f"• 致命的欠陥率: *{eng.get('fatal_flaw_rate', 0)}*%\n"
        f"• マッチ数: *{eng.get('matches_total', 0)}*\n"
        f"• メッセージ数: *{eng.get('messages_total', 0)}*\n\n"
        f"*🏥 ヘルススコア*\n"
        f"• グレード: *{health.get('grade', 'N/A')}* ({health.get('score', 0)}点)\n"
        f"• DAU/MAU: {details.get('dau_mau_ratio', 0)} | "
        f"マッチ率: {details.get('match_rate', 0)}% | "
        f"チャット率: {details.get('chat_active_rate', 0)}%\n"
    )


# ============================================================
# 3. Slack送信
# ============================================================
def send_to_slack(report: str) -> bool:
    """Slack Webhookでレポートを送信する"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URL未設定 — レポートをコンソール出力します")
        print("=" * 60)
        print(report)
        print("=" * 60)
        return False

    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d")
    print(f"📤 Slackにレポート送信中...")

    try:
        resp = httpx.post(
            SLACK_WEBHOOK_URL,
            json={
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"📊 Persona 週次KPIレポート ({today})",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": report[:3000],  # Slack Block Kit制限
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "🤖 _Gemini Flash + Persona KPI API で自動生成_",
                            }
                        ],
                    },
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        print("✅ Slack送信成功")
        return True

    except Exception as e:
        print(f"❌ Slack送信失敗: {e}")
        print("レポート内容:")
        print(report)
        return False


# ============================================================
# メイン実行
# ============================================================
def main():
    """週次KPIレポートの生成・送信を実行する"""
    print("=" * 60)
    print("🚀 Persona 週次KPIレポート生成開始")
    print(f"   実行時刻: {datetime.now(timezone(timedelta(hours=9))).isoformat()}")
    print("=" * 60)

    # 1. KPIデータ取得
    kpi = fetch_kpi()

    # 2. Geminiでレポート生成
    report = generate_report(kpi)

    # 3. Slack送信
    success = send_to_slack(report)

    if success:
        print("\n✅ 週次KPIレポートの送信が完了しました")
    else:
        print("\n⚠️  レポート生成は完了しましたが、Slack送信に問題がありました")

    return 0


if __name__ == "__main__":
    sys.exit(main())
