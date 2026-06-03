"""
health_score.py — ヘルススコアシステム（New-07）
ユーザーの行動データから0〜100点のヘルススコアを計算し、
スコア別に自動CS介入（プッシュ通知）を実行するバッチ処理。
毎日0時にAPSchedulerから呼び出す。

AUTO-04: プラットフォームヘルスメトリクス（DAU/MAU比率、認証完了率、
マッチ率、チャット活性率）とグレード判定（S/A/B/C/D）を追加。
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_, distinct


# ============================================================
# ヘルススコア計算ロジック（個人）
# ============================================================

def calculate_health_score(user, recent_activity: dict) -> int:
    """
    ユーザーの健全性スコアを0〜100点で計算する。

    Parameters:
        user: User モデルオブジェクト
        recent_activity: {
            "last_login_days_ago": int,
            "likes_sent_7d": int,
            "chat_reply_rate": float (0.0〜1.0),
            "simulation_count_7d": int,
            "is_paying": bool
        }

    スコア区分:
        80〜100: Healthy（介入不要）
        60〜79:  At Risk（リマインド）
        30〜59:  Critical（強い介入）
        0〜29:   Churning（解約防止オファー）
    """
    score = 0

    # ログイン頻度（30点）
    days = recent_activity.get("last_login_days_ago", 99)
    if days <= 1:
        score += 30
    elif days <= 3:
        score += 22
    elif days <= 7:
        score += 12
    elif days <= 14:
        score += 5
    # 14日超 → 0点

    # プロフィール完成度（15点）
    try:
        from growth_routes import calculate_audit_score
        audit = calculate_audit_score(user)
        score += int(audit["audit_score"] * 0.15)
    except Exception:
        if getattr(user, "is_verified", False):
            score += 8

    # 認証完了（10点）
    if getattr(user, "is_verified", False):
        score += 10

    # いいね送信数（15点）
    likes = recent_activity.get("likes_sent_7d", 0)
    score += min(likes * 3, 15)

    # チャット返信率（15点）
    reply_rate = recent_activity.get("chat_reply_rate", 0.0)
    score += int(reply_rate * 15)

    # シミュレーション利用（10点）
    sim_count = recent_activity.get("simulation_count_7d", 0)
    score += min(sim_count * 5, 10)

    # 課金ユーザー（5点）
    if recent_activity.get("is_paying"):
        score += 5

    return max(0, min(100, score))


def get_health_segment(score: int) -> str:
    """スコアをセグメント名に変換"""
    if score >= 80:
        return "healthy"
    elif score >= 60:
        return "at_risk"
    elif score >= 30:
        return "critical"
    return "churning"


# ============================================================
# プラットフォームヘルスメトリクス（AUTO-04）
# ============================================================

def _score_dau_mau(ratio: float) -> int:
    """DAU/MAU比率を25点満点でスコアリング"""
    if ratio >= 0.4:
        return 25
    elif ratio >= 0.3:
        return 20
    elif ratio >= 0.2:
        return 13
    elif ratio >= 0.1:
        return 7
    return 0


def _score_verification_rate(rate: float) -> int:
    """認証完了率（%）を25点満点でスコアリング"""
    if rate >= 50.0:
        return 25
    elif rate >= 30.0:
        return 18
    elif rate >= 15.0:
        return 10
    return 5


def _score_match_rate(rate: float) -> int:
    """マッチ率（%）を25点満点でスコアリング"""
    if rate >= 30.0:
        return 25
    elif rate >= 20.0:
        return 18
    elif rate >= 10.0:
        return 12
    return 5


def _score_chat_active_rate(rate: float) -> int:
    """チャット活性率（%）を25点満点でスコアリング"""
    if rate >= 60.0:
        return 25
    elif rate >= 40.0:
        return 18
    elif rate >= 20.0:
        return 12
    return 5


def _get_grade(score: int) -> str:
    """合計スコアからグレードを判定（S/A/B/C/D）"""
    if score >= 85:
        return "S"
    elif score >= 70:
        return "A"
    elif score >= 55:
        return "B"
    elif score >= 40:
        return "C"
    return "D"


async def calculate_platform_health(db: AsyncSession) -> dict:
    """
    プラットフォーム全体のヘルスメトリクスを計算する。

    返り値:
        {
            "grade": "B",
            "score": 65,
            "details": {
                "dau_mau_ratio": 0.35,
                "verification_rate": 30.0,
                "match_rate": 20.0,
                "chat_active_rate": 45.0
            }
        }
    """
    from models import User, SimulationResult, Match, Message

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    # --- 全ユーザー数 ---
    total_users_result = await db.execute(
        select(func.count()).select_from(User)
    )
    total_users = total_users_result.scalar() or 0

    # --- DAU/MAU比率: 7日以内にログインしたユーザー / 全ユーザー ---
    if total_users > 0:
        # last_login_date が YYYY-MM-DD 文字列なので文字列比較で判定
        seven_days_ago_str = seven_days_ago.strftime("%Y-%m-%d")
        active_users_result = await db.execute(
            select(func.count()).select_from(User).where(
                User.last_login_date >= seven_days_ago_str
            )
        )
        active_users = active_users_result.scalar() or 0
        dau_mau_ratio = round(active_users / total_users, 4)
    else:
        dau_mau_ratio = 0.0

    # --- 認証完了率: is_verified=True / 全ユーザー ---
    if total_users > 0:
        verified_result = await db.execute(
            select(func.count()).select_from(User).where(
                User.is_verified == True  # noqa: E712
            )
        )
        verified_count = verified_result.scalar() or 0
        verification_rate = round((verified_count / total_users) * 100, 2)
    else:
        verification_rate = 0.0

    # --- マッチ率: マッチ数 / シミュレーション数 ---
    total_simulations_result = await db.execute(
        select(func.count()).select_from(SimulationResult)
    )
    total_simulations = total_simulations_result.scalar() or 0

    total_matches_result = await db.execute(
        select(func.count()).select_from(Match)
    )
    total_matches = total_matches_result.scalar() or 0

    if total_simulations > 0:
        match_rate = round((total_matches / total_simulations) * 100, 2)
    else:
        match_rate = 0.0

    # --- チャット活性率: メッセージがあるマッチ / 全マッチ ---
    if total_matches > 0:
        active_chats_result = await db.execute(
            select(func.count(distinct(Message.match_id))).select_from(Message)
        )
        active_chats = active_chats_result.scalar() or 0
        chat_active_rate = round((active_chats / total_matches) * 100, 2)
    else:
        chat_active_rate = 0.0

    # --- スコア計算 ---
    score = (
        _score_dau_mau(dau_mau_ratio)
        + _score_verification_rate(verification_rate)
        + _score_match_rate(match_rate)
        + _score_chat_active_rate(chat_active_rate)
    )
    grade = _get_grade(score)

    return {
        "grade": grade,
        "score": score,
        "details": {
            "dau_mau_ratio": dau_mau_ratio,
            "verification_rate": verification_rate,
            "match_rate": match_rate,
            "chat_active_rate": chat_active_rate,
        },
    }


# ============================================================
# 日次ヘルスチェックバッチ（APSchedulerから呼び出し）
# ============================================================

async def run_daily_health_check():
    """
    毎日0時に実行。全ユーザーのヘルススコアを計算して自動介入する。
    APScheduler の add_job から呼び出す。
    最後にプラットフォームヘルスも計算してSlackレポートに含める。
    """
    from database import AsyncSessionLocal
    from models import User, SimulationResult
    from notifications import send_push_notification
    from agent_system.memory_store import MemoryStore

    store = MemoryStore()

    async with AsyncSessionLocal() as db:
        users_result = await db.execute(select(User))
        users = users_result.scalars().all()

        healthy_count = at_risk_count = critical_count = churning_count = 0

        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)

        for user in users:
            updated_at = getattr(user, "updated_at", None) or getattr(user, "created_at", None)
            days_ago = (
                (now - updated_at).days
                if updated_at else 99
            )

            # --- リアルデータクエリ: 7日以内のシミュレーション件数 ---
            sim_count_result = await db.execute(
                select(func.count()).select_from(SimulationResult).where(
                    and_(
                        (SimulationResult.user_a_id == user.id) | (SimulationResult.user_b_id == user.id),
                        SimulationResult.created_at >= seven_days_ago,
                    )
                )
            )
            simulation_count_7d = sim_count_result.scalar() or 0

            # likes_sent_7d: SimulationResultの件数で代用（user_a_id側をlike送信とみなす）
            likes_result = await db.execute(
                select(func.count()).select_from(SimulationResult).where(
                    and_(
                        SimulationResult.user_a_id == user.id,
                        SimulationResult.created_at >= seven_days_ago,
                    )
                )
            )
            likes_sent_7d = likes_result.scalar() or 0

            activity = {
                "last_login_days_ago": days_ago,
                "likes_sent_7d": likes_sent_7d,
                "chat_reply_rate": 0.5,
                "simulation_count_7d": simulation_count_7d,
                "is_paying": False,
            }

            health = calculate_health_score(user, activity)
            segment = get_health_segment(health)

            # KPI記録
            await store.save_kpi(f"health_{segment}_count",
                                 float({"healthy": healthy_count, "at_risk": at_risk_count,
                                        "critical": critical_count, "churning": churning_count}.get(segment, 0) + 1))

            if segment == "healthy":
                healthy_count += 1

            elif segment == "at_risk" and days_ago >= 3:
                at_risk_count += 1
                await send_push_notification(
                    user.id, "health_risk", db=db
                )

            elif segment == "critical" and days_ago >= 2:
                critical_count += 1
                await send_push_notification(
                    user.id, "health_risk", db=db
                )

            elif segment == "churning" and days_ago >= 7:
                churning_count += 1
                await send_push_notification(
                    user.id, "health_risk", db=db
                )

        # 日次サマリーをKPIとして記録
        await store.save_kpi("health_check_total_users", float(len(users)))
        await store.save_kpi("health_healthy_ratio",
                             float(healthy_count / max(len(users), 1)))

        # --- プラットフォームヘルスを計算（AUTO-04） ---
        platform_health = await calculate_platform_health(db)

        await store.save_kpi("platform_health_score", float(platform_health["score"]))
        await store.save_kpi("platform_health_dau_mau", float(platform_health["details"]["dau_mau_ratio"]))
        await store.save_kpi("platform_health_verification_rate", float(platform_health["details"]["verification_rate"]))
        await store.save_kpi("platform_health_match_rate", float(platform_health["details"]["match_rate"]))
        await store.save_kpi("platform_health_chat_active_rate", float(platform_health["details"]["chat_active_rate"]))

        # Slackに日次サマリーを送信（プラットフォームヘルス情報を追加）
        try:
            import os, httpx
            webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
            if webhook and users:
                details = platform_health["details"]
                await httpx.AsyncClient().post(webhook, json={"blocks": [
                    {"type": "header", "text": {"type": "plain_text",
                                                "text": "📊 Persona 日次ヘルスチェック完了"}},
                    {"type": "section", "text": {"type": "mrkdwn",
                     "text": (
                         f"*総ユーザー数:* {len(users)}人\n"
                         f"🟢 Healthy: {healthy_count}人\n"
                         f"🟡 At Risk: {at_risk_count}人（通知送信済み）\n"
                         f"🟠 Critical: {critical_count}人（通知送信済み）\n"
                         f"🔴 Churning: {churning_count}人（通知送信済み）"
                     )}},
                    {"type": "divider"},
                    {"type": "header", "text": {"type": "plain_text",
                                                "text": "🏥 プラットフォームヘルス"}},
                    {"type": "section", "text": {"type": "mrkdwn",
                     "text": (
                         f"*グレード:* {platform_health['grade']}　"
                         f"*スコア:* {platform_health['score']}/100\n"
                         f"• DAU/MAU比率: {details['dau_mau_ratio']}\n"
                         f"• 認証完了率: {details['verification_rate']}%\n"
                         f"• マッチ率: {details['match_rate']}%\n"
                         f"• チャット活性率: {details['chat_active_rate']}%"
                     )}},
                ]})
        except Exception:
            pass

        return {
            "total": len(users),
            "healthy": healthy_count,
            "at_risk": at_risk_count,
            "critical": critical_count,
            "churning": churning_count,
            "platform_health": platform_health,
        }
