import asyncio
import os
from database import engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# .envの読み込み
load_dotenv()

async def main():
    # notifications.pyのインポート
    import notifications
    print("Firebase Initialized State:", notifications.firebase_initialized)
    
    # データベースセッション作成
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        # トークンがない状態での動作検証
        res = await notifications.send_push_notification(
            user_id="non_existent_user_id",
            notification_type="new_match",
            db=session
        )
        print("Notification Send Test (Expected False for non-existent token):", res)

if __name__ == "__main__":
    asyncio.run(main())
