import asyncio
from main import trigger_simulation, SimulationRequest

async def test():
    req = SimulationRequest(
        user_a_id="a", user_b_id="b", agent_a_prompt="", agent_b_prompt="",
        user_a_data={"id": "A", "mbti": "ENTP"}, user_b_data={"id": "B", "mbti": "ISFJ"}
    )
    res = await trigger_simulation(req)
    print(res)

if __name__ == "__main__":
    asyncio.run(test())
