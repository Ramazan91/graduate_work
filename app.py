from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, date
import calendar as pycalendar
from flask import Flask, render_template, request
from translations import translations

import os

app = Flask(__name__)

DB_PATH = "tasks.db"

# подключение к базе
def get_db_connection(DATABASE=None):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# переводчик (доступен во всех шаблонах как t["..."])
@app.context_processor
def inject_translations():
    lang = request.args.get("lang", "ru")
    return dict(
        t=translations.get(lang, translations["ru"]),
        current_lang=lang
    )


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Создаём таблицу, если нет
    conn = get_db_connection()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT, -- ISO формат YYYY-MM-DD
            complete INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        )"""
    )
    conn.commit()

    # Лёгкая миграция на случай старой схемы
    # (если база уже была, добавим недостающие колонки)
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    def ensure_col(name, ddl):
        if name not in cols:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {ddl}")
            conn.commit()

    ensure_col("description", "description TEXT")
    ensure_col("due_date", "due_date TEXT")
    ensure_col("created_at", "created_at TEXT DEFAULT (datetime('now'))")
    ensure_col("completed_at", "completed_at TEXT")

    conn.close()

init_db()

@app.template_filter("human_date")
def human_date(value):
    """Рендерим YYYY-MM-DD в DD.MM.YYYY"""
    if not value:
        return ""
    try:
        d = datetime.strptime(value, "%Y-%m-%d").date()
        return d.strftime("%d.%m.%Y")
    except Exception:
        return value

def is_overdue(task):
    if task["complete"]:
        return False
    due = task["due_date"]
    if not due:
        return False
    try:
        d = datetime.strptime(due, "%Y-%m-%d").date()
        return d < date.today()
    except:
        return False

def is_today(task):
    due = task["due_date"]
    if not due:
        return False
    try:
        d = datetime.strptime(due, "%Y-%m-%d").date()
        return d == date.today()
    except:
        return False

@app.route("/")
def index():
    conn = get_db_connection()
    tasks = conn.execute(
        "SELECT * FROM tasks ORDER BY complete ASC, due_date IS NULL, due_date ASC, id DESC"
    ).fetchall()
    conn.close()

    # Для простого баннера-напоминания: есть ли задачи на сегодня
    has_today = any(is_today(t) and not t["complete"] for t in tasks)
    return render_template("index.html", tasks=tasks, is_overdue=is_overdue, is_today=is_today, has_today=has_today)

@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_date = request.form.get("due_date", "").strip() or None
    if title:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO tasks (title, description, due_date) VALUES (?, ?, ?)",
            (title, description, due_date)
        )
        conn.commit()
        conn.close()
    return redirect(url_for("index"))

@app.route("/complete/<int:task_id>")
def complete(task_id):
    conn = get_db_connection()
    conn.execute(
        "UPDATE tasks SET complete = 1, completed_at = datetime('now') WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/uncomplete/<int:task_id>")
def uncomplete(task_id):
    conn = get_db_connection()
    conn.execute(
        "UPDATE tasks SET complete = 0, completed_at = NULL WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/delete/<int:task_id>")
def delete(task_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/calendar")
def calendar_view():
    # Текущий месяц/год
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))

    # Достаём все задачи с датой в этом месяце
    month_start = f"{year:04d}-{month:02d}-01"
    # Вычислим конец месяца
    _, last_day = pycalendar.monthrange(year, month)
    month_end = f"{year:04d}-{month:02d}-{last_day:02d}"

    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT * FROM tasks
        WHERE due_date IS NOT NULL
          AND due_date >= ?
          AND due_date <= ?
        ORDER BY due_date ASC, complete ASC
        """,
        (month_start, month_end),
    ).fetchall()
    conn.close()

    # Сгруппируем по дате
    by_date = {}
    for r in rows:
        by_date.setdefault(r["due_date"], []).append(r)

    cal = pycalendar.monthcalendar(year, month)  # списки недель, 0 = пустая ячейка
    month_name = pycalendar.month_name[month]

    return render_template(
        "calendar.html",
        cal=cal,
        year=year,
        month=month,
        month_name=month_name,
        by_date=by_date,
        today=today,
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

