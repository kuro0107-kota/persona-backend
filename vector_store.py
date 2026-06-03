import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# Configuration
QDRANT_PATH = os.path.join(os.path.dirname(__file__), "qdrant_data")
COLLECTION_NAME = "agent_profiles"
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2" # 日本語対応で軽量なモデル

class VectorMatchEngine:
    def __init__(self):
        # Qdrantのローカルファイルベースのクライアントを初期化
        self.qdrant = QdrantClient(path=QDRANT_PATH)
        
        # SentenceTransformerモデルのロード（初回実行時にダウンロードされます）
        print(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
        self.encoder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print("Embedding model loaded.")
        
        # コレクション（テーブル）が存在するか確認し、なければ作成
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            self.qdrant.get_collection(collection_name=COLLECTION_NAME)
        except Exception:
            # paraphrase-multilingual-MiniLM-L12-v2の出力次元数は384
            print(f"Creating new Qdrant collection: {COLLECTION_NAME}")
            self.qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )

    def upsert_profile(self, qdrant_id: str, user_id: str, text_content: str):
        """
        プロフィール情報をベクトル化し、Qdrantに保存（Upsert）します。
        qdrant_idはUUID形式の文字列を想定しています。
        """
        vector = self.encoder.encode(text_content).tolist()
        point = PointStruct(
            id=qdrant_id,
            vector=vector,
            payload={"user_id": user_id}
        )
        self.qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )

    def search_candidates(self, query_text: str, limit: int = 5, exclude_user_id: str = None):
        """
        クエリテキストに最も近い候補者を検索します。
        """
        query_vector = self.encoder.encode(query_text).tolist()
        hits = self.qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit + 1 # 自分自身を除外する可能性があるため多めに取得
        )
        
        results = []
        for hit in hits:
            user_id = hit.payload.get("user_id")
            if user_id == exclude_user_id:
                continue
            
            results.append({
                "user_id": user_id,
                "compatibility_score": round(hit.score * 100, 1) # コサイン類似度(0~1)をパーセント表記に
            })
            
            if len(results) == limit:
                break
                
        return results

# シングルトンインスタンス
_vector_engine = None

def get_vector_engine() -> VectorMatchEngine:
    global _vector_engine
    if _vector_engine is None:
        _vector_engine = VectorMatchEngine()
    return _vector_engine
