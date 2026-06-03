"""
BaseAgent — 全エージェントの抽象基底クラス
CEO判断: モデル3層制を実装済み
  Tier A (Haiku)  : QA, 経理, 総務, CS
  Tier B (Sonnet) : CPO, CMO, Research, CFO
  Tier C (Opus)   : CEO, Legal
"""
from __future__ import annotations
import asyncio
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional
import anthropic
from dotenv import load_dotenv

load_dotenv()

# モデル3層制 (CEO判断 #001)
MODEL_TIERS = {
    "haiku":  "claude-haiku-4-5",
    "sonnet": "claude-sonnet-4-6",
    "opus":   "claude-opus-4-5",
}

AGENT_MODEL_MAP = {
    "ceo":        MODEL_TIERS["opus"],
    "legal":      MODEL_TIERS["opus"],
    "cfo":        MODEL_TIERS["sonnet"],
    "cpo":        MODEL_TIERS["sonnet"],
    "cmo":        MODEL_TIERS["sonnet"],
    "research":   MODEL_TIERS["sonnet"],
    "cto":        MODEL_TIERS["sonnet"],
    "qa":         MODEL_TIERS["haiku"],
    "accounting": MODEL_TIERS["haiku"],
    "cs":         MODEL_TIERS["haiku"],
    "ga":         MODEL_TIERS["haiku"],
}

class BaseAgent(ABC):
    """全エージェントの抽象基底クラス"""
    
    def __init__(self, agent_id: str, display_name: str, department: str):
        self.agent_id = agent_id
        self.display_name = display_name
        self.department = department
        self.model = AGENT_MODEL_MAP.get(agent_id, MODEL_TIERS["sonnet"])
        self.client = anthropic.AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self._last_run: Optional[datetime] = None
        self._is_running: bool = False

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """エージェント固有のシステムプロンプト"""
        ...

    @abstractmethod
    async def run_task(self, context: dict = {}) -> dict:
        """メインタスクを実行して結果を返す"""
        ...

    async def call_llm(self, user_message: str, max_tokens: int = 1000) -> str:
        """LLMを呼び出してテキストを返す共通メソッド"""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=self.system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )
            return response.content[0].text
        except Exception as e:
            return f"[{self.display_name}] エラー: {str(e)}"

    async def execute(self, context: dict = {}) -> dict:
        """エージェント実行ラッパー（ログ記録・エラーハンドリング付き）"""
        from agent_system.memory_store import MemoryStore
        
        self._is_running = True
        started_at = datetime.now(timezone.utc)
        
        try:
            result = await self.run_task(context)
            status = "success"
        except Exception as e:
            result = {"error": str(e)}
            status = "error"
        finally:
            self._is_running = False
            self._last_run = datetime.now(timezone.utc)

        # 実行ログをMemoryStoreに保存
        log_entry = {
            "agent_id": self.agent_id,
            "agent_name": self.display_name,
            "department": self.department,
            "status": status,
            "result": result,
            "started_at": started_at.isoformat(),
            "finished_at": self._last_run.isoformat(),
            "model_used": self.model,
        }
        
        store = MemoryStore()
        await store.save_log(log_entry)
        
        return log_entry

    def status(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "department": self.department,
            "model": self.model,
            "is_running": self._is_running,
            "last_run": self._last_run.isoformat() if self._last_run else None,
        }
