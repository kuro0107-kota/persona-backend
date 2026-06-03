"""
start.py — Railway用エントリーポイント
PORT環境変数を読み取ってuvicornを起動する
"""
import os
import uvicorn

port = int(os.environ.get("PORT", "8000"))
print(f"Starting Persona Backend on port {port}...")
uvicorn.run("main:app", host="0.0.0.0", port=port)
