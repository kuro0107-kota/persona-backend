"""
QA Agent — シミュレーション品質管理エージェント（Haiku / Tier A）
役割: 30分ごとにシミュレーションエンジンの品質をテストし、
     スコア異常・エラーを検知してCEOに報告する。

CEO承認事項①対応: シミュレーション失敗修正
- タイムアウトを120秒に延長（Claudeマルチターン会話は時間がかかる）
- エンジン直接テスト（API経由ではなくエンジンを直接呼ぶ）を追加
- エラー詳細の改善
"""
from __future__ import annotations
import os
import httpx
from agent_system.base_agent import BaseAgent
from agent_system.message_bus import MessageBus
from agent_system.memory_store import MemoryStore


BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# QAテスト用の標準ペルソナペア（安定型×安定型 → 高相性が期待される）
QA_TEST_PAIR = {
    "user_a": {
        "id": "qa_test_user_a",
        "name": "QAテストA（安定型）",
        "mbti": "ENFJ",
        "summary": "穏やかで話し合いを好む安定愛着スタイルの人物",
        "psychological_profile": {
            "mbti_estimate": "ENFJ",
            "attachment_style": "安定型",
            "conflict_resolution": "話し合う",
            "love_language": "言葉"
        }
    },
    "user_b": {
        "id": "qa_test_user_b",
        "name": "QAテストB（安定型）",
        "mbti": "INFP",
        "summary": "創造的で感受性が高い安定愛着スタイルの人物",
        "psychological_profile": {
            "mbti_estimate": "INFP",
            "attachment_style": "安定型",
            "conflict_resolution": "話し合う",
            "love_language": "時間"
        }
    }
}

# NGペア（不安型×回避型 → 即破綻が期待される）
QA_BAD_PAIR = {
    "user_a": {
        "id": "qa_bad_user_a",
        "name": "QAテストC（不安型）",
        "mbti": "ENFP",
        "summary": "不安型愛着スタイルで感情的になりやすい",
        "psychological_profile": {
            "mbti_estimate": "ENFP",
            "attachment_style": "不安型",
            "conflict_resolution": "感情的",
            "love_language": "行為"
        }
    },
    "user_b": {
        "id": "qa_bad_user_b",
        "name": "QAテストD（回避型）",
        "mbti": "ISTP",
        "summary": "回避型愛着スタイルで一人の時間を最優先する",
        "psychological_profile": {
            "mbti_estimate": "ISTP",
            "attachment_style": "回避型",
            "conflict_resolution": "黙る",
            "love_language": "一人の時間"
        }
    }
}


class QaAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="qa",
            display_name="🤖 QA Agent",
            department="Quality Assurance"
        )

    @property
    def system_prompt(self) -> str:
        return """あなたはPersona Inc.のシミュレーション品質管理AIエージェントです。

## 役割
- シミュレーションエンジンの動作テストを実行し、結果を検証する
- スコアの異常値・エラーを検知して報告する
- プロンプトの品質劣化を監視する

## 報告フォーマット
- 検出した問題は具体的に記述する
- 正常の場合は「✅ 正常稼働中」と報告する
- 重大な問題（エラー率>20%、スコアが常に0や100）はアラートとして送信する"""

    async def _test_health(self) -> dict:
        """テスト1: バックエンドヘルスチェック"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{BACKEND_URL}/health")
                return {"test": "health_check", "passed": resp.status_code == 200, "status": resp.status_code}
        except Exception as e:
            return {"test": "health_check", "passed": False, "error": str(e)}

    async def _test_compatibility_engine(self) -> dict:
        """テスト2: 心理的相性計算エンジンの直接テスト（API不要・高速）"""
        try:
            # エンジンをインポートして直接テスト
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from engine import calculate_psychological_compatibility

            # 安定型×安定型 → 高スコア期待
            good_result = calculate_psychological_compatibility(
                QA_TEST_PAIR["user_a"], QA_TEST_PAIR["user_b"]
            )
            good_score = good_result.get("score", 0)
            good_ok = good_score >= 50  # 安定型ペアは50点以上が正常

            # 不安型×回避型 → 低スコア+fatal_flaw期待
            bad_result = calculate_psychological_compatibility(
                QA_BAD_PAIR["user_a"], QA_BAD_PAIR["user_b"]
            )
            bad_fatal = bad_result.get("fatal_flaw", False)  # fatal_flawが検知されるべき

            engine_ok = good_ok and bad_fatal
            return {
                "test": "compatibility_engine",
                "passed": engine_ok,
                "good_score": good_score,
                "bad_fatal_detected": bad_fatal,
                "detail": f"安定型ペアスコア={good_score}, 不安×回避のfatal_flaw={bad_fatal}"
            }
        except Exception as e:
            return {"test": "compatibility_engine", "passed": False, "error": str(e)}

    async def _test_simulation_api(self) -> dict:
        """テスト3: フルシミュレーションAPI（タイムアウト120秒）"""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                payload = {
                    "user_a_id": QA_TEST_PAIR["user_a"]["id"],
                    "user_b_id": QA_TEST_PAIR["user_b"]["id"],
                    "agent_a_prompt": "テスト用プロンプトA",
                    "agent_b_prompt": "テスト用プロンプトB",
                    "user_a_data": QA_TEST_PAIR["user_a"],
                    "user_b_data": QA_TEST_PAIR["user_b"],
                }
                resp = await client.post(f"{BACKEND_URL}/api/v1/simulate", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    score = data.get("compatibility_score", -1)
                    score_ok = 0 <= score <= 100
                    anomaly = score == 0.0 or score == 100.0
                    return {
                        "test": "simulation_api",
                        "passed": score_ok and not anomaly,
                        "score": score,
                        "anomaly": anomaly,
                        "status_text": data.get("status", "")
                    }
                else:
                    return {"test": "simulation_api", "passed": False, "http_status": resp.status_code, "error": resp.text[:200]}
        except Exception as e:
            return {"test": "simulation_api", "passed": False, "error": str(e)}

    async def run_task(self, context: dict = {}) -> dict:
        bus = MessageBus()
        store = MemoryStore()
        errors = []

        # テスト実行（速い順）
        health_result    = await self._test_health()
        engine_result    = await self._test_compatibility_engine()
        # フルシミュレーションはオプション（contextで制御）
        run_full_sim = context.get("full_simulation", False)
        sim_result = None
        if run_full_sim:
            sim_result = await self._test_simulation_api()

        results = [health_result, engine_result]
        if sim_result:
            results.append(sim_result)

        # エラー集計
        if not health_result.get("passed"):
            errors.append(f"ヘルスチェック失敗: {health_result.get('error', health_result.get('status'))}")
        if not engine_result.get("passed"):
            errors.append(f"相性エンジン異常: {engine_result.get('detail', engine_result.get('error'))}")
        if sim_result and not sim_result.get("passed"):
            errors.append(f"シミュレーションAPI失敗: {sim_result.get('error', sim_result.get('http_status'))}")

        passed_count = sum(1 for r in results if r.get("passed"))
        total = len(results)

        # KPI記録
        engine_score = engine_result.get("good_score")
        if engine_score is not None:
            await store.save_kpi("qa_engine_score_stable_pair", float(engine_score))
        await store.save_kpi("qa_pass_rate", round(passed_count / total * 100, 1))

        # CEOへ報告（問題あり）
        if errors:
            report_text = f"QAテスト {passed_count}/{total} 合格\n\n問題点:\n" + "\n".join(errors)
            await bus.report_to_ceo("qa", report_text, {"results": results, "errors": errors})
            if not health_result.get("passed"):
                await bus.alert_owner("qa", "🚨 バックエンド障害検知",
                    f"ヘルスチェックが失敗しました。サーバーが停止している可能性があります。\n詳細: {errors}")

        # AI分析（Haiku）
        detail_str = "\n".join([
            f"- {r['test']}: {'✅' if r.get('passed') else '❌'} {r.get('detail', r.get('error', ''))}"
            for r in results
        ])
        analysis_prompt = f"""QAテスト結果（{passed_count}/{total} 合格）:
{detail_str}

問題があれば原因と対処法を、なければ「✅ 正常稼働中」と一言で報告してください。"""

        analysis = await self.call_llm(analysis_prompt, max_tokens=300)

        return {
            "tests_passed": passed_count,
            "tests_total": total,
            "errors": errors,
            "results": results,
            "analysis": analysis,
            "engine_score": engine_score,
        }
