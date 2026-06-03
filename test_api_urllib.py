import urllib.request
import json
import traceback

data = json.dumps({
    "user_a_id": "usr_1", "user_b_id": "usr_2", "agent_a_prompt": "", "agent_b_prompt": "",
    "user_a_data": {"name": "A", "mbti": "ENTP", "ng": ""}, "user_b_data": {"name": "B", "mbti": "ISFJ", "ng": ""}
}).encode('utf-8')

req = urllib.request.Request("http://127.0.0.1:8000/api/v1/simulate", data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as res:
        print(res.status)
        print(res.read().decode())
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode())
