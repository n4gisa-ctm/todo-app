"""Todoリストアプリ (Flask + Google Sheets)"""

import os
from datetime import date, datetime

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, url_for

import storage

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

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
    return {"title": title, "content": content, "due_date": due_date}, errors


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
    return {
        "today": date.today().isoformat(),
        "using_sheets": get_store().is_sheets,
    }


@app.route("/")
def index():
    todos = get_store().list_todos()
    todos.sort(
        key=lambda t: (
            t["status"] == "done",
            t["due_date"] == "",
            t["due_date"],
            t["created_at"],
        )
    )
    return render_template("index.html", todos=todos)


@app.route("/todos/new", methods=["GET", "POST"])
def new_todo():
    if request.method == "POST":
        values, errors = validate(request.form)
        if errors:
            return render_template("form.html", todo=values, errors=errors, mode="new")
        get_store().add_todo(values["title"], values["content"], values["due_date"])
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
    flash("完了にしました。" if new_status == "done" else "未完了に戻しました。", "success")
    return redirect(url_for("index"))


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
