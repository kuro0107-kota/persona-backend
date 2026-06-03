"""n8n ワークフロー作成スクリプト"""
import urllib.request
import json

APIKEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkYjQ0ODg0Yy1mY2EwLTRmMGItYThjMi1mZDlhMTQ1NjNkOGYiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiM2JhNjM2NjAtYjhhYi00NDZjLWFlMGYtYzliYjc1YjY2MzVjIiwiaWF0IjoxNzgwNDY1ODgyfQ.BEsu6QF-aIQtoVsvGdFL4vGoxYUyXe_JZXAn387VG9g"
BASE    = "https://saab9001.app.n8n.cloud"
GKEY   = "AQ.Ab8RN6KJ4nciAfaC_Kpgd0nMs31ZSFmG23NIPBKT2rzJvllTZQ"
SLACK  = "https://hooks.slack.com/services/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"
GURL   = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GKEY}"

PROMPT = (
    "あなたはPersonaというAIマッチングアプリのSNSマーケターです。\n"
    "Personaの特徴:\n"
    "- AIが代理で会話して相性チェック\n"
    "- AI本人確認バッジ（セルフィー認証）\n"
    "- 15問の価値観診断テスト\n\n"
    "今日のX投稿案を3本、それぞれ140文字以内で作成。\n"
    "各投稿に #Persona #AI婚活 を含める。\n"
    "鋭いフックで始める。番号付きリストで出力。"
)

GEMINI_BODY = json.dumps({
    "contents": [{"parts": [{"text": PROMPT}]}]
}, ensure_ascii=False)

SLACK_BODY = json.dumps({
    "text": "🌅 *今日のPersona投稿案*\n\n={{ $json.text }}\n\n✅ 気に入ったらそのまま投稿してください"
}, ensure_ascii=False)

JS_CODE = (
    "const d=$input.first().json;"
    "const t=d?.candidates?.[0]?.content?.parts?.[0]?.text??'生成失敗';"
    "const today=new Date().toLocaleDateString('ja-JP',{timeZone:'Asia/Tokyo'});"
    "return [{json:{text:t,date:today}}];"
)

workflow = {
    "name": "Persona - 毎朝SNS自動投稿",
    "settings": {"timezone": "Asia/Tokyo", "executionOrder": "v1"},
    "nodes": [
        {
            "id": "sch1", "name": "毎朝6時",
            "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2,
            "position": [200, 300],
            "parameters": {
                "rule": {"interval": [{"field": "cronExpression", "expression": "0 21 * * *"}]}
            }
        },
        {
            "id": "gem1", "name": "Gemini投稿案生成",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [500, 300],
            "parameters": {
                "method": "POST", "url": GURL,
                "authentication": "none", "sendBody": True,
                "specifyBody": "json", "jsonBody": GEMINI_BODY,
                "options": {}
            }
        },
        {
            "id": "cod1", "name": "整形",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [800, 300],
            "parameters": {"jsCode": JS_CODE}
        },
        {
            "id": "slk1", "name": "Slack通知",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [1100, 300],
            "parameters": {
                "method": "POST", "url": SLACK,
                "authentication": "none", "sendBody": True,
                "specifyBody": "json", "jsonBody": SLACK_BODY,
                "options": {}
            }
        }
    ],
    "connections": {
        "毎朝6時":         {"main": [[{"node": "Gemini投稿案生成", "type": "main", "index": 0}]]},
        "Gemini投稿案生成": {"main": [[{"node": "整形",            "type": "main", "index": 0}]]},
        "整形":            {"main": [[{"node": "Slack通知",        "type": "main", "index": 0}]]}
    }
}

def call(url, data=None, method="GET"):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={"X-N8N-API-KEY": APIKEY, "Content-Type": "application/json", "Accept": "application/json"}
    )
    r = urllib.request.urlopen(req, timeout=20)
    return json.loads(r.read())

# 作成
print("ワークフロー作成中...")
try:
    resp = call(f"{BASE}/api/v1/workflows", workflow, "POST")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"[NG] HTTP {e.code}: {body}")
    raise
wf_id = resp["id"]
print(f"[OK] 作成完了: ID={wf_id}")

# 有効化
print("有効化中...")
resp2 = call(f"{BASE}/api/v1/workflows/{wf_id}/activate", {}, "POST")
print(f"[OK] Active={resp2.get('active')}")

print(f"\n完了。ワークフローID: {wf_id}")
print(f"URL: {BASE}/workflow/{wf_id}")
