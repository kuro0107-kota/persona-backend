import os
import tweepy
from dotenv import load_dotenv

def post_tweet(text: str, image_path: str = None):
    # .env ファイルを読み込む（親ディレクトリにある可能性を考慮）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(os.path.dirname(current_dir), ".env")
    load_dotenv(dotenv_path=env_path)
    
    # 環境変数からキーを取得
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.environ.get("TWITTER_ACCESS_SECRET")
    
    if not api_key:
        print("Twitter API keys are not set.")
        return None

    # Tweepy V2 Client (for creating tweet)
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    
    # Tweepy V1.1 API (for media upload, free tier allows this)
    auth = tweepy.OAuth1UserHandler(
        api_key, api_secret, access_token, access_token_secret
    )
    api = tweepy.API(auth)
    
    try:
        media_ids = []
        if image_path and os.path.exists(image_path):
            print(f"Uploading media: {image_path}")
            media = api.media_upload(image_path)
            media_ids.append(media.media_id)
            
        if media_ids:
            response = client.create_tweet(text=text, media_ids=media_ids)
        else:
            response = client.create_tweet(text=text)
            
        print(f"Tweet successful! ID: {response.data['id']}")
        return response.data['id']
    except Exception as e:
        print(f"Failed to post tweet: {e}")
        return None

if __name__ == "__main__":
    post_tweet("これはPersona（AIマッチングアプリ）の自動投稿連携テストです。 #Persona")
