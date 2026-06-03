"""
Agent Routes — FastAPI エージェント管理APIルーター
/api/v1/agents/* エンドポイント群
Phase 4: Markdownエクスポート・タイムライン追加
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from agent_system.agents import get_agent, AGENT_REGISTRY
from agent_system.memory_store import MemoryStore
from agent_system.message_bus import MessageBus
from agent_system.scheduler import get_jobs_status
from agent_system.base_agent import AGENT_MODEL_MAP

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


# ===== エージェント実行 =====

class RunAgentRequest(BaseModel):
    context: dict = {}

@router.post("/run/{agent_id}")
async def run_agent(agent_id: str, payload: RunAgentRequest, background_tasks: BackgroundTasks):
    """エージェントを手動で実行する（バックグラウンド実行）"""
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(404, f"Agent '{agent_id}' not found. Available: {list(AGENT_REGISTRY.keys())}")

    async def _run():
        agent = get_agent(agent_id)
        await agent.execute(payload.context)

    background_tasks.add_task(_run)
    return {
        "status": "started",
        "agent_id": agent_id,
        "message": f"{agent_id} エージェントをバックグラウンドで実行中です。"
    }


@router.post("/run/{agent_id}/sync")
async def run_agent_sync(agent_id: str, payload: RunAgentRequest):
    """エージェントを同期実行して結果を即返す（テスト用）"""
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(404, f"Agent '{agent_id}' not found.")
    agent = get_agent(agent_id)
    result = await agent.execute(payload.context)
    return result


# ===== ステータス確認 =====

@router.get("/status")
async def get_all_agents_status():
    """全エージェントのステータス一覧"""
    agents_info = []
    for agent_id, agent_cls in AGENT_REGISTRY.items():
        agent = agent_cls()
        status = agent.status()
        status["schedule"] = _get_schedule_for_agent(agent_id)
        agents_info.append(status)

    scheduler_jobs = get_jobs_status()

    return {
        "agents": agents_info,
        "scheduler_jobs": scheduler_jobs,
        "total_agents": len(agents_info),
    }


@router.get("/status/{agent_id}")
async def get_agent_status(agent_id: str):
    """特定エージェントのステータス"""
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(404, f"Agent '{agent_id}' not found.")
    agent = get_agent(agent_id)
    return agent.status()


# ===== ログ =====

@router.get("/logs")
async def get_agent_logs(agent_id: Optional[str] = None, limit: int = 50):
    """エージェント実行ログ一覧"""
    store = MemoryStore()
    logs = await store.get_logs(agent_id=agent_id, limit=limit)
    return {"logs": logs, "count": len(logs)}


# ===== タイムライン（Phase 4追加） =====

@router.get("/timeline")
async def get_timeline(limit: int = 100):
    """全エージェントの実行タイムライン（時系列）"""
    store = MemoryStore()
    logs = await store.get_logs(limit=limit)
    msgs = await store.get_messages(limit=limit)

    events = []

    for log in logs:
        events.append({
            "type": "execution",
            "agent_id": log.get("agent_id"),
            "agent_name": log.get("agent_name", log.get("agent_id")),
            "status": log.get("status"),
            "model": log.get("model_used", ""),
            "timestamp": log.get("finished_at") or log.get("started_at"),
            "summary": _extract_summary(log.get("result_json", "{}")),
        })

    for msg in msgs:
        events.append({
            "type": "message",
            "agent_id": msg.get("from_agent"),
            "agent_name": msg.get("from_agent"),
            "message_type": msg.get("message_type"),
            "to_agent": msg.get("to_agent"),
            "priority": msg.get("priority", 1),
            "requires_approval": msg.get("requires_approval", 0),
            "approved": msg.get("approved", -1),
            "timestamp": msg.get("created_at"),
            "summary": str(msg.get("content", {}).get("report", msg.get("content", {}).get("title", "")))[:100],
        })

    # 時系列ソート
    events.sort(key=lambda e: e.get("timestamp") or "", reverse=True)

    return {"events": events[:limit], "count": len(events)}


# ===== メッセージ =====

@router.get("/messages")
async def get_messages(to_agent: Optional[str] = None, limit: int = 50):
    """エージェントメッセージ一覧（ダッシュボード用）"""
    bus = MessageBus()
    if to_agent:
        messages = await bus.get_inbox(to_agent, limit)
    else:
        messages = await bus.get_all_messages(limit)
    return {"messages": messages, "count": len(messages)}


class ApproveRequest(BaseModel):
    approved: bool

@router.post("/messages/{message_id}/approve")
async def approve_message(message_id: int, payload: ApproveRequest):
    """オーナーがメッセージを承認/却下する"""
    bus = MessageBus()
    await bus.approve(message_id, payload.approved)
    action = "承認" if payload.approved else "却下"
    return {"status": "ok", "message_id": message_id, "action": action}


# ===== KPI =====

@router.get("/kpi")
async def get_kpis(metric_name: Optional[str] = None, limit: int = 100):
    """KPIスナップショット一覧"""
    store = MemoryStore()
    kpis = await store.get_kpis(metric_name=metric_name, limit=limit)
    return {"kpis": kpis, "count": len(kpis)}


# ===== 週次レポート =====

@router.get("/reports")
async def get_weekly_reports(limit: int = 10):
    """CEOの週次経営報告書一覧"""
    store = MemoryStore()
    reports = await store.get_weekly_reports(limit=limit)
    return {"reports": reports, "count": len(reports)}


# ===== Markdownエクスポート（Phase 4追加） =====

@router.get("/export/markdown", response_class=PlainTextResponse)
async def export_markdown(weeks: int = 4):
    """週次レポート・KPI・ログをMarkdown形式でエクスポート"""
    store = MemoryStore()
    now = datetime.now(timezone.utc)

    reports = await store.get_weekly_reports(limit=weeks)
    kpis = await store.get_kpis(limit=200)
    logs = await store.get_logs(limit=50)

    # KPI最新値サマリー
    kpi_latest: dict = {}
    for k in reversed(kpis):
        kpi_latest[k["metric_name"]] = k["metric_value"]

    lines = [
        f"# Persona Inc. 運営レポート",
        f"",
        f"エクスポート日時: {now.strftime('%Y-%m-%d %H:%M')} UTC",
        f"",
        f"---",
        f"",
        f"## 📈 KPI サマリー（最新値）",
        f"",
        f"| 指標 | 最新値 |",
        f"|---|---|",
    ]
    for name, val in kpi_latest.items():
        lines.append(f"| {name} | {round(val, 3)} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## 📋 エージェント実行ログ（直近{len(logs)}件）",
        f"",
        f"| 日時 | エージェント | ステータス | モデル |",
        f"|---|---|---|---|",
    ]
    for log in logs:
        ts = log.get("finished_at", log.get("started_at", ""))[:16] if log.get("finished_at") else ""
        agent = log.get("agent_name") or log.get("agent_id", "")
        status = "✅" if log.get("status") == "success" else "❌"
        model = log.get("model_used", "").split("-")[-1]
        lines.append(f"| {ts} | {agent} | {status} | {model} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## 📄 CEO 週次経営報告書（直近{len(reports)}件）",
        f"",
    ]
    for report in reports:
        lines.append(f"### {report.get('week_label', '不明')} — {report.get('created_at', '')[:10]}")
        lines.append(f"")
        lines.append(report.get("report_text", ""))
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

    md = "\n".join(lines)

    # ファイルとして保存
    import os
    export_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
    os.makedirs(export_dir, exist_ok=True)
    fname = f"persona_report_{now.strftime('%Y%m%d_%H%M')}.md"
    with open(os.path.join(export_dir, fname), "w", encoding="utf-8") as f:
        f.write(md)

    return md


# ===== ヘルパー =====

AGENT_SCHEDULES = {
    "ceo":        "月曜 08:00",
    "legal":      "毎月1日 10:00",
    "cfo":        "月曜 09:00",
    "cpo":        "火曜 09:00",
    "cmo":        "水曜 12:00",
    "research":   "月曜 10:00",
    "cto":        "木曜 02:00",
    "qa":         "30分ごと",
    "accounting": "月曜 09:00",
    "cs":         "毎日 09:00",
    "ga":         "月曜 08:00",
}

def _get_schedule_for_agent(agent_id: str) -> str:
    return AGENT_SCHEDULES.get(agent_id, "手動実行のみ")

def _extract_summary(result_json: str) -> str:
    import json
    try:
        d = json.loads(result_json)
        for key in ("report", "analysis", "content", "minutes", "error"):
            if key in d and d[key]:
                return str(d[key])[:100]
    except Exception:
        pass
    return ""
