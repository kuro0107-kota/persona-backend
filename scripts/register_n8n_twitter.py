import requests
import json

jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkYjQ0ODg0Yy1mY2EwLTRmMGItYThjMi1mZDlhMTQ1NjNkOGYiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiM2JhNjM2NjAtYjhhYi00NDZjLWFlMGYtYzliYjc1YjY2MzVjIiwiaWF0IjoxNzgwNDY1ODgyfQ.BEsu6QF-aIQtoVsvGdFL4vGoxYUyXe_JZXAn387VG9g"

url = "https://saab9001.app.n8n.cloud/api/v1/credentials"
payload = {
    "name": "Twitter API (Legacy)",
    "type": "twitterApi",
    "data": {
        "consumerKey": "GwsOLlrambdU7r0mPhl95E38T",
        "consumerSecret": "20ca9Dhqehl3OWMFPMrV1KcicyGgLrTNvngQiEIWRcnCDkVcWa",
        "accessToken": "2062065015407128577-PsIyFPWELzK3YvZ2d1Bj3yA5vXawGZ",
        "accessSecret": "oZPQ2qUCPftMkZ0X4rJVonpA9VCZrxbzgzt2IwpVvW3YA"
    }
}

print("Trying X-N8N-API-KEY header...")
try:
    headers_api_key = {
        "X-N8N-API-KEY": jwt_token,
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers_api_key, json=payload)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
except Exception as e:
    print("Error:", e)
