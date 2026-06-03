"""
generate_image_phase1.py — Imagen 4 Fast画像生成スクリプト（Phase 1）
コスト: ¥0（1日1,500枚まで無料枠）

使い方:
  python generate_image_phase1.py "couple at a cafe, warm lighting" output.png
  python generate_image_phase1.py "couple at a cafe" output.png 9:16
"""

import asyncio
import aiohttp
import base64
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
IMAGEN_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/imagen-4.0-fast-generate-preview-06-06:predict"
)


async def generate_image_imagen4(
    prompt: str,
    output_path: str = "output.png",
    aspect_ratio: str = "1:1",
    retries: int = 3,
) -> str:
    """
    Google Imagen 4 FastでSNS用画像を生成する（非同期・エラーハンドリング付き）

    Args:
        prompt: 英語の画像生成プロンプト
        output_path: 保存先パス
        aspect_ratio: "1:1"(正方形) / "9:16"(縦型) / "16:9"(横型)
        retries: 失敗時のリトライ回数

    Returns:
        保存した画像のパス
    """
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY が .env に設定されていません")

    # Persona向けの共通スタイル指示を追加
    enhanced_prompt = (
        f"{prompt}, "
        "dating app marketing style, "
        "warm romantic atmosphere, "
        "modern japanese aesthetic, "
        "professional photography, "
        "vibrant colors, "
        "no text overlay"
    )

    payload = {
        "instances": [{"prompt": enhanced_prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "safetyFilterLevel": "BLOCK_MEDIUM_AND_ABOVE",
            "personGeneration": "ALLOW_ADULT",
        },
    }

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{IMAGEN_API_URL}?key={GOOGLE_API_KEY}",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:

                    if resp.status == 429:
                        print(f"⏳ レート制限。60秒後にリトライ... ({attempt+1}/{retries})")
                        await asyncio.sleep(60)
                        continue

                    if resp.status != 200:
                        error = await resp.text()
                        raise ValueError(f"API エラー {resp.status}: {error}")

                    data = await resp.json()

                    img_b64 = data["predictions"][0]["bytesBase64Encoded"]
                    img_bytes = base64.b64decode(img_b64)

                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(img_bytes)

                    print(f"✅ 画像生成完了: {output_path} ({len(img_bytes)//1024}KB)")
                    return output_path

        except asyncio.TimeoutError:
            print(f"⚠️ タイムアウト ({attempt+1}/{retries})")
            if attempt == retries - 1:
                raise
            await asyncio.sleep(10)

    raise RuntimeError("画像生成に失敗しました")


async def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "couple meeting at a cafe, warm lighting"
    output = sys.argv[2] if len(sys.argv) > 2 else "tmp/output.png"
    aspect = sys.argv[3] if len(sys.argv) > 3 else "1:1"
    await generate_image_imagen4(prompt, output, aspect)


if __name__ == "__main__":
    asyncio.run(main())
