import requests
try:
    res = requests.post("http://127.0.0.1:8000/api/v1/simulate", json={
        "user_a_id": "usr_1", "user_b_id": "usr_2", "agent_a_prompt": "", "agent_b_prompt": "",
        "user_a_data": {"name": "A", "mbti": "ENTP"}, "user_b_data": {"name": "B", "mbti": "ISFJ"}
    })
    print(res.status_code)
    print(res.text)
except Exception as e:
    print(e)
