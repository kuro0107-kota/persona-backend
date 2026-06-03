"""
cache.py — シミュレーション結果キャッシュ（P-01: APIコスト1/20削減）
同一ペアの24時間以内のシミュレーション結果をDBから再利用する。
MAU1500人超えでのAPI破産リスクを排除する。
"""
import hashlib
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_

CACHE_TTL_HOURS = 24  # 24時間キャッシュ


def make_cache_key(user_a_id: str, user_b_id: str) -> str:
    """ペアのキャッシュキーを生成（A-B と B-A を同一視）"""
    pair = tuple(sorted([user_a_id, user_b_id]))
    return hashlib.md5(f"{pair[0]}:{pair[1]}".encode()).hexdigest()


async def get_cached_simulation(
    user_a_id: str,
    user_b_id: str,
    db: AsyncSession
) -> dict | None:
    """
    24時間以内の同一ペアのシミュレーション結果を返す。
    ヒットしなければ None を返す（フルシミュレーション実行）。
    """
    from models import SimulationResult

    cutoff = datetime.now(timezone.utc) - timedelta(hours=CACHE_TTL_HOURS)

    stmt = (
        select(SimulationResult)
        .where(
            or_(
                and_(
                    SimulationResult.user_a_id == user_a_id,
                    SimulationResult.user_b_id == user_b_id,
                ),
                and_(
                    SimulationResult.user_a_id == user_b_id,
                    SimulationResult.user_b_id == user_a_id,
                ),
            ),
            SimulationResult.created_at >= cutoff,
        )
        .order_by(SimulationResult.created_at.desc())
        .limit(1)
    )

    result = await db.execute(stmt)
    cached = result.scalars().first()

    if cached:
        return {
            "simulation_id": str(cached.id),
            "status": "CACHED",
            "compatibility_score": float(cached.compatibility_score or 0.0),
            "summary": "キャッシュ済み結果（24時間以内の同一ペア）",
            "breakdown": cached.breakdown_json or {},
            "fatal_flaw_detected": bool(cached.fatal_flaw_detected),
            "transcript": [],
            "agent_report": cached.agent_report or "",
            "target_user_id": user_b_id,
            "target_user_profile": {},
            "cached": True,
        }
    return None
