"""
Scheduler — APSchedulerベースの全11エージェント自律稼働システム
CEO判断 #001 スケジュール定義（Phase 3完全版）
"""
from __future__ import annotations
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from agent_system.agents import get_agent

logger = logging.getLogger(__name__)

# ── 全11エージェント スケジュール定義（日次高速モード）────────
SCHEDULES = [
    # (agent_id,      cron_expr,          description)

    # Tier A: Haiku — 高頻度・軽量タスク（毎日実行）
    ("qa",         "*/30 * * * *",    "QA品質チェック（30分ごと）"),
    ("cs",         "0 9 * * *",       "CS/FAQ更新（毎日9時）"),
    ("accounting", "0 9 * * *",       "経理日次レポート（毎日9時）"),
    ("ga",         "0 8 * * *",       "総務日次議事録（毎日8時）"),

    # Tier B: Sonnet — 日次・分析タスク（毎日実行・時間をずらして負荷分散）
    ("cfo",        "0 8,18 * * *",    "CFO KPIレポート（毎日8時・18時）"),
    ("cpo",        "0 10 * * *",      "CPOプロダクト分析（毎日10時）"),
    ("cmo",        "0 6 * * *",       "CMOコンテンツ生成（毎日6時）"),
    ("cto",        "0 2 * * *",       "CTO技術レビュー（毎日2時）"),
    ("research",   "0 10 * * 1,4",    "競合調査レポート（月・木10時）"),

    # Tier C: Opus — 日次・重大判断タスク
    ("ceo",        "0 8 * * *",       "CEO日次経営報告書（毎日8時）"),
    ("legal",      "0 10 1,15 * *",   "法務監査（1日・15日 10時）"),
]

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Asia/Tokyo")
    return _scheduler


async def _run_agent_job(agent_id: str):
    logger.info(f"[Scheduler] Starting: {agent_id}")
    try:
        agent = get_agent(agent_id)
        result = await agent.execute()
        logger.info(f"[Scheduler] Done: {agent_id} → {result.get('status', '?')}")
    except Exception as e:
        logger.error(f"[Scheduler] Failed: {agent_id} → {e}")


async def _run_daily_health_check():
    """New-07: 日次ヘルスチェックバッチ（毎敥0時15分）"""
    logger.info("[Scheduler] Running daily health check...")
    try:
        from health_score import run_daily_health_check
        result = await run_daily_health_check()
        logger.info(f"[Scheduler] Health check done: {result}")
    except Exception as e:
        logger.error(f"[Scheduler] Health check failed: {e}")


def start_scheduler():
    scheduler = get_scheduler()
    if scheduler.running:
        return

    for agent_id, cron_expr, description in SCHEDULES:
        trigger = CronTrigger.from_crontab(cron_expr, timezone="Asia/Tokyo")
        scheduler.add_job(
            _run_agent_job,
            trigger=trigger,
            args=[agent_id],
            id=f"agent_{agent_id}",
            name=description,
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info(f"[Scheduler] Registered: {agent_id} ({cron_expr})")

    scheduler.start()
    logger.info(f"[Scheduler] Started with {len(SCHEDULES)} agent jobs.")

    # New-07: 日次ヘルスチェック（毎敥0時15分）
    scheduler.add_job(
        _run_daily_health_check,
        trigger=CronTrigger.from_crontab("15 0 * * *", timezone="Asia/Tokyo"),
        id="daily_health_check",
        name="日次ヘルスチェック（毎敥0時15分）",
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("[Scheduler] Registered: daily_health_check (15 0 * * *)")


def stop_scheduler():
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped.")


def get_jobs_status() -> list:
    scheduler = get_scheduler()
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        }
        for job in scheduler.get_jobs()
    ]
