from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# --- функция для подключения к БД ---
def get_db_connection():
    conn = sqlite3.connect("tasks.db")
    conn.row_factory = sqlite3.Row
    return conn

# --- создаём таблицу, если её нет ---
def init_db():
    conn = get_db_connection()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            complete BOOLEAN NOT NULL DEFAULT 0
        )"""
    )
    conn.commit()
    conn.close()

init_db()

# --- главная страница ---
@app.route("/")
def index():
    conn = get_db_connection()
    tasks = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return render_template("index.html", tasks=tasks)

# --- добавить задачу ---
@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title")
    if title:
        conn = get_db_connection()
        conn.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
        conn.commit()
        conn.close()
    return redirect(url_for("index"))

# --- отметить задачу выполненной ---
@app.route("/complete/<int:task_id>")
def complete(task_id):
    conn = get_db_connection()
    conn.execute("UPDATE tasks SET complete = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# --- удалить задачу ---
@app.route("/delete/<int:task_id>")
def delete(task_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
