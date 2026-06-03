"""
register_tasks.py — Windowsタスクスケジューラ登録スクリプト
管理者権限不要。ユーザーのタスクスケジューラに登録する。

使い方:
  cd backend
  python scripts/register_tasks.py
"""
import subprocess
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TASKS = [
    {
        "name": "Persona_DailyRunner",
        "bat": os.path.join(BACKEND_DIR, "scripts", "daily_runner.bat"),
        "schedule": "/SC DAILY /ST 06:00",
        "desc": "Persona 日次タスク（SNS投稿・コスト監視）毎朝6時",
    },
    {
        "name": "Persona_WeeklyKPI",
        "bat": os.path.join(BACKEND_DIR, "scripts", "weekly_kpi_report.bat"),
        "schedule": "/SC WEEKLY /D MON /ST 07:00",
        "desc": "Persona 週次KPIレポート 毎週月曜7時",
    },
]


def register():
    for t in TASKS:
        bat_path = t["bat"]
        # batファイルがなければスキップ
        if not os.path.exists(bat_path):
            print(f"⚠️ スキップ: {bat_path} が見つかりません")
            continue

        cmd = (
            f'schtasks /Create /TN "{t["name"]}" '
            f'/TR "\\""{bat_path}\\"" " '
            f'{t["schedule"]} /F'
        )
        print(f"📋 登録中: {t['name']} ({t['desc']})")
        print(f"   コマンド: {cmd}")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ 登録成功")
        else:
            # schtasksが失敗した場合、代替としてスタートアップフォルダにショートカット
            print(f"   ⚠️ schtasks失敗（管理者権限が必要かも）: {result.stderr.strip()}")
            print(f"   → 手動登録してください:")
            print(f"     1. Win+R → taskschd.msc")
            print(f"     2. 「タスクの作成」→ 名前: {t['name']}")
            print(f"     3. トリガー: {t['schedule']}")
            print(f"     4. 操作: {bat_path}")
        print()


def list_tasks():
    """登録済みのPersonaタスクを表示"""
    result = subprocess.run(
        'schtasks /Query /FO LIST /V /TN "Persona_*"',
        shell=True, capture_output=True, text=True
    )
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("Personaタスクは登録されていません。")


if __name__ == "__main__":
    print("=" * 50)
    print("🏢 Persona タスクスケジューラ登録")
    print("=" * 50)
    print()
    register()
    print()
    print("=" * 50)
    print("📋 登録済みタスク一覧:")
    print("=" * 50)
    list_tasks()
