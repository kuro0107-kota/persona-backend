import requests

jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkYjQ0ODg0Yy1mY2EwLTRmMGItYThjMi1mZDlhMTQ1NjNkOGYiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiM2JhNjM2NjAtYjhhYi00NDZjLWFlMGYtYzliYjc1YjY2MzVjIiwiaWF0IjoxNzgwNDY1ODgyfQ.BEsu6QF-aIQtoVsvGdFL4vGoxYUyXe_JZXAn387VG9g"

url = "https://saab9001.app.n8n.cloud/api/v1/credentials/VscH8bX9oQn0H5l3"
headers = {
    "X-N8N-API-KEY": jwt_token,
    "Content-Type": "application/json"
}

try:
    resp = requests.get(url, headers=headers)
    print("Status:", resp.status_code)
    print("Response:")
    print(resp.text)
except Exception as e:
    print("Error:", e)
