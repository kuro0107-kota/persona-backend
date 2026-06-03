# ============================================================
# Persona Backend — Production Dockerfile
# 24時間自動稼働・AI仮想企業組織
# ============================================================
FROM python:3.12-slim

# 作業ディレクトリ
WORKDIR /app

# システム依存パッケージ（Pillow, cryptography等に必要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libssl-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt を先にコピーしてキャッシュ活用
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# 環境変数
ENV PYTHONUTF8=1
ENV TZ=Asia/Tokyo

# ポート公開
EXPOSE 8000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; r=httpx.get('http://localhost:8000/health'); exit(0 if r.status_code==200 else 1)"

# 起動コマンド（uvicorn + APSchedulerで全エージェント自動稼働）
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
