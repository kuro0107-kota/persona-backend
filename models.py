from sqlalchemy import Column, String, Text, Float, Boolean, JSON, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
import uuid, random, string
from datetime import datetime, timezone
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    mbti = Column(String(4), nullable=True)
    bio = Column(Text, nullable=True)
    age = Column(String(10), nullable=True)
    hobbies = Column(Text, nullable=True)
    psychological_profile = Column(JSON, nullable=True)

    # Standard Profile Fields
    gender = Column(String(20), nullable=True)
    looking_for_gender = Column(String(20), nullable=True)
    location = Column(String(50), nullable=True)
    height = Column(String(10), nullable=True)
    job = Column(String(50), nullable=True)
    income = Column(String(50), nullable=True)
    smoking = Column(String(50), nullable=True)
    alcohol = Column(String(50), nullable=True)
    profile_image_url = Column(String(255), nullable=True)
    photo_urls = Column(JSON, nullable=True, default=list)
    is_verified = Column(Boolean, default=False)

    # New-02: リファラルプログラム
    referral_code = Column(String(20), unique=True, nullable=True)
    likes_balance = Column(Integer, default=10)

    # New-08: ストリーク
    login_streak = Column(Integer, default=0)
    last_login_date = Column(String(10), nullable=True)  # YYYY-MM-DD

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    agent_profile = relationship("AgentProfile", back_populates="user", uselist=False,
                                 cascade="all, delete-orphan")


class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    qdrant_id = Column(String(36), unique=True, nullable=True)
    prompt_blueprint = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="agent_profile")


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_a_id = Column(String(50), ForeignKey("users.id"))
    user_b_id = Column(String(50), ForeignKey("users.id"))
    compatibility_score = Column(Float, nullable=True)
    fatal_flaw_detected = Column(Boolean, default=False)
    breakdown_json = Column(JSON, nullable=True)
    transcript = Column(Text, nullable=True)
    agent_report = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Match(Base):
    __tablename__ = "matches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_a_id = Column(String(50), ForeignKey("users.id"))
    user_b_id = Column(String(50), ForeignKey("users.id"))
    status = Column(String(20), default="matched")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    match_id = Column(String(36), ForeignKey("matches.id", ondelete="CASCADE"))
    sender_id = Column(String(50), ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ============================================================
# New-01: ウェイティングリスト（女性先行獲得戦略）
# ============================================================
class WaitlistEntry(Base):
    __tablename__ = "waitlist"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    gender = Column(String(10), nullable=True)       # female | male | other
    age_range = Column(String(20), nullable=True)
    referral_code = Column(String(20), nullable=True)     # 誰に紹介されたか
    my_referral_code = Column(String(20), unique=True)    # 自分の紹介コード
    referral_count = Column(Integer, default=0)           # 紹介した人数
    position = Column(Integer, nullable=True)             # 順番（小さいほど早い）
    status = Column(String(20), default="waiting")        # waiting | invited | registered
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ============================================================
# New-02: リファラルプログラム
# ============================================================
class ReferralRecord(Base):
    __tablename__ = "referral_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_user_id = Column(String(50), ForeignKey("users.id"))
    referred_user_id = Column(String(50), ForeignKey("users.id"))
    bonus_given = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ============================================================
# New-04: ブロック・通報機能（法令必須）
# ============================================================
class Block(Base):
    __tablename__ = "blocks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    blocker_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    blocked_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reporter_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    reported_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    reason = Column(String(50), nullable=False)   # spam | fake | harassment | inappropriate
    detail = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending | reviewed | resolved
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ============================================================
# New-05: プッシュ通知トークン
# ============================================================
class PushToken(Base):
    __tablename__ = "push_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    token = Column(Text, nullable=False)
    platform = Column(String(20), default="web")    # web | ios | android
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ============================================================
# New-09: コミュニティ / 趣味タグ機能
# ============================================================
class HobbyTag(Base):
    """趣味・興味タグのマスターテーブル"""
    __tablename__ = "hobby_tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False, index=True)  # 例: "カフェ巡り"
    category = Column(String(30), nullable=True)  # 例: "アウトドア", "インドア", "グルメ"
    icon = Column(String(10), nullable=True)  # 絵文字: "☕"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserHobbyTag(Base):
    """ユーザーと趣味タグの中間テーブル"""
    __tablename__ = "user_hobby_tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(String(36), ForeignKey("hobby_tags.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ユーティリティ
def generate_referral_code(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))
