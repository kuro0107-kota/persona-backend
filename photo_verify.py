"""
photo_verify.py
セルフィー認証モジュール
- Gemini Vision APIを使って「提出写真」と「セルフィー」が同一人物かをAI判定する
- APIキーがない場合や呼び出し失敗時は、モック結果を返す（デモモード）
"""

import os
import base64
import httpx
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


async def verify_same_person(selfie_base64: str, profile_image_url: str) -> dict:
    """
    Parameters
    ----------
    selfie_base64  : カメラで撮影したセルフィー画像をBase64エンコードした文字列
    profile_image_url : 登録済みプロフィール写真のURL

    Returns
    -------
    dict:
        {
            "verified": bool,       # 同一人物と判定されたか
            "confidence": float,    # 確信度 0.0〜1.0
            "message": str          # AIからのコメント（日本語）
        }
    """
    if not GEMINI_API_KEY:
        # デモモード: APIキーなしでもUIが動くように擬似結果を返す
        return _mock_verify(selfie_base64)

    try:
        # プロフィール写真をURLから取得してBase64化
        async with httpx.AsyncClient(timeout=15.0) as client:
            img_resp = await client.get(profile_image_url)
            img_resp.raise_for_status()
            profile_b64 = base64.b64encode(img_resp.content).decode("utf-8")
            profile_mime = img_resp.headers.get("content-type", "image/jpeg")

        # selfieのMIMEタイプを推定
        selfie_mime = _detect_mime(selfie_base64)
        selfie_data = selfie_base64.split(",")[-1]  # data:image/...;base64, を除去

        # Gemini Vision API (gemini-1.5-flash) を呼び出す
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": (
                            "以下の2枚の画像を比較してください。\n"
                            "1枚目はユーザーが登録したプロフィール写真、2枚目はリアルタイムで撮影したセルフィーです。\n"
                            "この2枚が同一人物であるか判定し、以下のJSON形式で回答してください。\n\n"
                            "```json\n"
                            "{\n"
                            '  "same_person": true または false,\n'
                            '  "confidence": 0.0〜1.0の確信度,\n'
                            '  "reason": "判定理由（日本語、30文字以内）"\n'
                            "}\n"
                            "```\n\n"
                            "画像以外の情報は一切考慮しないでください。"
                        )},
                        {
                            "inline_data": {
                                "mime_type": profile_mime,
                                "data": profile_b64
                            }
                        },
                        {
                            "inline_data": {
                                "mime_type": selfie_mime,
                                "data": selfie_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 200
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        # JSONを抽出してパース
        import json, re
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            return {
                "verified": bool(result.get("same_person", False)),
                "confidence": float(result.get("confidence", 0.0)),
                "message": result.get("reason", "AI判定完了")
            }

    except Exception as e:
        # APIエラー時はモックフォールバック
        print(f"[PhotoVerify] Gemini API error: {e}")

    return _mock_verify(selfie_base64)


def _mock_verify(selfie_base64: str) -> dict:
    """
    S-01対応: DEMO_MODE=true の場合のみ自動認証通過。
    本番環境では必ずGemini APIによる実判定を行う。
    """
    is_demo = os.environ.get("DEMO_MODE", "false").lower() == "true"
    has_image = bool(selfie_base64 and len(selfie_base64) > 100)
    
    if is_demo and has_image:
        return {
            "verified": True,
            "confidence": 0.92,
            "message": "デモモード: 開発環境のため自動認証済み（本番では実判定が行われます）"
        }
    return {
        "verified": False,
        "confidence": 0.0,
        "message": "本人確認に失敗しました。Gemini APIキーが設定されていないか、通信エラーが発生しました。"
    }


def _detect_mime(b64_str: str) -> str:
    """Base64データURIからMIMEタイプを検出する"""
    if b64_str.startswith("data:"):
        mime = b64_str.split(";")[0].replace("data:", "")
        return mime
    return "image/jpeg"
