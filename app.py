"""Todoリストアプリ (Flask + Google Sheets)"""

import calendar
import os
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, url_for

import storage

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")


def _darken(hex_color, ratio=0.85):
    """RCDL規定のhover色（15% darken）を算出する。"""
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return "#{:02X}{:02X}{:02X}".format(int(r * ratio), int(g * ratio), int(b * ratio))


# テーマカラー定義（デザイン仕様書 §7）。redのhoverのみRCDL公式値。
THEMES = {
    "red": {"name": "レッド", "primary": "#E2001A", "hover": "#BD0016"},
    "blue": {"name": "ロイヤルブルー", "primary": "#0057B8", "hover": _darken("#0057B8")},
    "teal": {"name": "ティールグリーン", "primary": "#00857C", "hover": _darken("#00857C")},
    "forest": {"name": "フォレストグリーン", "primary": "#2E7D32", "hover": _darken("#2E7D32")},
    "indigo": {"name": "インディゴ", "primary": "#4F46E5", "hover": _darken("#4F46E5")},
    "navy": {"name": "ネイビー", "primary": "#1F4E79", "hover": _darken("#1F4E79")},
    "purple": {"name": "パープル", "primary": "#7B1FA2", "hover": _darken("#7B1FA2")},
    "rose": {"name": "ローズ", "primary": "#C2185B", "hover": _darken("#C2185B")},
    "brown": {"name": "ブラウン", "primary": "#6D4C41", "hover": _darken("#6D4C41")},
    "slate": {"name": "スレートグレー", "primary": "#37474F", "hover": _darken("#37474F")},
}

REPEAT_LABELS = {"weekly": "毎週", "monthly": "毎月"}

_store = None


def get_store():
    global _store
    if _store is None:
        _store = storage.create_store()
    return _store


def validate(form):
    """フォーム値を検証し (values, errors) を返す。"""
    title = form.get("title", "").strip()
    content = form.get("content", "").strip()
    due_date = form.get("due_date", "").strip()
    repeat = form.get("repeat", "").strip()
    errors = {}
    if not title:
        errors["title"] = "タイトルを入力してください。"
    elif len(title) > 100:
        errors["title"] = "タイトルは100文字以内で入力してください。"
    if len(content) > 1000:
        errors["content"] = "内容は1000文字以内で入力してください。"
    if due_date:
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            errors["due_date"] = "期日は YYYY-MM-DD 形式で入力してください。"
    if repeat not in ("", "weekly", "monthly"):
        errors["repeat"] = "繰り返しの指定が不正です。"
    elif repeat and not due_date:
        errors["due_date"] = "繰り返しを設定する場合は期日を入力してください。"
    return {"title": title, "content": content, "due_date": due_date, "repeat": repeat}, errors


def next_due_date(due_str, repeat):
    """繰り返しタスクの次回期日を返す（要件定義書 F-12）。"""
    d = datetime.strptime(due_str, "%Y-%m-%d").date()
    today = date.today()
    while True:
        if repeat == "weekly":
            d = d + timedelta(days=7)
        else:  # monthly: 翌月同日、月末超過はその月の末日
            year = d.year + (1 if d.month == 12 else 0)
            month = 1 if d.month == 12 else d.month + 1
            day = min(d.day, calendar.monthrange(year, month)[1])
            d = date(year, month, day)
        if d >= today:
            return d.isoformat()


@app.template_filter("jp_date")
def jp_date(value):
    """'2026-09-20' -> '2026年9月20日'"""
    try:
        d = datetime.strptime(value, "%Y-%m-%d").date()
        return f"{d.year}年{d.month}月{d.day}日"
    except (ValueError, TypeError):
        return value


@app.context_processor
def inject_globals():
    store = get_store()
    settings = store.get_settings()
    theme = THEMES.get(settings.get("theme"), THEMES["red"])
    return {
        "today": date.today().isoformat(),
        "using_sheets": store.is_sheets,
        "settings": settings,
        "theme": theme,
        "repeat_labels": REPEAT_LABELS,
    }


@app.route("/")
def index():
    store = get_store()
    todos = store.list_todos()
    todos.sort(
        key=lambda t: (
            t["status"] == "done",
            t["due_date"] == "",
            t["due_date"],
            t["created_at"],
        )
    )
    due_todos = [
        t
        for t in todos
        if t["status"] != "done" and t["due_date"] and t["due_date"] <= date.today().isoformat()
    ]
    return render_template("index.html", todos=todos, due_todos=due_todos)


@app.route("/todos/new", methods=["GET", "POST"])
def new_todo():
    if request.method == "POST":
        values, errors = validate(request.form)
        if errors:
            return render_template("form.html", todo=values, errors=errors, mode="new")
        get_store().add_todo(
            values["title"], values["content"], values["due_date"], values["repeat"]
        )
        flash("やることを登録しました。", "success")
        return redirect(url_for("index"))
    return render_template("form.html", todo=None, errors={}, mode="new")


@app.route("/todos/<todo_id>/edit", methods=["GET", "POST"])
def edit_todo(todo_id):
    store = get_store()
    todo = store.get_todo(todo_id)
    if todo is None:
        abort(404)
    if request.method == "POST":
        values, errors = validate(request.form)
        if errors:
            values["id"] = todo_id
            return render_template("form.html", todo=values, errors=errors, mode="edit")
        store.update_todo(todo_id, **values)
        flash("やることを更新しました。", "success")
        return redirect(url_for("index"))
    return render_template("form.html", todo=todo, errors={}, mode="edit")


@app.route("/todos/<todo_id>/toggle", methods=["POST"])
def toggle_todo(todo_id):
    store = get_store()
    todo = store.get_todo(todo_id)
    if todo is None:
        abort(404)
    new_status = "open" if todo["status"] == "done" else "done"
    store.update_todo(todo_id, status=new_status)
    # 繰り返しタスクの完了時は次回タスクを自動生成する（F-12）
    if new_status == "done" and todo.get("repeat") in REPEAT_LABELS and todo["due_date"]:
        next_due = next_due_date(todo["due_date"], todo["repeat"])
        store.add_todo(todo["title"], todo["content"], next_due, todo["repeat"])
        label = REPEAT_LABELS[todo["repeat"]]
        flash(
            f"完了にしました。{label}の繰り返し設定により、次回（期日: {next_due}）のタスクを作成しました。",
            "success",
        )
    else:
        flash("完了にしました。" if new_status == "done" else "未完了に戻しました。", "success")
    return redirect(url_for("index"))


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    store = get_store()
    if request.method == "POST":
        theme = request.form.get("theme", "red")
        if theme not in THEMES:
            theme = "red"
        reminder = "on" if request.form.get("reminder") == "on" else "off"
        store.save_settings({"theme": theme, "reminder": reminder})
        flash("設定を保存しました。", "success")
        return redirect(url_for("settings_page"))
    return render_template("settings.html", themes=THEMES)


@app.route("/todos/<todo_id>/delete", methods=["POST"])
def delete_todo(todo_id):
    if get_store().delete_todo(todo_id):
        flash("やることを削除しました。", "success")
    else:
        flash("対象が見つかりませんでした。", "error")
    return redirect(url_for("index"))


@app.errorhandler(Exception)
def handle_error(e):
    from werkzeug.exceptions import HTTPException

    if isinstance(e, HTTPException):
        return e
    app.logger.exception("Unhandled error")
    return render_template("error.html", message=str(e)), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
