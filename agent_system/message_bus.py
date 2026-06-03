"""
MessageBus — エージェント間メッセージング + Slack通知連携
エージェントが互いに報告・依頼・アラートを送受信する
承認要求・アラートは自動でSlackにも通知される
"""
from __future__ import annotations
from typing import Any
from agent_system.memory_store import MemoryStore


class MessageBus:
    """エージェント間メッセージバス"""

    def __init__(self):
        self.store = MemoryStore()

    async def send(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: dict,
        priority: int = 1,
        requires_approval: bool = False,
    ):
        """メッセージを送信する"""
        msg = {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "content": content,
            "priority": priority,
            "requires_approval": requires_approval,
        }
        await self.store.send_message(msg)

    async def broadcast(self, from_agent: str, message_type: str, content: dict, priority: int = 1):
        """全エージェントにブロードキャスト"""
        await self.send(from_agent, "all", message_type, content, priority)

    async def alert_owner(self, from_agent: str, title: str, body: str):
        """緊急アラートをオーナーに送信（priority=5）→ Slack通知"""
        await self.send(
            from_agent=from_agent,
            to_agent="owner",
            message_type="alert",
            content={"title": title, "body": body},
            priority=5,
            requires_approval=True,
        )
        # Slack通知（非同期・失敗してもメインフローに影響しない）
        try:
            from agent_system.slack_notify import notify_alert
            await notify_alert(from_agent, title, body, priority=5)
        except Exception:
            pass

    async def report_to_ceo(self, from_agent: str, report: str, data: dict = {}):
        """CEOへのレポート送信"""
        await self.send(
            from_agent=from_agent,
            to_agent="ceo",
            message_type="report",
            content={"report": report, "data": data},
            priority=2,
        )

    async def request_approval(self, from_agent: str, action: str, detail: dict):
        """承認要求（オーナーへ）→ Slack通知"""
        await self.send(
            from_agent=from_agent,
            to_agent="owner",
            message_type="approval_request",
            content={"action": action, "detail": detail},
            priority=4,
            requires_approval=True,
        )
        # Slack通知
        try:
            from agent_system.slack_notify import notify_approval_request
            # message_idは最後に挿入されたIDを取得
            msgs = await self.store.get_messages(to_agent="owner", limit=1)
            msg_id = msgs[0]["id"] if msgs else 0
            await notify_approval_request(from_agent, action, detail, msg_id)
        except Exception:
            pass

    async def notify_weekly_report(self, week_label: str, report_text: str):
        """CEO週次報告書をSlackで通知"""
        try:
            from agent_system.slack_notify import notify_weekly_report
            summary = report_text[:500] + "..." if len(report_text) > 500 else report_text
            await notify_weekly_report(week_label, summary)
        except Exception:
            pass

    async def get_inbox(self, agent_id: str, limit: int = 20) -> list:
        """エージェントの受信ボックスを取得"""
        return await self.store.get_messages(to_agent=agent_id, limit=limit)

    async def get_all_messages(self, limit: int = 100) -> list:
        """全メッセージ取得（ダッシュボード用）"""
        return await self.store.get_messages(limit=limit)

    async def approve(self, message_id: int, approved: bool):
        """オーナーが承認/却下"""
        await self.store.approve_message(message_id, approved)
