"""
seed_hobby_tags.py — 趣味タグの初期データ投入スクリプト

使い方:
  cd backend
  python scripts/seed_hobby_tags.py

既存のタグは重複スキップ（name が UNIQUE のため）。
テーブルが存在しない場合は CREATE TABLE IF NOT EXISTS で自動作成。
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime, timezone

# backend ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from database import AsyncSessionLocal, engine

# 初期タグデータ: (name, category, icon)
TAGS = [
    ("カフェ巡り", "グルメ", "☕"), ("料理", "グルメ", "🍳"), ("ワイン", "グルメ", "🍷"),
    ("映画鑑賞", "インドア", "🎬"), ("読書", "インドア", "📚"), ("ゲーム", "インドア", "🎮"),
    ("音楽", "インドア", "🎵"), ("アニメ", "インドア", "🎌"),
    ("キャンプ", "アウトドア", "⛺"), ("旅行", "アウトドア", "✈️"), ("登山", "アウトドア", "🏔️"),
    ("ランニング", "スポーツ", "🏃"), ("ヨガ", "スポーツ", "🧘"), ("筋トレ", "スポーツ", "💪"),
    ("サウナ", "リラクゼーション", "🧖"), ("温泉", "リラクゼーション", "♨️"),
    ("写真", "クリエイティブ", "📸"), ("アート", "クリエイティブ", "🎨"),
    ("テクノロジー", "学び", "💻"), ("心理学", "学び", "🧠"),
    ("ペット", "ライフスタイル", "🐶"), ("ドライブ", "ライフスタイル", "🚗"),
    ("ファッション", "ライフスタイル", "👗"), ("お酒", "グルメ", "🍺"),
]


async def main():
    """テーブル作成 → シードデータ投入"""

    # --- テーブル作成（既存DBの場合に備えて直接SQL実行）---
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS hobby_tags (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE,
                category VARCHAR(30),
                icon VARCHAR(10),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_hobby_tags (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(50) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                tag_id VARCHAR(36) NOT NULL REFERENCES hobby_tags(id) ON DELETE CASCADE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))

    # --- シードデータ投入 ---
    async with AsyncSessionLocal() as session:
        inserted = 0
        skipped = 0

        for name, category, icon in TAGS:
            # 重複チェック（name が UNIQUE）
            result = await session.execute(
                text("SELECT id FROM hobby_tags WHERE name = :name"),
                {"name": name},
            )
            if result.fetchone():
                skipped += 1
                continue

            tag_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            await session.execute(
                text(
                    "INSERT INTO hobby_tags (id, name, category, icon, created_at) "
                    "VALUES (:id, :name, :category, :icon, :created_at)"
                ),
                {
                    "id": tag_id,
                    "name": name,
                    "category": category,
                    "icon": icon,
                    "created_at": now,
                },
            )
            inserted += 1

        await session.commit()

    print(f"✅ シード完了: {inserted}件追加 / {skipped}件スキップ（既存）")
    print(f"   合計タグ数: {inserted + skipped}")


if __name__ == "__main__":
    asyncio.run(main())
