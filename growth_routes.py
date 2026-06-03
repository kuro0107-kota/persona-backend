"""
growth_routes.py — 成長機能APIルーター
New-01: ウェイティングリスト
New-02: リファラルプログラム
New-04: ブロック・通報
New-06: 審査制バッジ
New-08: ストリーク（連続ログインボーナス）
"""
from __future__ import annotations

import io
import os
import json
import base64
from datetime import datetime, timezone, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from database import get_db
from models import (
    User, WaitlistEntry, ReferralRecord, Block, Report,
    SimulationResult, Match, Message,
    HobbyTag, UserHobbyTag,
    generate_referral_code,
)

router = APIRouter(prefix="/api/v1", tags=["growth"])

# ============================================================
# New-01: ウェイティングリスト
# ============================================================

class WaitlistRequest(BaseModel):
    email: str
    gender: str = ""
    age_range: str = ""
    referral_code: str = ""


@router.post("/waitlist/join")
async def join_waitlist(payload: WaitlistRequest, db: AsyncSession = Depends(get_db)):
    """ウェイティングリストに参加する（女性は優先順位UP）"""

    # 重複チェック
    existing = await db.execute(
        select(WaitlistEntry).where(WaitlistEntry.email == payload.email)
    )
    if existing.scalars().first():
        return {"status": "already_registered", "message": "このメールアドレスは既に登録済みです"}

    # 現在の参加者数
    count_result = await db.execute(select(func.count(WaitlistEntry.id)))
    current_count = count_result.scalar() or 0

    # 紹介コードがある場合、紹介者の順番を上げる
    if payload.referral_code:
        referrer = await db.execute(
            select(WaitlistEntry).where(WaitlistEntry.my_referral_code == payload.referral_code)
        )
        referrer_entry = referrer.scalars().first()
        if referrer_entry:
            referrer_entry.referral_count = (referrer_entry.referral_count or 0) + 1
            referrer_entry.position = max(1, (referrer_entry.position or current_count) - 50)

    # 女性先行戦略: 女性は200人分繰り上げ
    base_position = current_count + 1
    if payload.gender == "female":
        base_position = max(1, base_position - 200)

    my_code = generate_referral_code()
    entry = WaitlistEntry(
        email=payload.email,
        gender=payload.gender,
        age_range=payload.age_range,
        referral_code=payload.referral_code or None,
        my_referral_code=my_code,
        position=base_position,
        referral_count=0,
        status="waiting",
    )
    db.add(entry)
    await db.commit()

    return {
        "status": "registered",
        "position": base_position,
        "total_waiting": current_count + 1,
        "my_referral_code": my_code,
        "referral_url": f"https://persona-app.jp/waitlist?ref={my_code}",
        "message": f"ウェイティングリスト {base_position}番目に登録されました！",
        "female_bonus": payload.gender == "female",
    }


@router.get("/waitlist/stats")
async def get_waitlist_stats(db: AsyncSession = Depends(get_db)):
    """ウェイティングリストの統計（LP表示用）"""
    count_result = await db.execute(select(func.count(WaitlistEntry.id)))
    total = count_result.scalar() or 0

    female_result = await db.execute(
        select(func.count(WaitlistEntry.id)).where(WaitlistEntry.gender == "female")
    )
    female_count = female_result.scalar() or 0

    return {
        "total_waiting": total,
        "female_count": female_count,
        "male_count": total - female_count,
        "message": f"現在{total}人がウェイティング中",
    }


# ============================================================
# New-02: リファラルプログラム
# ============================================================

REFERRAL_BONUS_LIKES = 30  # 招待1件あたりのいいね付与数

class ReferralRequest(BaseModel):
    referred_user_id: str
    referral_code: str


@router.post("/referral/apply")
async def apply_referral(payload: ReferralRequest, db: AsyncSession = Depends(get_db)):
    """招待コードを適用してボーナスいいねを双方に付与する"""

    # 紹介コードからユーザーを検索
    referrer_result = await db.execute(
        select(User).where(User.referral_code == payload.referral_code)
    )
    referrer = referrer_result.scalars().first()
    if not referrer:
        raise HTTPException(400, "Invalid referral code")

    # 重複チェック
    dup = await db.execute(
        select(ReferralRecord).where(ReferralRecord.referred_user_id == payload.referred_user_id)
    )
    if dup.scalars().first():
        return {"status": "already_applied"}

    record = ReferralRecord(
        referrer_user_id=referrer.id,
        referred_user_id=payload.referred_user_id,
        bonus_given=True,
    )
    db.add(record)

    # 双方にいいねボーナス
    referrer.likes_balance = (referrer.likes_balance or 10) + REFERRAL_BONUS_LIKES

    referred = await db.get(User, payload.referred_user_id)
    if referred:
        referred.likes_balance = (referred.likes_balance or 10) + REFERRAL_BONUS_LIKES

    await db.commit()

    return {
        "status": "applied",
        "referrer_id": referrer.id,
        "bonus_likes": REFERRAL_BONUS_LIKES,
        "message": f"招待コード適用！双方にいいね{REFERRAL_BONUS_LIKES}枚をプレゼント🎁",
    }


@router.get("/users/{user_id}/referral-info")
async def get_referral_info(user_id: str, db: AsyncSession = Depends(get_db)):
    """ユーザーの招待コードと招待実績を返す"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # 招待コードがなければ自動生成
    if not user.referral_code:
        user.referral_code = generate_referral_code()
        await db.commit()

    count_result = await db.execute(
        select(func.count(ReferralRecord.id)).where(
            ReferralRecord.referrer_user_id == user_id,
            ReferralRecord.bonus_given == True,
        )
    )
    referral_count = count_result.scalar() or 0

    return {
        "referral_code": user.referral_code,
        "referral_url": f"https://persona-app.jp/register?ref={user.referral_code}",
        "referral_count": referral_count,
        "likes_balance": user.likes_balance or 10,
        "bonus_per_referral": REFERRAL_BONUS_LIKES,
    }


# ============================================================
# New-04: ブロック・通報機能（法令上必須）
# ============================================================

class BlockRequest(BaseModel):
    blocker_id: str
    blocked_id: str


@router.post("/blocks")
async def block_user(payload: BlockRequest, db: AsyncSession = Depends(get_db)):
    """ユーザーをブロックする"""
    existing = await db.execute(
        select(Block).where(
            Block.blocker_id == payload.blocker_id,
            Block.blocked_id == payload.blocked_id,
        )
    )
    if existing.scalars().first():
        return {"status": "already_blocked"}

    block = Block(blocker_id=payload.blocker_id, blocked_id=payload.blocked_id)
    db.add(block)
    await db.commit()
    return {"status": "blocked", "message": "ユーザーをブロックしました"}


@router.delete("/blocks/{blocker_id}/{blocked_id}")
async def unblock_user(blocker_id: str, blocked_id: str, db: AsyncSession = Depends(get_db)):
    """ブロックを解除する"""
    result = await db.execute(
        select(Block).where(Block.blocker_id == blocker_id, Block.blocked_id == blocked_id)
    )
    block = result.scalars().first()
    if block:
        await db.delete(block)
        await db.commit()
    return {"status": "unblocked"}


class ReportRequest(BaseModel):
    reporter_id: str
    reported_id: str
    reason: str   # spam | fake | harassment | inappropriate
    detail: str = ""


@router.post("/reports")
async def report_user(payload: ReportRequest, db: AsyncSession = Depends(get_db)):
    """ユーザーを通報する（自動でブロックも実行・3件で管理者Slack通知）"""

    report = Report(
        reporter_id=payload.reporter_id,
        reported_id=payload.reported_id,
        reason=payload.reason,
        detail=payload.detail,
    )
    db.add(report)

    # 自動ブロック
    existing_block = await db.execute(
        select(Block).where(
            Block.blocker_id == payload.reporter_id,
            Block.blocked_id == payload.reported_id,
        )
    )
    if not existing_block.scalars().first():
        db.add(Block(blocker_id=payload.reporter_id, blocked_id=payload.reported_id))

    await db.commit()

    # 同一ユーザーへの通報が3件以上→Slack通知
    count_result = await db.execute(
        select(func.count(Report.id)).where(
            Report.reported_id == payload.reported_id,
            Report.status == "pending",
        )
    )
    report_count = count_result.scalar() or 0

    if report_count >= 3:
        try:
            import os, httpx
            webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
            if webhook:
                await httpx.AsyncClient().post(webhook, json={
                    "text": f"🚨 通報アラート: ユーザー `{payload.reported_id}` への通報が *{report_count}件* に達しました。\n理由: {payload.reason}\n管理画面で確認してください。"
                })
        except Exception:
            pass

    return {
        "status": "reported",
        "message": "通報を受け付けました。確認後、適切な対応を行います。",
    }


# ============================================================
# New-06: 審査制バッジ（自動審査 / コストほぼゼロ）
# ============================================================

def calculate_audit_score(user: User) -> dict:
    """
    プロフィール完成度を0〜100点でスコアリングし、
    「審査合格」かどうかを判定する。
    70点以上 = ✅ Persona審査合格バッジ付与
    """
    score = 0
    details = []

    # AI本人確認: 40点
    if user.is_verified:
        score += 40
        details.append({"item": "AI本人確認", "points": 40, "passed": True})
    else:
        details.append({"item": "AI本人確認", "points": 0, "passed": False,
                        "hint": "セルフィー認証を完了してください"})

    # プロフィール写真: 20点（3枚以上で満点）
    photo_count = len(user.photo_urls or [])
    photo_points = min(photo_count * 7, 20)
    score += photo_points
    details.append({"item": f"プロフィール写真（{photo_count}枚）",
                    "points": photo_points, "passed": photo_count >= 3,
                    "hint": "写真を3枚以上追加してください"})

    # 自己紹介文: 20点（200文字以上で満点）
    bio_len = len(user.bio or "")
    bio_points = 20 if bio_len >= 200 else (10 if bio_len >= 100 else 0)
    score += bio_points
    details.append({"item": f"自己紹介（{bio_len}文字）", "points": bio_points,
                    "passed": bio_len >= 200, "hint": "自己紹介を200文字以上書いてください"})

    # MBTI/価値観診断: 10点
    if user.mbti:
        score += 10
        details.append({"item": "価値観診断/MBTI", "points": 10, "passed": True})
    else:
        details.append({"item": "価値観診断/MBTI", "points": 0, "passed": False,
                        "hint": "価値観診断を完了してください"})

    # 基本情報（年齢・職業）: 10点
    if user.age and user.job:
        score += 10
        details.append({"item": "基本情報（年齢・職業）", "points": 10, "passed": True})
    else:
        details.append({"item": "基本情報（年齢・職業）", "points": 0, "passed": False,
                        "hint": "年齢・職業を入力してください"})

    is_approved = score >= 70
    return {
        "audit_score": score,
        "is_approved": is_approved,
        "badge": "✅ Persona審査合格" if is_approved else "⏳ 審査中",
        "details": details,
        "next_hint": next(
            (d["hint"] for d in details if not d["passed"] and "hint" in d), None
        ),
    }


@router.get("/users/{user_id}/audit-badge")
async def get_audit_badge(user_id: str, db: AsyncSession = Depends(get_db)):
    """審査バッジの取得（New-06）"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return calculate_audit_score(user)


# ============================================================
# New-08: ストリーク（連続ログインボーナス）
# ============================================================

@router.post("/users/{user_id}/checkin")
async def daily_checkin(user_id: str, db: AsyncSession = Depends(get_db)):
    """ログイン時に呼び出す。連続ログインボーナスを付与する。"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 既にチェックイン済み
    if getattr(user, "last_login_date", None) == today:
        return {
            "status": "already_checked_in",
            "streak": user.login_streak or 0,
            "likes_balance": user.likes_balance or 10,
        }

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    if getattr(user, "last_login_date", None) == yesterday:
        user.login_streak = (user.login_streak or 0) + 1
    else:
        user.login_streak = 1

    user.last_login_date = today

    streak = user.login_streak
    if streak >= 30:
        bonus_likes = 10
    elif streak >= 14:
        bonus_likes = 5
    elif streak >= 7:
        bonus_likes = 3
    else:
        bonus_likes = 1

    user.likes_balance = (user.likes_balance or 10) + bonus_likes
    await db.commit()

    return {
        "status": "checked_in",
        "streak": streak,
        "bonus_likes": bonus_likes,
        "likes_balance": user.likes_balance,
        "message": f"🔥 {streak}日連続ログイン！いいね{bonus_likes}枚GET！",
        "milestone": streak in [7, 14, 30, 60, 100],
    }


# ============================================================
# New-03: シミュレーション結果シェアカード
# ============================================================

@router.get("/share-card/{simulation_id}")
async def get_share_card(simulation_id: str, db: AsyncSession = Depends(get_db)):
    """シミュレーション結果のシェアカード画像を生成（Pillow使用）"""
    from models import SimulationResult

    sim = await db.get(SimulationResult, simulation_id)
    if not sim:
        raise HTTPException(404, "Simulation not found")

    score = int(sim.compatibility_score or 0)

    if score >= 80:
        color_hex = "#63e6be"
        label = "高相性！"
        emoji = "💚"
    elif score >= 60:
        color_hex = "#ffd43b"
        label = "まずまず"
        emoji = "💛"
    else:
        color_hex = "#ff6b6b"
        label = "課題あり"
        emoji = "❤️"

    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (600, 315), color=(13, 13, 26))
        draw = ImageDraw.Draw(img)

        # グラデーション背景（簡易）
        for i in range(315):
            v = 13 + int(i / 315 * 20)
            draw.line([(0, i), (600, i)], fill=(v, v, v + 20))

        # カラー変換
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)

        draw.text((300, 60),  "Persona AI相性診断",   fill=(255, 255, 255), anchor="mm")
        draw.text((300, 130), f"{emoji} 相性スコア",  fill=(170, 170, 170), anchor="mm")
        draw.text((300, 200), f"{score}%",             fill=(r, g, b),       anchor="mm")
        draw.text((300, 270), "AI本人確認マッチング | Persona", fill=(100, 100, 100), anchor="mm")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        return {
            "image_base64": f"data:image/png;base64,{img_b64}",
            "score": score,
            "share_text": f"AIが私の相性を診断したら{score}%でした✨ #Persona #AI婚活",
            "share_url": "https://persona-app.jp/",
        }
    except ImportError:
        # Pillow未インストールの場合はテキストレスポンス
        return {
            "image_base64": None,
            "score": score,
            "share_text": f"AIが私の相性を診断したら{score}%でした✨ #Persona #AI婚活",
            "share_url": "https://persona-app.jp/",
        }


# ============================================================
# New-05: プッシュ通知トークン登録
# ============================================================

class PushTokenRequest(BaseModel):
    user_id: str
    token: str
    platform: str = "web"


@router.post("/push/register")
async def register_push_token(payload: PushTokenRequest, db: AsyncSession = Depends(get_db)):
    """FCMプッシュ通知トークンを登録する"""
    from models import PushToken

    token_entry = PushToken(
        user_id=payload.user_id,
        token=payload.token,
        platform=payload.platform,
    )
    db.add(token_entry)
    await db.commit()
    return {"status": "registered", "message": "プッシュ通知を有効化しました"}


# ============================================================
# New-07: ヘルススコア手動取得（デバッグ用）
# ============================================================

@router.get("/users/{user_id}/health-score")
async def get_user_health_score(user_id: str, db: AsyncSession = Depends(get_db)):
    """ユーザーのヘルススコアを取得する"""
    from health_score import calculate_health_score, get_health_segment

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    updated_at = getattr(user, "updated_at", None) or getattr(user, "created_at", None)
    from datetime import datetime, timezone
    days_ago = (datetime.now(timezone.utc) - updated_at).days if updated_at else 99

    activity = {
        "last_login_days_ago": days_ago,
        "likes_sent_7d": 0,
        "chat_reply_rate": 0.5,
        "simulation_count_7d": 0,
        "is_paying": False,
    }

    score = calculate_health_score(user, activity)
    segment = get_health_segment(score)

    return {
        "user_id": user_id,
        "health_score": score,
        "segment": segment,
        "days_since_activity": days_ago,
        "intervention": {
            "healthy":  "介入不要",
            "at_risk":  "リマインドプッシュ通知",
            "critical": "強い介入（特別オファー）",
            "churning": "解約防止オファー",
        }.get(segment, "不明"),
    }


# ============================================================
# AUTO-03: KPIサマリーAPI（管理画面 / n8n用）
# ============================================================

def _health_grade(score: int) -> str:
    """ヘルススコアをグレード文字列に変換する"""
    if score >= 85:
        return "S"
    elif score >= 70:
        return "A"
    elif score >= 55:
        return "B"
    elif score >= 40:
        return "C"
    return "D"


@router.get("/admin/kpi-summary")
async def get_kpi_summary(db: AsyncSession = Depends(get_db)):
    """
    KPIサマリーを一括取得するエンドポイント。
    n8nや管理画面からの定期取得を想定。認証不要（内部利用）。
    """
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    # --- ユーザー統計 ---
    total_users_q = await db.execute(select(func.count(User.id)))
    total_users = total_users_q.scalar() or 0

    verified_users_q = await db.execute(
        select(func.count(User.id)).where(User.is_verified == True)
    )
    verified_users = verified_users_q.scalar() or 0

    verification_rate = round(verified_users / max(total_users, 1) * 100, 1)

    # --- ウェイティングリスト統計 ---
    total_waitlist_q = await db.execute(select(func.count(WaitlistEntry.id)))
    total_waitlist = total_waitlist_q.scalar() or 0

    female_waitlist_q = await db.execute(
        select(func.count(WaitlistEntry.id)).where(WaitlistEntry.gender == "female")
    )
    female_waitlist = female_waitlist_q.scalar() or 0
    male_waitlist = total_waitlist - female_waitlist
    female_ratio = round(female_waitlist / max(total_waitlist, 1) * 100, 1)

    # --- エンゲージメント統計 ---
    sim_total_q = await db.execute(select(func.count(SimulationResult.id)))
    simulations_total = sim_total_q.scalar() or 0

    sim_7d_q = await db.execute(
        select(func.count(SimulationResult.id)).where(
            SimulationResult.created_at >= seven_days_ago
        )
    )
    simulations_7d = sim_7d_q.scalar() or 0

    avg_score_q = await db.execute(
        select(func.avg(SimulationResult.compatibility_score))
    )
    avg_compatibility_score = round(avg_score_q.scalar() or 0, 1)

    fatal_count_q = await db.execute(
        select(func.count(SimulationResult.id)).where(
            SimulationResult.fatal_flaw_detected == True
        )
    )
    fatal_count = fatal_count_q.scalar() or 0
    fatal_flaw_rate = round(fatal_count / max(simulations_total, 1) * 100, 1)

    matches_total_q = await db.execute(select(func.count(Match.id)))
    matches_total = matches_total_q.scalar() or 0

    messages_total_q = await db.execute(select(func.count(Message.id)))
    messages_total = messages_total_q.scalar() or 0

    # --- ヘルススコア ---
    # DAU/MAU比率（簡易推定: 直近1日ログインユーザー / 直近30日ログインユーザー）
    today_str = now.strftime("%Y-%m-%d")
    dau_q = await db.execute(
        select(func.count(User.id)).where(User.last_login_date == today_str)
    )
    dau = dau_q.scalar() or 0

    thirty_days_ago = now - timedelta(days=30)
    thirty_days_dates = [
        (now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)
    ]
    # MAU: last_login_dateがここ30日以内のユーザー数
    mau_q = await db.execute(
        select(func.count(User.id)).where(User.last_login_date.in_(thirty_days_dates))
    )
    mau = mau_q.scalar() or 0

    dau_mau_ratio = round(dau / max(mau, 1), 2)

    # マッチ率（マッチ数 / シミュレーション数）
    match_rate = round(matches_total / max(simulations_total, 1) * 100, 1)

    # チャットアクティブ率（メッセージ送信ユーザー数 / マッチ済みユーザー数の簡易推定）
    chat_senders_q = await db.execute(
        select(func.count(func.distinct(Message.sender_id)))
    )
    chat_senders = chat_senders_q.scalar() or 0
    # マッチに関わるユニークユーザー数
    match_users_a_q = await db.execute(
        select(func.count(func.distinct(Match.user_a_id)))
    )
    match_users_b_q = await db.execute(
        select(func.count(func.distinct(Match.user_b_id)))
    )
    match_users_approx = max(
        (match_users_a_q.scalar() or 0) + (match_users_b_q.scalar() or 0), 1
    )
    chat_active_rate = round(chat_senders / match_users_approx * 100, 1)

    # 総合ヘルススコア（4指標の加重平均）
    health_score = round(
        dau_mau_ratio * 100 * 0.3
        + verification_rate * 0.2
        + match_rate * 0.25
        + chat_active_rate * 0.25,
        0,
    )
    health_score = int(min(health_score, 100))
    health_grade = _health_grade(health_score)

    # --- SNS統計（プレースホルダー: 将来SNS投稿テーブル追加時に実データに差し替え） ---
    sns_last_post_date = now.strftime("%Y-%m-%d")
    sns_posts_this_week = 0

    return {
        "timestamp": now.isoformat(timespec="seconds"),
        "users": {
            "total": total_users,
            "verified": verified_users,
            "verification_rate": verification_rate,
        },
        "waitlist": {
            "total": total_waitlist,
            "female": female_waitlist,
            "male": male_waitlist,
            "female_ratio": female_ratio,
        },
        "engagement": {
            "simulations_total": simulations_total,
            "simulations_7d": simulations_7d,
            "avg_compatibility_score": avg_compatibility_score,
            "fatal_flaw_rate": fatal_flaw_rate,
            "matches_total": matches_total,
            "messages_total": messages_total,
        },
        "health": {
            "grade": health_grade,
            "score": health_score,
            "details": {
                "dau_mau_ratio": dau_mau_ratio,
                "verification_rate": verification_rate,
                "match_rate": match_rate,
                "chat_active_rate": chat_active_rate,
            },
        },
        "sns": {
            "last_post_date": sns_last_post_date,
            "posts_this_week": sns_posts_this_week,
        },
    }


# ============================================================
# New-09: デートプランAI提案
# ============================================================

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


class DatePlanRequest(BaseModel):
    """デートプラン提案リクエスト"""
    user_a_id: str
    user_b_id: str
    simulation_id: str = ""   # オプション: 特定のシミュレーション結果を参照
    budget: str = "普通"      # 節約 / 普通 / リッチ
    area: str = ""            # デートエリア（空なら user_a の location を使う）


def _build_fallback_plans(area: str, budget: str) -> dict:
    """Gemini APIが使えない場合のフォールバックテンプレートプラン"""
    return {
        "plans": [
            {
                "title": f"{area or '都内'}カフェ巡り＆散歩デート",
                "description": "おしゃれなカフェを2〜3軒巡りながら、ゆったり会話を楽しむプラン。"
                                "歩きながら自然と距離が縮まります。",
                "duration": "3-4時間",
                "budget": "¥2,000-4,000" if budget == "節約" else "¥3,000-5,000",
                "rating": 4,
                "reason": "初デートにぴったり。カフェなら会話に集中でき、お互いを深く知れます。",
            },
            {
                "title": f"{area or '都内'}美術館＆ランチデート",
                "description": "話題の展覧会を観た後、近くのレストランでランチ。"
                                "アートの感想がそのまま会話のネタになります。",
                "duration": "4-5時間",
                "budget": "¥4,000-7,000" if budget != "リッチ" else "¥8,000-12,000",
                "rating": 4,
                "reason": "共通の体験が話題を生み、沈黙を気にせず楽しめます。",
            },
            {
                "title": f"{area or '都内'}夜景ディナーデート",
                "description": "眺望の良いレストランでディナー。"
                                "夜景をバックにロマンチックな雰囲気を演出。",
                "duration": "2-3時間",
                "budget": "¥5,000-8,000" if budget != "リッチ" else "¥10,000-20,000",
                "rating": 5,
                "reason": "特別感があり、二人の関係を一歩進めるのに最適です。",
            },
        ],
        "conversation_starters": [
            "最近ハマっていることはありますか？",
            "休日はどんな過ごし方が多いですか？",
            "今年中にやりたいことってありますか？",
        ],
        "compatibility_note": "お二人に合わせたプランをご提案しました。リラックスして楽しんでください！",
    }


@router.post("/date-plan/suggest")
async def suggest_date_plan(
    payload: DatePlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """マッチしたペアにAIが最適なデートプランを提案する"""

    # --- 1. ユーザープロフィール取得 ---
    user_a = await db.get(User, payload.user_a_id)
    if not user_a:
        raise HTTPException(404, f"User not found: {payload.user_a_id}")

    user_b = await db.get(User, payload.user_b_id)
    if not user_b:
        raise HTTPException(404, f"User not found: {payload.user_b_id}")

    # --- 2. シミュレーション結果取得（オプション）---
    sim_info = ""
    if payload.simulation_id:
        sim = await db.get(SimulationResult, payload.simulation_id)
        if sim:
            sim_info = (
                f"相性スコア: {sim.compatibility_score}点\n"
                f"詳細: {json.dumps(sim.breakdown_json, ensure_ascii=False) if sim.breakdown_json else 'なし'}"
            )

    # エリア決定（リクエスト > user_a.location > デフォルト）
    area = payload.area or (user_a.location if user_a.location else "東京")

    # --- 3. Gemini API でデートプラン生成 ---
    if not GOOGLE_API_KEY:
        # APIキー未設定 → フォールバック
        return _build_fallback_plans(area, payload.budget)

    prompt = f"""あなたはデートプランナーAIです。
以下の二人のプロフィールと条件をもとに、最適なデートプラン3つを提案してください。

【Aさんのプロフィール】
- 名前: {user_a.name or '未設定'}
- MBTI: {user_a.mbti or '未診断'}
- 年齢: {user_a.age or '未設定'}
- 趣味: {user_a.hobbies or '未設定'}
- エリア: {user_a.location or '未設定'}
- 職業: {user_a.job or '未設定'}

【Bさんのプロフィール】
- 名前: {user_b.name or '未設定'}
- MBTI: {user_b.mbti or '未診断'}
- 年齢: {user_b.age or '未設定'}
- 趣味: {user_b.hobbies or '未設定'}
- エリア: {user_b.location or '未設定'}
- 職業: {user_b.job or '未設定'}

【条件】
- 予算レベル: {payload.budget}
- デートエリア: {area}
{f'【相性診断結果】{chr(10)}{sim_info}' if sim_info else ''}

以下のJSON形式で回答してください:
- plans: 3つのデートプラン（title, description, duration, budget, rating[1-5], reason）
- conversation_starters: 会話のきっかけになるトピック3つ
- compatibility_note: 二人の相性に基づくコメント
"""

    # Gemini APIのレスポンススキーマ定義
    response_schema = {
        "type": "object",
        "properties": {
            "plans": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "duration": {"type": "string"},
                        "budget": {"type": "string"},
                        "rating": {"type": "integer"},
                        "reason": {"type": "string"},
                    },
                    "required": ["title", "description", "duration", "budget", "rating", "reason"],
                },
            },
            "conversation_starters": {
                "type": "array",
                "items": {"type": "string"},
            },
            "compatibility_note": {"type": "string"},
        },
        "required": ["plans", "conversation_starters", "compatibility_note"],
    }

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GEMINI_URL}?key={GOOGLE_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.8,
                        "maxOutputTokens": 2048,
                        "responseMimeType": "application/json",
                        "responseSchema": response_schema,
                    },
                },
            ) as resp:
                data = await resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(text)
                return result
    except Exception:
        # Gemini APIエラー → フォールバック
        return _build_fallback_plans(area, payload.budget)


# ============================================================
# New-10: コミュニティ / 趣味タグ機能
# ============================================================

@router.get("/tags")
async def list_tags(db: AsyncSession = Depends(get_db)):
    """全趣味タグ一覧を返す"""
    result = await db.execute(select(HobbyTag).order_by(HobbyTag.category, HobbyTag.name))
    tags = result.scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "category": t.category,
            "icon": t.icon,
        }
        for t in tags
    ]


class SetTagsRequest(BaseModel):
    """ユーザーへのタグ設定リクエスト（最大10個）"""
    tag_ids: List[str]


@router.post("/users/{user_id}/tags")
async def set_user_tags(
    user_id: str,
    payload: SetTagsRequest,
    db: AsyncSession = Depends(get_db),
):
    """ユーザーにタグを設定する（既存タグをリセットして上書き・最大10個）"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # 最大10個に制限
    tag_ids = payload.tag_ids[:10]

    # 既存のユーザータグを全削除
    existing = await db.execute(
        select(UserHobbyTag).where(UserHobbyTag.user_id == user_id)
    )
    for row in existing.scalars().all():
        await db.delete(row)

    # 新しいタグを登録
    added = []
    for tid in tag_ids:
        tag = await db.get(HobbyTag, tid)
        if tag:
            db.add(UserHobbyTag(user_id=user_id, tag_id=tid))
            added.append({"id": tag.id, "name": tag.name, "icon": tag.icon})

    await db.commit()
    return {"status": "updated", "tags": added, "count": len(added)}


@router.get("/users/{user_id}/tags")
async def get_user_tags(user_id: str, db: AsyncSession = Depends(get_db)):
    """ユーザーに紐づくタグ一覧を返す"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    result = await db.execute(
        select(HobbyTag)
        .join(UserHobbyTag, UserHobbyTag.tag_id == HobbyTag.id)
        .where(UserHobbyTag.user_id == user_id)
    )
    tags = result.scalars().all()
    return [
        {"id": t.id, "name": t.name, "category": t.category, "icon": t.icon}
        for t in tags
    ]


@router.get("/tags/{tag_id}/users")
async def get_tag_users(tag_id: str, db: AsyncSession = Depends(get_db)):
    """特定タグを持つユーザー一覧を返す（コミュニティ発見用）"""
    tag = await db.get(HobbyTag, tag_id)
    if not tag:
        raise HTTPException(404, "Tag not found")

    result = await db.execute(
        select(User)
        .join(UserHobbyTag, UserHobbyTag.user_id == User.id)
        .where(UserHobbyTag.tag_id == tag_id)
    )
    users = result.scalars().all()
    return {
        "tag": {"id": tag.id, "name": tag.name, "category": tag.category, "icon": tag.icon},
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "age": u.age,
                "mbti": u.mbti,
                "location": u.location,
                "profile_image_url": u.profile_image_url,
                "is_verified": u.is_verified or False,
            }
            for u in users
        ],
        "count": len(users),
    }
