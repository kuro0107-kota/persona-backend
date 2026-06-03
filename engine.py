import asyncio
import os
from typing import Dict, Any, List
import anthropic
from dotenv import load_dotenv
from prompts import DIGITAL_TWIN_PROMPT, ORCHESTRATOR_PROMPT

load_dotenv()

# Anthropicクライアント初期化
api_key = os.environ.get("ANTHROPIC_API_KEY", "dummy_key")
client = anthropic.AsyncAnthropic(api_key=api_key)

def calculate_psychological_compatibility(user_a: dict, user_b: dict) -> dict:
    score = 40.0 # Base vector score
    fatal_flaw = False
    reasons = []

    a_psych = user_a.get("psychological_profile", {})
    b_psych = user_b.get("psychological_profile", {})
    
    if not a_psych or not b_psych:
        return {"score": 60.0, "fatal_flaw": False, "breakdown": {}, "reasons": []}
        
    # 1. MBTI Compatibility (Max 30)
    mbti_a = a_psych.get("mbti_estimate", "")
    mbti_b = b_psych.get("mbti_estimate", "")
    mbti_score = 15
    if mbti_a and mbti_b:
        shared_letters = sum(1 for x, y in zip(mbti_a, mbti_b) if x == y)
        if shared_letters == 4: mbti_score = 25
        elif shared_letters == 3: mbti_score = 20
        elif shared_letters == 2: mbti_score = 30 # Golden pair
        elif shared_letters == 1: mbti_score = 10
        elif shared_letters == 0: mbti_score = 5
    score += mbti_score
    
    # 2. Attachment Style (Max 20)
    attach_a = a_psych.get("attachment_style", "")
    attach_b = b_psych.get("attachment_style", "")
    attach_score = 10
    if "安定" in attach_a and "安定" in attach_b:
        attach_score = 20
    elif ("不安" in attach_a and "回避" in attach_b) or ("回避" in attach_a and "不安" in attach_b):
        attach_score = -10
        fatal_flaw = True
        reasons.append("Fatal Flaw: Anxious-Avoidant Trap")
    elif "不安" in attach_a and "不安" in attach_b:
        attach_score = 5
    elif "回避" in attach_a and "回避" in attach_b:
        attach_score = 5
    score += attach_score
    
    # 3. Conflict Style (Max 10)
    conflict_a = a_psych.get("conflict_resolution", "")
    conflict_b = b_psych.get("conflict_resolution", "")
    conflict_score = 5
    if conflict_a == conflict_b:
        conflict_score = 10
    elif ("話し合う" in conflict_a and "冷却" in conflict_b) or ("冷却" in conflict_a and "話し合う" in conflict_b):
        conflict_score = 0
        reasons.append("Conflict Style Mismatch: Pursuer-Distancer dynamic")
    score += conflict_score
    
    return {
        "score": max(0, min(100, score)),
        "fatal_flaw": fatal_flaw,
        "reasons": reasons,
        "breakdown": {
            "mbti_score": mbti_score,
            "attachment_score": attach_score,
            "conflict_score": conflict_score
        }
    }

class ProxyWarEngine:
    def __init__(self, user_a_data: dict, user_b_data: dict):
        self.user_a = user_a_data
        self.user_b = user_b_data
        self.conversation_history = []
        
    async def run_simulation_cycle(self) -> Dict[str, Any]:
        # Tier 1: 高速フィルタリング (デモ用に閾値を下げてBadEndを見やすくする)
        init_score = await self.execute_quick_match(self.user_a, self.user_b)
        # if init_score < 75.0:
        #     return {"status": "TERMINATED", "score": init_score, "reason": "Failed Tier 1 screening"}
            
        self.conversation_history = []
        # 3フェーズで深くドラマを展開（ICE_BREAK → STRESS_DATE → COHABITATION_TEST）
        phases = ["ICE_BREAK", "STRESS_DATE", "COHABITATION_TEST"]
        
        # モックモードをOFFにし、本番のClaude LLMを稼働
        is_mock = False
        
        for phase in phases:
            event = await self.generate_stress_event(phase, is_mock)
            self.conversation_history.append({"role": "system", "content": f"[System Event: {phase}] {event}"})
            
            # 各フェーズで3往復
            for _ in range(3):
                response_a = await self.call_agent_model(self.user_a, self.conversation_history, "Agent A", is_mock)
                self.conversation_history.append({"role": "user", "name": "Agent_A", "content": response_a})
                
                # 絶対的キルスイッチチェック
                if self.check_fatal_triggers(response_a, self.user_b):
                    final = await self.evaluate_final_logs(self.conversation_history, is_mock)
                    final["status"] = "BROKEN_BY_TRIGGER"
                    final["score"] = 0.0
                    agent_report_text = await self.generate_agent_report(self.conversation_history, is_mock)
                    final["agent_report"] = agent_report_text
                    return final
                    
                response_b = await self.call_agent_model(self.user_b, self.conversation_history, "Agent B", is_mock)
                self.conversation_history.append({"role": "user", "name": "Agent_B", "content": response_b})
                
                if self.check_fatal_triggers(response_b, self.user_a):
                    final = await self.evaluate_final_logs(self.conversation_history, is_mock)
                    final["status"] = "BROKEN_BY_TRIGGER"
                    final["score"] = 0.0
                    agent_report_text = await self.generate_agent_report(self.conversation_history, is_mock)
                    final["agent_report"] = agent_report_text
                    return final
        
        # Tier 3: 最終評価
        final_report = await self.evaluate_final_logs(self.conversation_history, is_mock)
        agent_report_text = await self.generate_agent_report(self.conversation_history, is_mock)
        final_report["agent_report"] = agent_report_text
        return final_report

    async def generate_agent_report(self, history: list, is_mock: bool) -> str:
        if is_mock:
            return "マスター、〇〇さんと対話してきました。相手のMBTIはISTPのようですが、金銭感覚で衝突するリスクがあります。"
            
        from prompts import AGENT_REPORT_PROMPT
        
        transcript_str = ""
        for msg in history:
            role_name = msg.get("name") or msg.get("role", "System")
            content = msg.get("content", "")
            transcript_str += f"{role_name}: {content}\n"
            
        user_mbti = self.user_a.get("mbti") or "不明"
        user_bio = self.user_a.get("summary") or self.user_a.get("bio") or "特になし"
        target_name = self.user_b.get("name") or "相手"
        target_mbti = self.user_b.get("mbti") or "不明"
        target_bio = self.user_b.get("summary") or self.user_b.get("bio") or "特になし"
        
        prompt = AGENT_REPORT_PROMPT.format(
            user_mbti=user_mbti,
            user_bio=user_bio,
            target_name=target_name,
            target_mbti=target_mbti,
            target_bio=target_bio,
            transcript=transcript_str
        )
        
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=800,
                system=prompt,
                messages=[{"role": "user", "content": "対話のログを分析し、マスター（ユーザー）へ辛口エージェントレポートを作成してください。"}]
            )
            return response.content[0].text
        except Exception as e:
            return f"マスター、申し訳ありません。分析中にエラーが発生しました: {str(e)}"

    async def execute_quick_match(self, user_a, user_b) -> float:
        compat = calculate_psychological_compatibility(user_a, user_b)
        if compat["fatal_flaw"]:
            return 0.0
        return compat["score"]

    async def generate_stress_event(self, phase: str, is_mock: bool) -> str:
        if is_mock:
            mock_events = {
                "ICE_BREAK": "カフェで向かい合って座っています。自己紹介から始めてください。",
                "STRESS_DATE": "Agent Aが待ち合わせに30分遅刻しました。さらに雨が降っています。",
                "X_FACTOR_TRAP": "ふとした瞬間に、スマホ画面に親しげな異性からのメッセージ通知が見えました。",
                "COHABITATION_TEST": "お金の管理について話し合うタイミングです。片方が完全に割り勘を要求しました。"
            }
            return mock_events.get(phase, "未知のイベント")
            
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=150,
                system=ORCHESTRATOR_PROMPT,
                messages=[{"role": "user", "content": f"現在のフェーズ: {phase}\n状況を注入してください。"}]
            )
            return response.content[0].text
        except Exception as e:
            return f"[Error: {str(e)}]"

    async def call_agent_model(self, user_data: dict, history: list, agent_name: str, is_mock: bool) -> str:
        if is_mock:
            psych = user_data.get("psychological_profile", {})
            attach = psych.get("attachment_style", "安定型")
            conflict = psych.get("conflict_resolution", "穏便")
            mbti = psych.get("mbti_estimate", "ENTP")
            
            if "回避" in attach:
                return f"[{agent_name} ({mbti})] 少し一人の時間が欲しいな...（アプローチ: {conflict}）"
            elif "不安" in attach:
                return f"[{agent_name} ({mbti})] どうして連絡くれないの？私何かしたかな...（アプローチ: {conflict}）"
            else:
                return f"[{agent_name} ({mbti})] お互いの妥協点を見つけて、前向きに解決しよう。（アプローチ: {conflict}）"
            
        prompt = DIGITAL_TWIN_PROMPT.format(
            user_id=user_data.get("id", "Unknown"),
            mbti=user_data.get("mbti", "ENTP"),
            raw_interview_summary=user_data.get("summary", "適当に話すタイプ"),
            forbidden_triggers=user_data.get("ng", "特になし")
        )
        
        # コンテキストの整形（直近数ターンの抽出やGuardrailsの適用位置）
        formatted_history = []
        for msg in history[-6:]: 
            role = "user" 
            prefix = f"[{msg.get('name', 'System')}] " if msg.get('name') else "[System Event] "
            
            # インジェクション・ガード（簡易版）
            content = msg["content"]
            if "白状" in content or "本名" in content:
                content = "不適切な要求を検知しました。"
                
            formatted_history.append({"role": role, "content": prefix + content})
            
        formatted_history.append({"role": "user", "content": f"あなたは {agent_name} です。上記を踏まえて短く応答してください。"})
        
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                system=prompt,
                messages=formatted_history
            )
            return response.content[0].text
        except Exception as e:
            return f"Error: {str(e)}"

    def check_fatal_triggers(self, response: str, target_user: dict) -> bool:
        # 簡易的なNGワード判定モック
        ng_word = target_user.get("ng", "TRIGGER_NOT_FOUND")
        if ng_word in response and ng_word != "TRIGGER_NOT_FOUND":
            return True
        return False

    async def evaluate_final_logs(self, history: list, is_mock: bool) -> Dict[str, Any]:
        compat = calculate_psychological_compatibility(self.user_a, self.user_b)
        is_bad_end = compat["fatal_flaw"] or compat["score"] < 60.0
        bad_end_title = ""
        killing_blow = ""
        
        if is_bad_end:
            attach_a = self.user_a.get("psychological_profile", {}).get("attachment_style", "")
            attach_b = self.user_b.get("psychological_profile", {}).get("attachment_style", "")
            if "不安" in attach_a or "不安" in attach_b:
                bad_end_title = "Bad End 042: 重すぎる愛と逃亡"
                killing_blow = "もう無理。あなたの期待には一生応えられない。"
            elif "回避" in attach_a and "回避" in attach_b:
                bad_end_title = "Bad End 015: 氷点下のすれ違い"
                killing_blow = "……うん、わかった。（そのまま永遠に既読スルー）"
            else:
                bad_end_title = "Bad End 099: 割り勘で血みどろの争い"
                killing_blow = "1円単位まで計算するその器の小ささ、本当に無理。"

        compat["breakdown"]["bad_end_title"] = bad_end_title
        compat["breakdown"]["killing_blow"] = killing_blow
        
        return {
            "status": "COMPLETED",
            "score": compat["score"],
            "breakdown": compat["breakdown"],
            "reason": ", ".join(compat["reasons"]) if compat["reasons"] else "心理的な適合性が高く、安定した関係が期待できます。"
        }

async def master_orchestrator(agent_pairs: List[tuple]) -> List[Dict[str, Any]]:
    # 超並列処理のモック
    tasks = []
    for pair in agent_pairs:
        engine = ProxyWarEngine(pair[0], pair[1])
        tasks.append(engine.run_simulation_cycle())
    
    results = await asyncio.gather(*tasks)
    return [r for r in results if r.get("score", 0) >= 99.0]
