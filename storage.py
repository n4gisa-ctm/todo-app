"""Todoデータの永続化層。

Google スプレッドシート（gspread + サービスアカウント）を正とし、
認証情報が未設定の場合はローカルJSONファイルにフォールバックする。
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

HEADERS = ["id", "title", "content", "due_date", "status", "created_at", "updated_at"]
WORKSHEET_NAME = "todos"

_LOCAL_FILE = Path(__file__).parent / "data" / "todos.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class LocalStore:
    """開発用フォールバック: data/todos.json に保存する。"""

    is_sheets = False

    def _load(self):
        if _LOCAL_FILE.exists():
            return json.loads(_LOCAL_FILE.read_text(encoding="utf-8"))
        return []

    def _save(self, todos):
        _LOCAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LOCAL_FILE.write_text(
            json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_todos(self):
        return self._load()

    def get_todo(self, todo_id):
        return next((t for t in self._load() if t["id"] == todo_id), None)

    def add_todo(self, title, content, due_date):
        todos = self._load()
        todo = {
            "id": uuid.uuid4().hex,
            "title": title,
            "content": content,
            "due_date": due_date,
            "status": "open",
            "created_at": _now(),
            "updated_at": _now(),
        }
        todos.append(todo)
        self._save(todos)
        return todo

    def update_todo(self, todo_id, **fields):
        todos = self._load()
        for t in todos:
            if t["id"] == todo_id:
                t.update({k: v for k, v in fields.items() if k in HEADERS})
                t["updated_at"] = _now()
                self._save(todos)
                return t
        return None

    def delete_todo(self, todo_id):
        todos = self._load()
        remaining = [t for t in todos if t["id"] != todo_id]
        self._save(remaining)
        return len(remaining) != len(todos)


class SheetsStore:
    """Google スプレッドシートに保存する本番用ストア。"""

    is_sheets = True

    def __init__(self, credentials_info, spreadsheet_id):
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(spreadsheet_id)
        try:
            self.ws = spreadsheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            self.ws = spreadsheet.add_worksheet(WORKSHEET_NAME, rows=1000, cols=len(HEADERS))
        if self.ws.row_values(1) != HEADERS:
            self.ws.update(values=[HEADERS], range_name="A1")

    def _rows(self):
        """(行番号, dict) のリストを返す。2行目以降がデータ。"""
        values = self.ws.get_all_values()
        rows = []
        for i, row in enumerate(values[1:], start=2):
            if not any(row):
                continue
            padded = row + [""] * (len(HEADERS) - len(row))
            rows.append((i, dict(zip(HEADERS, padded))))
        return rows

    def list_todos(self):
        return [t for _, t in self._rows()]

    def get_todo(self, todo_id):
        return next((t for _, t in self._rows() if t["id"] == todo_id), None)

    def add_todo(self, title, content, due_date):
        todo = {
            "id": uuid.uuid4().hex,
            "title": title,
            "content": content,
            "due_date": due_date,
            "status": "open",
            "created_at": _now(),
            "updated_at": _now(),
        }
        self.ws.append_row([todo[h] for h in HEADERS], value_input_option="RAW")
        return todo

    def update_todo(self, todo_id, **fields):
        for row_num, todo in self._rows():
            if todo["id"] == todo_id:
                todo.update({k: v for k, v in fields.items() if k in HEADERS})
                todo["updated_at"] = _now()
                self.ws.update(
                    values=[[todo[h] for h in HEADERS]],
                    range_name=f"A{row_num}:G{row_num}",
                    value_input_option="RAW",
                )
                return todo
        return None

    def delete_todo(self, todo_id):
        for row_num, todo in self._rows():
            if todo["id"] == todo_id:
                self.ws.delete_rows(row_num)
                return True
        return False


def create_store():
    """環境変数からストアを構築する。

    GOOGLE_CREDENTIALS_JSON: サービスアカウントJSONの中身、またはJSONファイルへのパス
    SPREADSHEET_ID: 保存先スプレッドシートのID
    どちらかが未設定ならローカルJSONにフォールバックする。
    """
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "").strip()
    if not raw or not spreadsheet_id:
        return LocalStore()

    if raw.startswith("{"):
        info = json.loads(raw)
    else:
        info = json.loads(Path(raw).read_text(encoding="utf-8"))
    return SheetsStore(info, spreadsheet_id)
