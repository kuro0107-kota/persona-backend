"""
MemoryStore — エージェント共有メモリ（SQLiteベース）
エージェント実行ログ・メッセージ・KPIデータを永続化する
"""
from __future__ import annotations
import json
import os
import aiosqlite
from datetime import datetime, timezone
from typing import Any, Optional

# 既存のproxywar.dbと同じディレクトリに配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DB_PATH = os.path.join(BASE_DIR, "agent_memory.db")


class MemoryStore:
    """エージェント間共有メモリストア"""

    def _get_conn(self):
        """aiosqlite接続コンテキストマネージャを返す"""
        return aiosqlite.connect(AGENT_DB_PATH)

    async def initialize(self):
        """テーブル初期化"""
        async with self._get_conn() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    agent_name TEXT,
                    department TEXT,
                    status TEXT,
                    result_json TEXT,
                    model_used TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS agent_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_agent TEXT NOT NULL,
                    to_agent TEXT NOT NULL,
                    message_type TEXT,
                    content_json TEXT,
                    priority INTEGER DEFAULT 1,
                    requires_approval INTEGER DEFAULT 0,
                    approved INTEGER DEFAULT -1,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS kpi_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    metadata_json TEXT,
                    recorded_at TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS weekly_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    week_label TEXT,
                    report_text TEXT,
                    created_by TEXT DEFAULT 'ceo',
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.commit()

    async def save_log(self, log: dict):
        async with self._get_conn() as db:
            await db.execute("""
                INSERT INTO agent_logs
                (agent_id, agent_name, department, status, result_json, model_used, started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log.get("agent_id"),
                log.get("agent_name"),
                log.get("department"),
                log.get("status"),
                json.dumps(log.get("result", {}), ensure_ascii=False),
                log.get("model_used"),
                log.get("started_at"),
                log.get("finished_at"),
            ))
            await db.commit()

    async def get_logs(self, agent_id: Optional[str] = None, limit: int = 50) -> list:
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            if agent_id:
                cursor = await db.execute(
                    "SELECT * FROM agent_logs WHERE agent_id=? ORDER BY id DESC LIMIT ?",
                    (agent_id, limit)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM agent_logs ORDER BY id DESC LIMIT ?", (limit,)
                )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def send_message(self, msg: dict):
        async with self._get_conn() as db:
            await db.execute("""
                INSERT INTO agent_messages
                (from_agent, to_agent, message_type, content_json, priority, requires_approval)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                msg.get("from_agent"),
                msg.get("to_agent"),
                msg.get("message_type"),
                json.dumps(msg.get("content", {}), ensure_ascii=False),
                msg.get("priority", 1),
                1 if msg.get("requires_approval") else 0,
            ))
            await db.commit()

    async def get_messages(self, to_agent: Optional[str] = None, limit: int = 50) -> list:
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            if to_agent:
                cursor = await db.execute(
                    "SELECT * FROM agent_messages WHERE to_agent=? OR to_agent='all' ORDER BY priority DESC, id DESC LIMIT ?",
                    (to_agent, limit)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM agent_messages ORDER BY priority DESC, id DESC LIMIT ?", (limit,)
                )
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["content"] = json.loads(d.get("content_json") or "{}")
                result.append(d)
            return result

    async def approve_message(self, message_id: int, approved: bool):
        async with self._get_conn() as db:
            await db.execute(
                "UPDATE agent_messages SET approved=? WHERE id=?",
                (1 if approved else 0, message_id)
            )
            await db.commit()

    async def save_kpi(self, metric_name: str, value: float, metadata: dict = {}):
        async with self._get_conn() as db:
            await db.execute(
                "INSERT INTO kpi_snapshots (metric_name, metric_value, metadata_json) VALUES (?, ?, ?)",
                (metric_name, value, json.dumps(metadata, ensure_ascii=False))
            )
            await db.commit()

    async def get_kpis(self, metric_name: Optional[str] = None, limit: int = 100) -> list:
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            if metric_name:
                cursor = await db.execute(
                    "SELECT * FROM kpi_snapshots WHERE metric_name=? ORDER BY id DESC LIMIT ?",
                    (metric_name, limit)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM kpi_snapshots ORDER BY id DESC LIMIT ?", (limit,)
                )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def save_weekly_report(self, week_label: str, report_text: str):
        async with self._get_conn() as db:
            await db.execute(
                "INSERT INTO weekly_reports (week_label, report_text) VALUES (?, ?)",
                (week_label, report_text)
            )
            await db.commit()

    async def get_weekly_reports(self, limit: int = 10) -> list:
        async with self._get_conn() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM weekly_reports ORDER BY id DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
