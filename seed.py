import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base
from models import User
from vector_store import get_vector_engine
import uuid
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

DUMMY_USERS = [
    {
        "id": "dummy_1",
        "name": "Sakura",
        "mbti": "ENFJ",
        "bio": "カフェ巡りと旅行が好きです。休日は外に出かけることが多いアクティブ派です。相手を思いやる関係を築きたいです。",
        "prompt": "You are Sakura, an ENFJ who loves cafes and traveling. You are empathetic and energetic.",
        "age": "24",
        "gender": "女性",
        "looking_for_gender": "男性",
        "location": "東京都",
        "height": "158cm",
        "job": "看護師",
        "income": "400万円",
        "smoking": "吸わない",
        "alcohol": "時々飲む",
        "profile_image_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150"
    },
    {
        "id": "dummy_2",
        "name": "Kenji",
        "mbti": "ISTP",
        "bio": "バイクとDIYが趣味。休日はガレージに引きこもってます。無口ですが誠実な関係を望んでます。",
        "prompt": "You are Kenji, an ISTP who loves motorcycles and DIY. You are quiet but sincere.",
        "age": "28",
        "gender": "男性",
        "looking_for_gender": "女性",
        "location": "神奈川県",
        "height": "175cm",
        "job": "エンジニア",
        "income": "600万円",
        "smoking": "吸わない",
        "alcohol": "時々飲む",
        "profile_image_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150"
    },
    {
        "id": "dummy_3",
        "name": "Yui",
        "mbti": "INFP",
        "bio": "インドア派で、読書や映画鑑賞が好きです。静かな時間を一緒に楽しめる人が理想です。",
        "prompt": "You are Yui, an INFP. You love reading and movies. You want someone who enjoys quiet time.",
        "age": "22",
        "gender": "女性",
        "looking_for_gender": "男性",
        "location": "東京都",
        "height": "152cm",
        "job": "イラストレーター",
        "income": "300万円",
        "smoking": "吸わない",
        "alcohol": "飲まない",
        "profile_image_url": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150"
    },
    {
        "id": "dummy_4",
        "name": "Takeru",
        "mbti": "ENTJ",
        "bio": "起業家として日々奮闘中。目標に向かって一緒に成長できるパートナーを探しています。",
        "prompt": "You are Takeru, an ENTJ entrepreneur. You are ambitious and seek a partner to grow with.",
        "age": "31",
        "gender": "男性",
        "looking_for_gender": "女性",
        "location": "東京都",
        "height": "180cm",
        "job": "会社経営",
        "income": "1500万円",
        "smoking": "吸わない",
        "alcohol": "飲む",
        "profile_image_url": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150"
    },
    {
        "id": "dummy_5",
        "name": "Mio",
        "mbti": "ESFP",
        "bio": "毎日楽しく過ごすのがモットー！美味しいものを食べに行ったり、フェスに行ったりするのが好き！",
        "prompt": "You are Mio, an ESFP. You love food, festivals, and having fun every day.",
        "age": "25",
        "gender": "女性",
        "looking_for_gender": "男性",
        "location": "大阪府",
        "height": "162cm",
        "job": "アパレル店員",
        "income": "350万円",
        "smoking": "時々吸う",
        "alcohol": "飲む",
        "profile_image_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150"
    }
]

async def seed_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    vec_engine = get_vector_engine()
    
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as db:
        for u in DUMMY_USERS:
            existing = await db.get(User, u["id"])
            if not existing:
                print(f"Creating user {u['name']}...")
                new_user = User(
                    id=u["id"],
                    name=u["name"],
                    mbti=u["mbti"],
                    bio=u["bio"],
                    age=u["age"],
                    gender=u["gender"],
                    looking_for_gender=u["looking_for_gender"],
                    location=u["location"],
                    height=u["height"],
                    job=u["job"],
                    income=u["income"],
                    smoking=u["smoking"],
                    alcohol=u["alcohol"],
                    profile_image_url=u["profile_image_url"]
                )
                db.add(new_user)
                
                q_id = str(uuid.uuid4())
                text_for_embedding = f"{u['bio']}\n{u['prompt']}"
                vec_engine.upsert_profile(q_id, u["id"], text_for_embedding)
        await db.commit()
    print("Seed complete!")

if __name__ == "__main__":
    asyncio.run(seed_data())
