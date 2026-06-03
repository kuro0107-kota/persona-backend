import asyncio
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from contextlib import asynccontextmanager

from engine import ProxyWarEngine
from database import get_db, engine
from models import User, SimulationResult, Base
from vector_store import get_vector_engine
from photo_verify import verify_same_person
from agent_routes import router as agent_router
from growth_routes import router as growth_router  # New-01~08: 成長機能
from agent_system.memory_store import MemoryStore
from agent_system.scheduler import start_scheduler, stop_scheduler
from cache import get_cached_simulation  # P-01: キャッシュモジュール
import uuid

@asynccontextmanager
async def lifespan(app: FastAPI):
    # アプリ起動時にテーブルが存在しなければ作成する
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # エージェントメモリDBを初期化
    store = MemoryStore()
    await store.initialize()
    # APSchedulerでエージェントを自律稼働開始
    start_scheduler()
    yield
    # シャットダウン時にスケジューラーを停止
    stop_scheduler()

app = FastAPI(title="TinderProxyWar-CoreEngine", version="1.2.0", lifespan=lifespan)

# ============================================================
# 文字化け防止: JSONレスポンスに charset=utf-8 を強制
# ============================================================
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from fastapi.responses import JSONResponse
import json as _json

class CustomJSONResponse(JSONResponse):
    """日本語がエスケープされないJSONレスポンス"""
    def render(self, content) -> bytes:
        return _json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

app.default_response_class = CustomJSONResponse

class Utf8Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        ct = response.headers.get("content-type", "")
        if "application/json" in ct and "charset" not in ct:
            response.headers["content-type"] = ct + "; charset=utf-8"
        return response

app.add_middleware(Utf8Middleware)

# エージェント管理APIをマウント
app.include_router(agent_router)
# 成長機能（ウェイティングリスト・リファラル・ブロック・通報・ストリーク）をマウント
app.include_router(growth_router)


import os

# S-02: CORSをホワイトリスト化（現地開発 + 本番ドメイン）
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.3.6:3000",
]
if os.environ.get("ALLOWED_ORIGIN"):
    ALLOWED_ORIGINS.append(os.environ["ALLOWED_ORIGIN"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

class SimulationRequest(BaseModel):
    user_a_id: str
    user_b_id: str
    agent_a_prompt: str
    agent_b_prompt: str
    user_a_data: dict = {}
    user_b_data: dict = {}

class SimulationResponse(BaseModel):
    simulation_id: str
    status: str
    compatibility_score: float
    summary: str
    breakdown: Dict[str, Any]
    fatal_flaw_detected: bool
    transcript: List[Dict[str, Any]]
    agent_report: str = ""
    target_user_id: str = ""
    target_user_profile: dict = {}

@app.get("/")
async def root():
    """Persona API ダッシュボード"""
    from fastapi.responses import HTMLResponse
    html = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Persona API — 24h Cloud Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#0a0a0f;color:#e0e0e0;min-height:100vh;
background:linear-gradient(135deg,#0a0a1a 0%,#1a0a2e 50%,#0a1a2e 100%)}
.container{max-width:800px;margin:0 auto;padding:40px 20px}
h1{font-size:2.5em;background:linear-gradient(135deg,#a855f7,#06b6d4);-webkit-background-clip:text;
-webkit-text-fill-color:transparent;margin-bottom:8px}
.subtitle{color:#888;font-size:1.1em;margin-bottom:40px}
.status{display:inline-flex;align-items:center;gap:8px;background:#0f2a1a;border:1px solid #22c55e;
border-radius:20px;padding:6px 16px;color:#22c55e;font-weight:600;margin-bottom:30px}
.dot{width:10px;height:10px;border-radius:50%;background:#22c55e;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);
border-radius:16px;padding:24px;margin-bottom:20px;backdrop-filter:blur(10px)}
.card h2{font-size:1.2em;color:#a855f7;margin-bottom:16px}
table{width:100%;border-collapse:collapse}
td{padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.06)}
td:first-child{color:#888;width:40%}
a{color:#06b6d4;text-decoration:none}
a:hover{text-decoration:underline}
.footer{text-align:center;color:#444;margin-top:40px;font-size:.85em}
</style>
</head>
<body>
<div class="container">
<h1>✦ Persona API</h1>
<p class="subtitle">AI恋愛シミュレーション × 仮想企業自律運営</p>
<div class="status"><span class="dot"></span> 24時間稼働中</div>

<div class="card">
<h2>🏢 AI仮想企業（11名）</h2>
<table>
<tr><td>👑 CEO</td><td>毎日8:00 — 経営報告書</td></tr>
<tr><td>📈 CFO</td><td>毎日8:00 / 20:00 — KPI分析</td></tr>
<tr><td>📣 CMO</td><td>毎日6:00 — SNSコンテンツ生成</td></tr>
<tr><td>📊 CPO</td><td>毎日10:00 — プロダクト改善</td></tr>
<tr><td>🛡️ CTO</td><td>毎日2:00 — 技術レビュー</td></tr>
<tr><td>✅ QA</td><td>30分ごと — 品質チェック</td></tr>
<tr><td>💬 CS / 💰 経理 / 📋 総務 / 🔬 Research / ⚖️ Legal</td><td>日次稼働</td></tr>
</table>
</div>

<div class="card">
<h2>🔗 APIエンドポイント</h2>
<table>
<tr><td>GET</td><td><a href="/health">/health</a></td></tr>
<tr><td>GET</td><td><a href="/api/v1/agents/status">/api/v1/agents/status</a></td></tr>
<tr><td>GET</td><td><a href="/api/v1/agents/schedule">/api/v1/agents/schedule</a></td></tr>
<tr><td>POST</td><td>/api/v1/simulate</td></tr>
<tr><td>POST</td><td>/api/v1/agents/run/{agent_name}</td></tr>
<tr><td>GET</td><td><a href="/api/v1/tags">/api/v1/tags</a></td></tr>
<tr><td>POST</td><td>/api/v1/date-plan/suggest</td></tr>
<tr><td>GET</td><td><a href="/docs">/docs</a> (Swagger UI)</td></tr>
</table>
</div>

<div class="footer">
Persona v1.0 — Powered by Claude AI × Railway Cloud<br>
PCが閉じていても、AIが24時間働き続けています。
</div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/v1/simulate", response_model=SimulationResponse)
async def trigger_simulation(payload: SimulationRequest, db: AsyncSession = Depends(get_db)):
    try:
        # =============================================
        # P-01: キャッシュチェック（APIコスト1/20削減）
        # 24時間以内の同一ペアはDB再利用
        # =============================================
        cached = await get_cached_simulation(payload.user_a_id, payload.user_b_id, db)
        if cached:
            return SimulationResponse(**{k: v for k, v in cached.items() if k != "cached"})

        # Ensure users exist in the DB
        for user_data in [payload.user_a_data, payload.user_b_data]:
            uid = user_data.get("id") or (payload.user_a_id if user_data == payload.user_a_data else payload.user_b_id)
            existing_user = await db.get(User, uid)
            if not existing_user:
                new_user = User(
                    id=uid,
                    name=user_data.get("name", "名前未設定"),  # Fix-04: ハードコード名前削除
                    mbti=user_data.get("mbti"),
                    bio=user_data.get("summary")
                )
                db.add(new_user)
        await db.commit()

        # Initialize the ProxyWarEngine with payload data
        engine = ProxyWarEngine(
            user_a_data=payload.user_a_data or {"id": payload.user_a_id},
            user_b_data=payload.user_b_data or {"id": payload.user_b_id}
        )
        
        # Run the full simulation pipeline
        result = await engine.run_simulation_cycle()
        
        is_fatal = result.get("status") == "BROKEN_BY_TRIGGER"
        
        # Save the result to the database
        sim_result = SimulationResult(
            user_a_id=payload.user_a_id,
            user_b_id=payload.user_b_id,
            compatibility_score=result.get("score", 0.0),
            fatal_flaw_detected=is_fatal,
            breakdown_json=result.get("breakdown", {}),
            transcript=str(engine.conversation_history),
            agent_report=result.get("agent_report", "")
        )
        db.add(sim_result)
        await db.commit()
        await db.refresh(sim_result)
        
        # ② KPI自動計測（CEO承認事項②対応）
        try:
            from agent_system.memory_store import MemoryStore as _MS
            _store = _MS()
            score = result.get("score", 0.0)
            await _store.save_kpi("simulation_score", score, {
                "user_a": payload.user_a_id,
                "user_b": payload.user_b_id,
                "fatal": is_fatal,
                "status": result.get("status", "")
            })
            await _store.save_kpi("fatal_flaw_rate", 1.0 if is_fatal else 0.0)
        except Exception:
            pass  # KPI記録失敗はメインフローに影響させない
        
        return SimulationResponse(
            simulation_id=str(sim_result.id),
            status=result.get("status", "UNKNOWN"),
            compatibility_score=result.get("score", 0.0),
            summary=result.get("reason", "No reason provided"),
            breakdown=result.get("breakdown", {}),
            fatal_flaw_detected=is_fatal,
            transcript=engine.conversation_history,
            agent_report=result.get("agent_report", ""),
            target_user_id=payload.user_b_id
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Engine Panic: {str(e)}")

class RegisterRequest(BaseModel):
    user_id: str
    name: str
    mbti: str
    summary: str
    agent_prompt: str
    psychological_profile: dict = {}
    age: str = ""
    hobbies: str = ""
    gender: str = ""
    looking_for_gender: str = ""
    location: str = ""
    height: str = ""
    job: str = ""
    income: str = ""
    smoking: str = ""
    alcohol: str = ""
    profile_image_url: str = ""
    photo_urls: List[str] = []
    is_verified: bool = False

@app.post("/api/v1/users/register")
async def register_user(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await db.get(User, payload.user_id)
        if not user:
            user = User(
                id=payload.user_id, 
                name=payload.name, 
                mbti=payload.mbti, 
                bio=payload.summary,
                age=payload.age,
                hobbies=payload.hobbies,
                psychological_profile=payload.psychological_profile,
                gender=payload.gender,
                looking_for_gender=payload.looking_for_gender,
                location=payload.location,
                height=payload.height,
                job=payload.job,
                income=payload.income,
                smoking=payload.smoking,
                alcohol=payload.alcohol,
                profile_image_url=payload.profile_image_url,
                photo_urls=payload.photo_urls or [],
                is_verified=payload.is_verified
            )
            db.add(user)
        else:
            user.name = payload.name
            user.mbti = payload.mbti
            user.bio = payload.summary
            user.age = payload.age
            user.hobbies = payload.hobbies
            user.psychological_profile = payload.psychological_profile
            user.gender = payload.gender
            user.looking_for_gender = payload.looking_for_gender
            user.location = payload.location
            user.height = payload.height
            user.job = payload.job
            user.income = payload.income
            user.smoking = payload.smoking
            user.alcohol = payload.alcohol
            user.profile_image_url = payload.profile_image_url
            if payload.photo_urls:
                user.photo_urls = payload.photo_urls
            if payload.is_verified:
                user.is_verified = True
        
        vec_engine = get_vector_engine()
        q_id = str(uuid.uuid4())
        text_for_embedding = f"{payload.summary}\n{payload.agent_prompt}"
        vec_engine.upsert_profile(q_id, payload.user_id, text_for_embedding)
        
        await db.commit()
        
        # KPI自動計測（ユーザー登録数）
        try:
            from agent_system.memory_store import MemoryStore as _MS
            _store = _MS()
            await _store.save_kpi("user_registered", 1.0, {
                "user_id": payload.user_id,
                "gender": payload.gender,
                "location": payload.location,
            })
        except Exception:
            pass
        
        return {"status": "registered", "qdrant_id": q_id}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


class SelfieVerifyRequest(BaseModel):
    user_id: str
    selfie_base64: str         # data:image/jpeg;base64,... 形式
    profile_image_url: str     # 対象のプロフィール写真URL

@app.post("/api/v1/users/verify-selfie")
async def selfie_verify(payload: SelfieVerifyRequest, db: AsyncSession = Depends(get_db)):
    """
    S-05: user_idが存在するユーザーのみ認証可能。
    セルフィーとプロフィール写真をAIで比較し、同一人物か判定する
    """
    # S-05: ユーザー存在確認（未登録ユーザーの認証を拒否）
    user = await db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please complete registration first.")

    # P-02: セルフィーサイズ械準（5MB超えたら拒否）
    selfie_data = payload.selfie_base64.split(",")[-1]
    approx_size_bytes = len(selfie_data) * 3 // 4
    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    if approx_size_bytes > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Selfie image too large. Please use an image under 5MB.")

    result = await verify_same_person(payload.selfie_base64, payload.profile_image_url)
    
    # 認証成功時はDBに記録
    if result["verified"]:
        user.is_verified = True
        await db.commit()
    
    return result


class AddPhotosRequest(BaseModel):
    user_id: str
    photo_urls: List[str]

@app.post("/api/v1/users/photos")
async def add_photos(payload: AddPhotosRequest, db: AsyncSession = Depends(get_db)):
    """ユーザーに写真を追加登録する"""
    user = await db.get(User, payload.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    existing = user.photo_urls or []
    # 重複を除いてマージ
    merged = list(dict.fromkeys(existing + payload.photo_urls))
    # 最大6枚まで
    user.photo_urls = merged[:6]
    await db.commit()
    return {"status": "updated", "photo_urls": user.photo_urls}

@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "name": user.name,
        "mbti": user.mbti,
        "bio": user.bio,
        "age": user.age,
        "hobbies": user.hobbies,
        "psychological_profile": user.psychological_profile,
        "gender": user.gender,
        "looking_for_gender": user.looking_for_gender,
        "location": user.location,
        "height": user.height,
        "job": user.job,
        "income": user.income,
        "smoking": user.smoking,
        "alcohol": user.alcohol,
        "profile_image_url": user.profile_image_url,
        "photo_urls": user.photo_urls or [],
        "is_verified": user.is_verified or False
    }

class MatchRequest(BaseModel):
    user_id: str
    min_age: int = 18
    max_age: int = 100
    location: str = ""
    limit: int = 5

@app.post("/api/v1/match", response_model=List[SimulationResponse])
async def find_matches(payload: MatchRequest, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, payload.user_id)
    if not user:
        raise HTTPException(404, "User not found")
        
    # 1. DB-level filtering (gender, location, age)
    stmt = select(User).where(User.id != user.id)
    result_users = await db.execute(stmt)
    all_users = result_users.scalars().all()
    
    filtered_users = []
    for u in all_users:
        # Gender Match
        if user.looking_for_gender and user.looking_for_gender != "全て":
            if u.gender != user.looking_for_gender:
                continue
        # Location Match
        if payload.location and payload.location != "全国":
            if u.location != payload.location:
                continue
        # Age Match
        if u.age:
            try:
                age_val = int(u.age)
                if age_val < payload.min_age or age_val > payload.max_age:
                    continue
            except ValueError:
                pass
        filtered_users.append(u)
        
    filtered_user_ids = {u.id for u in filtered_users}
    
    # 2. Vector search matching
    vec_engine = get_vector_engine()
    candidates = vec_engine.search_candidates(user.bio, limit=100, exclude_user_id=payload.user_id)
    
    # 3. Filter vector results
    valid_candidates = [c for c in candidates if c["user_id"] in filtered_user_ids]
    valid_candidates = valid_candidates[:payload.limit]
    
    # Fallback if vector database search did not return matches
    if not valid_candidates:
        for u in filtered_users[:payload.limit]:
            valid_candidates.append({
                "user_id": u.id,
                "compatibility_score": 50.0
            })
            
    async def process_candidate(cand):
        cand_user = await db.get(User, cand["user_id"])
        if not cand_user:
            return None
            
        proxy_engine = ProxyWarEngine(
            user_a_data={
                "id": user.id,
                "name": user.name,
                "mbti": user.mbti,
                "summary": user.bio,
                "psychological_profile": user.psychological_profile,
                "gender": user.gender,
                "looking_for_gender": user.looking_for_gender,
                "location": user.location,
                "height": user.height,
                "job": user.job,
                "income": user.income,
                "smoking": user.smoking,
                "alcohol": user.alcohol
            },
            user_b_data={
                "id": cand_user.id,
                "name": cand_user.name,
                "mbti": cand_user.mbti,
                "summary": cand_user.bio,
                "psychological_profile": cand_user.psychological_profile,
                "gender": cand_user.gender,
                "looking_for_gender": cand_user.looking_for_gender,
                "location": cand_user.location,
                "height": cand_user.height,
                "job": cand_user.job,
                "income": cand_user.income,
                "smoking": cand_user.smoking,
                "alcohol": cand_user.alcohol
            }
        )
        sim_res = await proxy_engine.run_simulation_cycle()
        
        return SimulationResponse(
            simulation_id=str(uuid.uuid4()),
            status=sim_res.get("status", "COMPLETED"),
            compatibility_score=sim_res.get("score", 0.0),
            summary=f"[Vector Match: {cand.get('compatibility_score', 50)}%] " + sim_res.get("reason", ""),
            breakdown=sim_res.get("breakdown", {}),
            fatal_flaw_detected=sim_res.get("score", 0.0) == 0.0 or sim_res.get("breakdown", {}).get("bad_end_title") != "",
            transcript=proxy_engine.conversation_history,
            agent_report=sim_res.get("agent_report", ""),
            target_user_id=cand_user.id,
            target_user_profile={
                "name": cand_user.name,
                "mbti": cand_user.mbti,
                "age": cand_user.age,
                "gender": cand_user.gender,
                "location": cand_user.location,
                "height": cand_user.height,
                "job": cand_user.job,
                "income": cand_user.income,
                "smoking": cand_user.smoking,
                "alcohol": cand_user.alcohol,
                "profile_image_url": cand_user.profile_image_url,
                "bio": cand_user.bio
            }
        )

    # 複数人のシミュレーションを並列で実行
    tasks = [process_candidate(c) for c in valid_candidates]
    results = await asyncio.gather(*tasks)
    
    return [r for r in results if r is not None]

# === Phase 5: Matches & Chat APIs ===
from models import Match, Message
from sqlalchemy import or_, and_

class AcceptMatchRequest(BaseModel):
    user_id: str
    target_user_id: str

@app.post("/api/v1/matches/accept")
async def accept_match(payload: AcceptMatchRequest, db: AsyncSession = Depends(get_db)):
    # Check if already matched
    stmt = select(Match).where(
        or_(
            and_(Match.user_a_id == payload.user_id, Match.user_b_id == payload.target_user_id),
            and_(Match.user_a_id == payload.target_user_id, Match.user_b_id == payload.user_id)
        )
    )
    result = await db.execute(stmt)
    existing_match = result.scalars().first()
    
    if existing_match:
        return {"status": "already_matched", "match_id": existing_match.id}
        
    new_match = Match(user_a_id=payload.user_id, user_b_id=payload.target_user_id)
    db.add(new_match)
    await db.commit()
    await db.refresh(new_match)
    return {"status": "matched", "match_id": new_match.id}

@app.get("/api/v1/matches/{user_id}")
async def get_matches(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Match).where(or_(Match.user_a_id == user_id, Match.user_b_id == user_id))
    result = await db.execute(stmt)
    matches = result.scalars().all()
    
    response = []
    for m in matches:
        target_id = m.user_b_id if m.user_a_id == user_id else m.user_a_id
        target_user = await db.get(User, target_id)
        if target_user:
            response.append({
                "match_id": m.id,
                "target_user_id": target_user.id,
                "target_name": target_user.name,
                "target_bio": target_user.bio,
                "status": m.status,
                "created_at": m.created_at
            })
    return response

class SendMessageRequest(BaseModel):
    sender_id: str
    content: str

@app.post("/api/v1/messages/{match_id}")
async def send_message(match_id: str, payload: SendMessageRequest, db: AsyncSession = Depends(get_db)):
    msg = Message(match_id=match_id, sender_id=payload.sender_id, content=payload.content)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return {"status": "sent", "message_id": msg.id, "created_at": msg.created_at}

@app.get("/api/v1/messages/{match_id}")
async def get_messages(match_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Message).where(Message.match_id == match_id).order_by(Message.created_at.asc())
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    return [
        {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "created_at": msg.created_at
        } for msg in messages
    ]

# === Phase 6: AI Support Concierge ===
import anthropic
import os

class SupportRequest(BaseModel):
    user_id: str
    message: str

@app.post("/api/v1/support")
async def ai_support(payload: SupportRequest, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, payload.user_id)
    if not user:
        raise HTTPException(404, "User not found")
        
    psych = user.psychological_profile or {}
    mbti = psych.get("mbti_estimate", "不明")
    attachment = psych.get("attachment_style", "不明")
    conflict = psych.get("conflict_resolution", "不明")
    love = psych.get("love_language", "不明")
    
    system_prompt = f"""あなたは「Persona」の凄腕AIコンシェルジュ（恋愛・心理コンサルタント）です。
    ユーザーからの質問に対し、恋愛工学や心理学を交えつつ、少し辛口で的確なアドバイスを提供してください。
    
    【質問者の心理プロファイル】
    - MBTI: {mbti}
    - 愛着スタイル: {attachment}
    - 衝突解決スタイル: {conflict}
    - 愛情表現: {love}
    
    上記を踏まえ、「あなたは{attachment}だからこそ〜」のようにパーソナライズした回答を心がけてください。
    また、Personaの課金プランやスコアの仕組みについての質問であれば、システム仕様を簡潔に回答してください。"""
    
    api_key = os.environ.get("ANTHROPIC_API_KEY", "dummy_key")
    client = anthropic.AsyncAnthropic(api_key=api_key)
    
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": payload.message}]
        )
        return {"response": response.content[0].text}
    except Exception as e:
        return {"response": f"申し訳ありません。システムエラーが発生しました。({str(e)})"}

