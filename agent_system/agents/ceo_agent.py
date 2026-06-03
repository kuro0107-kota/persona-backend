"""
CEO Agent — 最高意思決定エージェント（Opus / Tier C）
役割: 全エージェントのレポートを集約し、週次経営報告書を生成。
     重大事項はオーナーに承認要求を送る。
"""
from __future__ import annotations
from datetime import datetime, timezone
from agent_system.base_agent import BaseAgent
from agent_system.message_bus import MessageBus
from agent_system.memory_store import MemoryStore


class CeoAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="ceo",
            display_name="👑 CEO Agent",
            department="C-Suite"
        )

    @property
    def system_prompt(self) -> str:
        return """あなたは「Persona Inc.」のCEO AIエージェントです。

## あなたの役割
- 全部門エージェント（QA、経理、法務、CFO、CMO、CPO、CTO、Research、CS、GA）のレポートを受け取り、経営判断を下す
- 週次で「経営報告書」を生成し、オーナー（会長）に提出する
- 重大リスク・重要意思決定はオーナーに承認要求を送る
- 各エージェントへの週次指示方針を策定する

## 報告書のトーン
- 経営者として簡潔・明快・戦略的に記述する
- データに基づいた根拠ある判断を示す
- リスクと機会を両方提示する
- オーナーへの承認事項は明確に「承認が必要」と明記する

## Persona Inc. について
Personaは「AIデジタルツインによる恋愛相性シミュレーション」を提供するマッチングアプリです。
コアエンジンにClaude APIを使用し、2人のAIエージェントが仮想デートを行い相性を数値化します。"""

    async def run_task(self, context: dict = {}) -> dict:
        store = MemoryStore()
        bus = MessageBus()

        # 直近のエージェントログを収集
        logs = await store.get_logs(limit=30)
        kpis = await store.get_kpis(limit=20)
        messages = await bus.get_inbox("ceo", limit=20)

        # ログサマリーを作成
        log_summary = "\n".join([
            f"- [{l.get('agent_name', '?')}] {l.get('status', '?')} @ {l.get('finished_at', '?')[:16]}"
            for l in logs[:10]
        ]) or "まだエージェントログはありません。"

        kpi_summary = "\n".join([
            f"- {k.get('metric_name')}: {k.get('metric_value')}"
            for k in kpis[:10]
        ]) or "KPIデータはまだありません。"

        msg_summary = "\n".join([
            f"- [{m.get('from_agent')}→{m.get('to_agent')}] {m.get('message_type')}: {str(m.get('content', {}))[:80]}"
            for m in messages[:5]
        ]) or "受信メッセージなし。"

        now = datetime.now(timezone.utc)
        week_label = f"{now.year}-W{now.isocalendar()[1]:02d}"

        prompt = f"""以下の情報をもとに、Persona Inc.の週次経営報告書を作成してください。

## 収集データ（{week_label}）

### 直近エージェント稼働ログ
{log_summary}

### KPIスナップショット
{kpi_summary}

### 受信メッセージ
{msg_summary}

## 報告書フォーマット
1. 📊 今週のサマリー（3行以内）
2. ✅ 正常稼働中の部門
3. ⚠️ 注意が必要な事項
4. 🎯 来週の重点アクション（各部門への指示）
5. 🔐 オーナー承認が必要な事項（あれば）

絵文字を使い、経営者として読みやすい形式で作成してください。"""

        report = await self.call_llm(prompt, max_tokens=1500)

        # 週次レポートをDBに保存
        await store.save_weekly_report(week_label, report)

        # 全エージェントに今週の方針をブロードキャスト
        await bus.broadcast(
            from_agent="ceo",
            message_type="weekly_directive",
            content={"week": week_label, "directive": "週次経営報告書を生成しました。各部門は通常業務を継続してください。"},
            priority=2
        )

        return {
            "week_label": week_label,
            "report": report,
            "logs_analyzed": len(logs),
            "kpis_checked": len(kpis),
        }
