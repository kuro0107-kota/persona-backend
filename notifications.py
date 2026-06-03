"""
notifications.py — プッシュ通知システム（New-05）
Firebase FCM (v1 API) 経由でユーザーにプッシュ通知を送信する。
サービスアカウントJSONまたはプロジェクトIDが未設定の場合はサイレントスキップ。
"""
from __future__ import annotations
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import firebase_admin
from firebase_admin import credentials, messaging

# Firebase SDKの初期化
firebase_initialized = False
try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    service_account_path = os.path.join(base_dir, "firebase-service-account.json")
    
    if os.path.exists(service_account_path) and os.environ.get("FIREBASE_PROJECT_ID"):
        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        firebase_initialized = True
except Exception as e:
    print(f"[Firebase Init Failed] {e}")

# 通知テンプレート
NOTIFICATION_TEMPLATES: dict[str, dict[str, str]] = {
    "new_match": {
        "title": "🎉 新しいマッチが成立しました！",
        "body": "AIが相性を確認しました。今すぐチェックしてください。",
    },
    "high_score": {
        "title": "💚 AIが高相性な相手を発見しました",
        "body": "相性スコア{score}%の相手がいます！",
    },
    "health_risk": {
        "title": "Personaからお知らせ",
        "body": "最近、出会いはありましたか？AIコンシェルジュに相談してみませんか。",
    },
    "referral_bonus": {
        "title": "🎁 招待ボーナスが付与されました！",
        "body": "いいね{count}枚をプレゼント！今すぐ使ってみてください。",
    },
    "message_received": {
        "title": "💬 新しいメッセージが届きました",
        "body": "{sender_name}さんからメッセージが届いています。",
    },
    "streak_milestone": {
        "title": "🔥 {streak}日連続ログイン達成！",
        "body": "いいねボーナスをGETしました。このまま続けて素敵な出会いを見つけてください！",
    },
    "simulation_ready": {
        "title": "✨ AIシミュレーション結果が届きました",
        "body": "相手との相性スコアをチェックしてください。",
    },
}


async def send_push_notification(
    user_id: str,
    notification_type: str,
    data: dict | None = None,
    db: AsyncSession | None = None,
) -> bool:
    """
    指定ユーザーにプッシュ通知を送信する。
    Firebaseが初期化されていない、またはDBなしの場合はスキップ。
    """
    if not firebase_initialized or not db:
        return False

    from models import PushToken

    tokens_result = await db.execute(
        select(PushToken).where(PushToken.user_id == user_id)
    )
    tokens = tokens_result.scalars().all()

    if not tokens:
        return False

    template = NOTIFICATION_TEMPLATES.get(notification_type, {})
    title = template.get("title", "Personaからのお知らせ")
    try:
        body = template.get("body", "").format(**(data or {}))
    except (KeyError, ValueError):
        body = template.get("body", "")

    # FCM v1 API向けにdataの全値を文字列に変換
    data_payload: dict[str, str] = {}
    if data:
        for k, v in data.items():
            data_payload[str(k)] = str(v)

    success = False
    for token_entry in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data_payload,
                token=token_entry.token
            )
            # 送信実行 (同期処理のためブロッキングを避ける必要があれば非同期でラップ)
            messaging.send(message)
            success = True
        except Exception as e:
            print(f"[FCM Send Failed] token: {token_entry.token}, error: {e}")

    return success


async def send_bulk_push(
    user_ids: list[str],
    notification_type: str,
    data: dict | None = None,
    db: AsyncSession | None = None,
) -> int:
    """複数ユーザーへ一括通知。送信成功件数を返す。"""
    count = 0
    for uid in user_ids:
        if await send_push_notification(uid, notification_type, data, db):
            count += 1
    return count

