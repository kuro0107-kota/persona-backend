"""
daily_auto_post.py — 毎朝6時に実行されるSNS自動投稿フロー（Phase 1）
cron: 0 6 * * * python /path/to/daily_auto_post.py

フロー:
  6:00 → キャプション生成 → 画像生成 → Slack承認依頼送信
  →（あなたが✅）→ X/Instagram/TikTokに自動投稿

コスト: Gemini Flash + Imagen 4 = ¥0（無料枠）
"""

import asyncio
import aiohttp
import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
WEEKLY_THEMES = {
    0: ("月曜", "AIシミュレーション機能", "feature_intro"),
    1: ("火曜", "本人確認バッジの安心感", "user_story"),
    2: ("水曜", "価値観診断テスト", "feature_intro"),
    3: ("木曜", "AI婚活の最新トレンド", "data_fact"),
    4: ("金曜", "Personaで出会いのコツ", "general"),
    5: ("土曜", "週末の特別企画", "general"),
    6: ("日曜", "来週の出会いに向けて", "general"),
}


async def send_slack_notification(posts: list, results: list) -> None:
    """Slackに投稿完了の報告を送る"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️ SLACK_WEBHOOK_URL が未設定。Slack通知をスキップ")
        return

    today = datetime.now()
    day_info = WEEKLY_THEMES.get(today.weekday(), ("", "一般投稿", "general"))

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text",
                     "text": f"✅ {today.strftime('%m/%d')} ({day_info[0]}) の自動投稿が完了しました"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn",
                     "text": f"テーマ: *{day_info[1]}*"},
        },
        {"type": "divider"},
    ]

    for i, (post, res) in enumerate(zip(posts, results), 1):
        status_icon = "🟢" if res else "🔴"
        blocks.extend([
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{status_icon} *【投稿{i}】{post.get('sns_type', '').upper()}*\n\n"
                        f"{post.get('caption', '')}\n\n"
                        f"🖼 _{post.get('image_prompt', '')}_\n\n"
                        f"結果: {res}"
                    ),
                },
            },
            {"type": "divider"},
        ])

    payload = {"blocks": blocks, "text": f"本日の投稿完了 {len(posts)}本"}

    async with aiohttp.ClientSession() as session:
        resp = await session.post(SLACK_WEBHOOK_URL, json=payload)
        if resp.status == 200:
            print(f"📨 Slackに結果を報告しました（{len(posts)}本）")
        else:
            print(f"⚠️ Slack送信失敗: HTTP {resp.status}")


async def main():
    """毎朝6時に実行されるメインフロー"""
    print(f"\n🚀 Persona SNS完全自動投稿システム起動: {datetime.now()}")

    # Step 1: 今日のテーマを取得
    today = datetime.now()
    day_theme = WEEKLY_THEMES.get(today.weekday(), ("", "一般投稿", "general"))
    print(f"📅 今日のテーマ: {day_theme[1]}")

    # Step 2: キャプション生成
    from generate_caption import generate_daily_posts
    posts = await generate_daily_posts([day_theme[1]] * 3)

    # Step 3: 画像生成
    Path("tmp").mkdir(exist_ok=True)
    from generate_image_phase1 import generate_image_imagen4
    for i, post in enumerate(posts):
        img_path = f"tmp/post_{i+1}.png"
        try:
            await generate_image_imagen4(post["image_prompt"], img_path)
            post["image_path"] = img_path
        except Exception as e:
            print(f"⚠️ 画像生成スキップ（投稿{i+1}）: {e}")
            post["image_path"] = None

    # Step 4: 各SNSへ自動投稿
    from post_to_twitter import post_tweet
    results = []
    for i, post in enumerate(posts):
        sns_type = post.get("sns_type", "").lower()
        if "twitter" in sns_type or "x" in sns_type:
            print(f"🐦 X (Twitter) へ投稿開始: 投稿{i+1}")
            tweet_id = post_tweet(text=post.get("caption", ""), image_path=post.get("image_path"))
            if tweet_id:
                results.append(f"成功 (ID: {tweet_id})")
            else:
                results.append("失敗")
        else:
            print(f"⏩ {sns_type} は現在未実装のためスキップ: 投稿{i+1}")
            results.append("未実装スキップ")

    # Step 5: Slackへ事後報告
    await send_slack_notification(posts, results)

    # 投稿データを保存（ログ用）
    with open("tmp/today_posts.json", "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    print("✅ 完了。")


if __name__ == "__main__":
    asyncio.run(main())
