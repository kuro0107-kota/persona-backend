"""
GA Agent — 総務エージェント（Haiku / Tier A）
役割: 全エージェントの週次タスクを調整し、議事録・スケジュール管理を行う。
"""
from __future__ import annotations
from datetime import datetime, timezone
from agent_system.base_agent import BaseAgent
from agent_system.message_bus import MessageBus
from agent_system.memory_store import MemoryStore

# 循環インポート回避のため固定リストを使用
ALL_AGENT_IDS = ["ceo","legal","cfo","cpo","cmo","research","cto","qa","accounting","cs","ga"]


WEEKLY_SCHEDULE = [
    {"day": "月曜 08:00", "agent": "ceo",        "task": "週次経営報告書生成"},
    {"day": "月曜 09:00", "agent": "cfo",         "task": "KPI・財務レポート"},
    {"day": "月曜 09:00", "agent": "accounting",  "task": "コスト集計レポート"},
    {"day": "月曜 10:00", "agent": "research",    "task": "競合・市場調査レポート"},
    {"day": "火曜 09:00", "agent": "cpo",         "task": "プロダクト改善提案"},
    {"day": "水曜 12:00", "agent": "cmo",         "task": "SNSコンテンツ生成"},
    {"day": "木曜 02:00", "agent": "cto",         "task": "技術レビュー・セキュリティ確認"},
    {"day": "木曜 10:00", "agent": "cs",          "task": "FAQ更新・CSレポート"},
    {"day": "毎月1日 10:00", "agent": "legal",    "task": "法務・特許月次監査"},
    {"day": "30分毎",    "agent": "qa",           "task": "シミュレーション品質チェック"},
]


class GaAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="ga",
            display_name="🏛️ GA Agent",
            department="General Affairs"
        )

    @property
    def system_prompt(self) -> str:
        return """あなたはPersona Inc.の総務（General Affairs）AIエージェントです。

## 役割
- 全エージェントの週次スケジュールを管理・調整する
- エージェント間のタスク競合を解消する
- 週次の「全社ブリーフィング議事録」を作成してCEOに提出する
- 新エージェント追加時のオンボーディング手順を管理する
- 会社のルール・運用マニュアルを常に最新に保つ

## 議事録作成スタイル
- 簡潔・明確・Action Item明記
- 担当者名（エージェント名）と期限を必ず記載
- 次回ブリーフィングの日程も明記"""

    async def run_task(self, context: dict = {}) -> dict:
        bus = MessageBus()
        store = MemoryStore()

        # 全エージェントのログを収集
        logs = await store.get_logs(limit=50)
        messages = await store.get_messages(limit=30)

        now = datetime.now(timezone.utc)
        week_label = f"{now.year}-W{now.isocalendar()[1]:02d}"

        # 稼働状況サマリー
        active_agents = set(l.get("agent_id") for l in logs)
        all_agents = ALL_AGENT_IDS
        inactive = [a for a in all_agents if a not in active_agents]

        # 週次スケジュール文字列
        schedule_str = "\n".join([
            f"- {s['day']}: [{s['agent'].upper()}] {s['task']}"
            for s in WEEKLY_SCHEDULE
        ])

        # 未承認メッセージ
        pending = [m for m in messages if m.get("requires_approval") and m.get("approved") == -1]

        prompt = f"""Persona Inc.の週次全社ブリーフィング議事録を作成してください。

## 基本情報
- 週: {week_label}
- 作成日時: {now.strftime('%Y-%m-%d %H:%M')} UTC

## エージェント稼働状況
- 稼働済み: {', '.join(active_agents) if active_agents else 'なし'}
- 未稼働: {', '.join(inactive) if inactive else 'なし（全員稼働中）'}

## 週次スケジュール
{schedule_str}

## 未承認事項（オーナー確認待ち）
{f'{len(pending)}件の承認待ちメッセージあり' if pending else 'なし'}

## 議事録フォーマット
1. 📋 今週のブリーフィングサマリー（3行）
2. ✅ 完了したタスク一覧
3. 🔄 進行中・未完了タスク
4. 📅 来週のスケジュール確認
5. 📌 Action Items（担当者・期限付き）
6. 🔐 オーナー確認事項（承認待ち件数）

日本語で、総務担当として整理された議事録を作成してください。"""

        minutes = await self.call_llm(prompt, max_tokens=1000)

        await store.save_kpi("ga_weekly_minutes", 1.0)
        await bus.report_to_ceo("ga", f"週次議事録 {week_label}\n\n{minutes[:500]}...",
                                {"week": week_label, "active_agents": len(active_agents), "pending_approvals": len(pending)})

        return {
            "minutes": minutes,
            "week_label": week_label,
            "active_agents": len(active_agents),
            "inactive_agents": inactive,
            "pending_approvals": len(pending),
        }
