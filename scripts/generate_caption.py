"""
generate_caption.py — Gemini Flash SNSキャプション生成（Phase 1）
コスト: ¥0（1日1,500リクエストまで無料枠）

使い方:
  python generate_caption.py  # 3本一括生成
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)

# Personaブランド専用プロンプト
PERSONA_SYSTEM_PROMPT = """あなたはPersonaというAIマッチングアプリのSNSマーケティング担当です。

【Personaの強み・差別化ポイント】
1. AIが代理で会話して相性チェック（3フェーズ・18メッセージのシミュレーション）
2. AI本人確認済みバッジ（セルフィー認証）
3. 15問の価値観診断テスト
4. MBTI連携
5. 審査制で質の高いユーザーが集まる

【ターゲット】
- 真剣な出会いを求める20〜35歳の日本人男女
- 外見より中身・価値観で相手を選びたい人
- AIが好きな人・テクノロジーに関心がある人

【NGワード】
- 過度な宣伝・保証・確約を匂わせる表現
- 他社の批判

【投稿スタイル】
- 共感を呼ぶストーリー形式
- データ・事実に基づいた訴求
- 適度なユーモア
- ハッシュタグ5〜7個（#Persona #AI婚活 #価値観マッチング など）
"""

SNS_TYPE_SPECS = {
    "x": {
        "max_chars": 140,
        "style": "短く鋭く。改行少なめ。ハッシュタグ3個まで。",
    },
    "instagram": {
        "max_chars": 300,
        "style": "絵文字を使って読みやすく。改行多め。ハッシュタグ7個。",
    },
    "tiktok": {
        "max_chars": 100,
        "style": "最初の一文でフックを作る。テンポよく。",
    },
}

# 週次テーマカレンダー
WEEKLY_THEMES = {
    0: ("月曜", "AIシミュレーション機能", "feature_intro"),
    1: ("火曜", "本人確認バッジの安心感", "user_story"),
    2: ("水曜", "価値観診断テスト", "feature_intro"),
    3: ("木曜", "AI婚活の最新トレンド", "data_fact"),
    4: ("金曜", "Personaで出会いのコツ", "general"),
    5: ("土曜", "週末の特別企画", "general"),
    6: ("日曜", "来週の出会いに向けて", "general"),
}


async def generate_caption(
    theme: str,
    sns_type: str = "instagram",
    content_type: str = "general",
) -> dict:
    """
    Persona向けSNSキャプションを生成する。

    Returns: {caption, image_prompt, hashtags, hook, sns_type, theme}
    """
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY が .env に設定されていません")

    spec = SNS_TYPE_SPECS.get(sns_type, SNS_TYPE_SPECS["instagram"])

    content_type_instruction = {
        "general": "一般的なマッチングアプリの悩みに共感して、Personaが解決策になることを伝える",
        "feature_intro": f"Personaの特定機能を紹介する。機能名: {theme}",
        "user_story": "架空のユーザーエピソードを使ってPersonaの価値を伝える（実際の体験談ではないことが分かるように）",
        "data_fact": "AI・マッチングアプリに関するデータや事実から入り、Personaに繋げる",
    }.get(content_type, "")

    prompt = f"""{PERSONA_SYSTEM_PROMPT}

今日のテーマ: {theme}
SNSタイプ: {sns_type}（最大{spec['max_chars']}文字）
スタイル指示: {spec['style']}
コンテンツ種別: {content_type_instruction}

以下のJSON形式で出力してください（コードブロックなし）:
{{
  "caption": "投稿文（{spec['max_chars']}文字以内）",
  "image_prompt": "この投稿に合う画像の英語プロンプト（Imagen 4向け）",
  "hashtags": ["ハッシュタグ1", "ハッシュタグ2"],
  "hook": "最初の一文（フック）"
}}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "caption": {"type": "STRING"},
                    "image_prompt": {"type": "STRING"},
                    "hashtags": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    },
                    "hook": {"type": "STRING"}
                },
                "required": ["caption", "image_prompt", "hashtags", "hook"]
            }
        },
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{GEMINI_API_URL}?key={GOOGLE_API_KEY}",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                raise ValueError(f"Gemini API エラー: {await resp.text()}")

            data = await resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Remove markdown code blocks if any
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            try:
                result = json.loads(text)
            except json.JSONDecodeError as e:
                print(f"--- JSON Parse Error ---")
                print(f"Raw Text: {repr(text)}")
                print(f"------------------------")
                raise e
            
            result["sns_type"] = sns_type
            result["theme"] = theme
            return result


async def generate_daily_posts(themes: list | None = None) -> list:
    """1日分の投稿案（3本）を一括生成する"""
    import datetime
    today = datetime.datetime.now().weekday()
    day_info = WEEKLY_THEMES.get(today, ("", "一般投稿", "general"))

    if themes is None:
        themes = [day_info[1]] * 3

    tasks = [
        generate_caption(themes[0], "x", day_info[2]),
        generate_caption(themes[1], "instagram", "user_story"),
        generate_caption(themes[2], "tiktok", "data_fact"),
    ]

    results = await asyncio.gather(*tasks)

    print(f"\n📝 本日の投稿案（{len(results)}本）生成完了")
    for i, post in enumerate(results, 1):
        print(f"\n【投稿{i}】{post['sns_type'].upper()}")
        print(f"フック: {post.get('hook', '')}")
        print(f"文字数: {len(post['caption'])}文字")

    return results


if __name__ == "__main__":
    asyncio.run(generate_daily_posts())
