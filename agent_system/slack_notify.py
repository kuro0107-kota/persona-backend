"""
Slack通知モジュール — 承認要求・アラートをSlackへ自動送信
.envのSLACK_WEBHOOK_URLが空の場合はログのみ（エラーにならない）
"""
from __future__ import annotations
import os
import json
import logging
import aiohttp
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

PRIORITY_EMOJI = {1: "🟢", 2: "🔵", 3: "🟡", 4: "🟠", 5: "🔴"}
MSG_TYPE_LABEL = {
    "report":           "📊 レポート",
    "alert":            "🚨 アラート",
    "approval_request": "🔐 承認要求",
    "weekly_directive": "📋 週次指示",
}


async def send_slack(webhook_url: str, blocks: list, text: str = "") -> bool:
    """Slack Webhook にメッセージを送信する"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"text": text, "blocks": blocks}
            async with session.post(
                webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    return True
                else:
                    body = await resp.text()
                    logger.warning(f"[Slack] HTTP {resp.status}: {body}")
                    return False
    except Exception as e:
        logger.error(f"[Slack] Send failed: {e}")
        return False


async def notify_approval_request(from_agent: str, action: str, detail: dict, message_id: int):
    """オーナー承認が必要な事項をSlackで通知"""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        logger.info(f"[Slack] SLACK_WEBHOOK_URL未設定のためスキップ: {action}")
        return

    dashboard_url = "http://localhost:3000/admin"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🔐 オーナー承認が必要な事項があります"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*送信元:*\n{from_agent.upper()} Agent"},
                {"type": "mrkdwn", "text": f"*件名:*\n{action}"},
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*詳細:*\n{json.dumps(detail, ensure_ascii=False)[:200]}"}
        },
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ ダッシュボードで承認する"},
                    "url": f"{dashboard_url}",
                    "style": "primary",
                }
            ]
        }
    ]
    await send_slack(webhook_url, blocks, text=f"[Persona] 承認要求: {action}")
    logger.info(f"[Slack] 承認通知送信: {action}")


async def notify_alert(from_agent: str, title: str, body: str, priority: int = 4):
    """重要アラートをSlackで通知"""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        logger.info(f"[Slack] SLACK_WEBHOOK_URL未設定のためスキップ: {title}")
        return

    emoji = PRIORITY_EMOJI.get(priority, "🔴")
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} アラート: {title}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*送信元:*\n{from_agent.upper()} Agent"},
                {"type": "mrkdwn", "text": f"*優先度:*\nP{priority} {emoji}"},
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*内容:*\n{body[:400]}"}
        },
    ]
    await send_slack(webhook_url, blocks, text=f"[Persona] 🚨 {title}")
    logger.info(f"[Slack] アラート通知送信: {title}")


async def notify_weekly_report(week_label: str, report_summary: str):
    """CEO週次報告書をSlackで通知"""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        return

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📊 Persona Inc. 週次経営報告書 {week_label}"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": report_summary[:600]}
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "📋 <http://localhost:3000/admin|ダッシュボードで全文を確認する>"}
        }
    ]
    await send_slack(webhook_url, blocks, text=f"[Persona] 週次報告書 {week_label}")
    logger.info(f"[Slack] 週次報告書通知送信: {week_label}")


async def notify_agent_complete(agent_id: str, status: str, summary: str = ""):
    """エージェント実行完了（エラー時のみ通知）"""
    if status == "success":
        return  # 正常完了はSlack通知しない（ノイズ軽減）
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        return
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"❌ *{agent_id.upper()} Agent* が失敗しました\n{summary[:200]}"}
        }
    ]
    await send_slack(webhook_url, blocks, text=f"[Persona] {agent_id} 失敗")
