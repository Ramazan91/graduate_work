# Импортируем необходимые объекты из Flask — приложение, рендеринг шаблонов,
# объект request для доступа к данным запроса, redirect и url_for для перенаправлений.
from flask import Flask, render_template, request, redirect, url_for

# Подключаем sqlite3 для работы с локальной файловой базой данных SQLite.
import sqlite3

# Импортируем инструменты для работы с датой и временем.
from datetime import datetime, date

# Импортируем модуль calendar под именем pycalendar, чтобы избежать коллизий с переменными month/weekday.
import calendar as pycalendar

# Закомментированный импорт оставлен в исходнике — возможно, использовался ранее или для заметки.
# from flask import Flask, render_template, request

# Импортируем словарь переводов из файла translations.py. Ожидается, что там есть dict translations.
from translations import translations

# Модуль os импортирован — может понадобиться для путей или env-переменных (в текущем коде прямо не используется).
import os

# Создаём экземпляр Flask-приложения. __name__ помогает Flask находить ресурсы и шаблоны.
app = Flask(__name__)

# Константа с путём к файлу базы данных SQLite (в той же директории, где запускается скрипт).
DB_PATH = "tasks.db"


# Контекст-процессор — добавляет переменные в контекст всех шаблонов автоматически.
@app.context_processor  # Декоратор
def inject_translations():
    # Получаем язык из query-параметров, например ?lang=en, по умолчанию 'ru'.
    lang = request.args.get("lang", "ru")
    # Возвращаем словарь, который будет доступен во всех шаблонах как переменные.
    # t — выбранный набор переводов, current_lang — код текущего языка.
    return dict(
        t=translations.get(lang, translations["ru"]),
        current_lang=lang
    )


# Утилитарная функция для открытия соединения с SQLite.
def get_db_connection():
    # Открываем соединение с файлом базы данных (создастся, если отсутствует).
    conn = sqlite3.connect(DB_PATH)
    # Устанавливаем row_factory в sqlite3.Row — это позволяет обращаться к колонкам
    # результата как к словарю: row['title'] или row['due_date'].
    conn.row_factory = sqlite3.Row
    return conn


# Функция инициализации БД: создаёт таблицу и делает простую миграцию схемы при необходимости.
def init_db():
    # Создаём/открываем соединение
    conn = get_db_connection()

    # Создаём таблицу tasks, если она ещё не существует. Объяснение колонок:
    # - id: первичный ключ, автоинкремент
    # - title: заголовок задачи, обязательный
    # - description: дополнительное описание (nullable)
    # - due_date: дата выполнения в ISO формате YYYY-MM-DD (nullable)
    # - complete: флаг выполнения (0/1), по умолчанию 0
    # - created_at: дата создания, по умолчанию текущая дата/время (SQLite datetime('now'))
    # - completed_at: дата завершения (nullable)
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
    # Сохраняем изменения (создание таблицы)
    conn.commit()

    # Простая миграция: получаем список колонок в таблице tasks
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()]

    # Вложенная функция для добавления колонки, если её нет в текущей схеме.
    def ensure_col(name, ddl):
        # Если колонка отсутствует в списке, выполняем ALTER TABLE для её добавления.
        if name not in cols:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {ddl}")
            conn.commit()

    # Гарантируем наличие колонок (это безопасно, если таблица новая — ensure_col ничего не сделает).
    ensure_col("description", "description TEXT")
    ensure_col("due_date", "due_date TEXT")
    ensure_col("created_at", "created_at TEXT DEFAULT (datetime('now'))")
    ensure_col("completed_at", "completed_at TEXT")

    # Закрываем соединение с базой.
    conn.close()


# Вызываем инициализацию БД при старте модуля (автоматически создаст файл/таблицу при запуске приложения).
init_db()


# Регистрируем пользовательский фильтр для шаблонов Jinja: human_date
@app.template_filter("human_date")
def human_date(value):
    """Рендерим YYYY-MM-DD в DD.MM.YYYY"""
    # Если значение пустое или None — возвращаем пустую строку (чтобы шаблон не показывал 'None').
    if not value:
        return ""
    try:
        # Парсим строковую дату в объект date
        d = datetime.strptime(value, "%Y-%m-%d").date()
        # Возвращаем в человекочитаемом формате
        return d.strftime("%d.%m.%Y")
    except Exception:
        # Если формат не тот, возвращаем оригинальное значение (без падения приложения).
        return value


# Проверяет, просрочена ли задача (True если дата меньше сегодняшней и задача не выполнена).
def is_overdue(task):
    # Если задача помечена как complete, она не считается просроченной.
    if task["complete"]:
        return False
    # Получаем дату из задачи
    due = task["due_date"]
    # Если даты нет — не просрочено
    if not due:
        return False
    try:
        # Парсим дату и сравниваем с сегодняшней
        d = datetime.strptime(due, "%Y-%m-%d").date()
        return d < date.today()
    except:
        # При ошибке парсинга считаем, что не просрочено (без падения программы).
        return False


# Проверяет, стоит ли задача на сегодня
def is_today(task):
    due = task["due_date"]
    if not due:
        return False
    try:
        d = datetime.strptime(due, "%Y-%m-%d").date()
        return d == date.today()
    except:
        return False


# Главная страница: список задач
@app.route("/")
def index():
    # Открываем соединение и получаем все задачи, упорядоченные так: незавершённые вверх,
    # затем задачи без due_date (чтобы пустые даты шли после заполненных), затем по due_date,
    # а затем по id по убыванию (чтобы новые задачи шли перед старыми при одинаковых датах).
    conn = get_db_connection()
    tasks = conn.execute(
        "SELECT * FROM tasks ORDER BY complete ASC, due_date IS NULL, due_date ASC, id DESC"
    ).fetchall()
    conn.close()

    # Для баннера-напоминания: проверяем, есть ли среди задач непомеченные как выполненные задачи на сегодня.
    has_today = any(is_today(t) and not t["complete"] for t in tasks)

    # Рендерим шаблон index.html, передаём список задач и утилиты для проверки дат.
    return render_template("index.html", tasks=tasks, is_overdue=is_overdue, is_today=is_today, has_today=has_today)


# Маршрут для добавления новой задачи (ожидает POST-запрос)
@app.route("/add", methods=["POST"])
def add():
    # Берём поля формы, применяем strip() для удаления лишних пробелов.
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    # Если поле due_date пустое, приводим его к None для вставки в БД.
    due_date = request.form.get("due_date", "").strip() or None

    # Если заголовок не пуст — вставляем задачу в базу
    if title:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO tasks (title, description, due_date) VALUES (?, ?, ?)",
            (title, description, due_date)
        )
        conn.commit()
        conn.close()
    # Перенаправляем обратно на главную страницу
    return redirect(url_for("index"))


# Пометить задачу как выполненную
@app.route("/complete/<int:task_id>")
def complete(task_id):
    conn = get_db_connection()
    # Устанавливаем флаг complete=1 и записываем время завершения c помощью SQLite datetime('now')
    conn.execute(
        "UPDATE tasks SET complete = 1, completed_at = datetime('now') WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


# Снять отметку о выполнении (отмена)
@app.route("/uncomplete/<int:task_id>")
def uncomplete(task_id):
    conn = get_db_connection()
    # Сбрасываем флаг complete и очищаем completed_at (NULL)
    conn.execute(
        "UPDATE tasks SET complete = 0, completed_at = NULL WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


# Удалить задачу
@app.route("/delete/<int:task_id>")
def delete(task_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


# Представление календаря — показывает задачи, привязанные к дням месяца
@app.route("/calendar")
def calendar_view():
    # Текущая дата для подсветки "сегодня"
    today = date.today()
    # Получаем год/месяц из query-параметров, если не указаны — берем текущие
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))

    # Начало месяца в формате YYYY-MM-DD
    month_start = f"{year:04d}-{month:02d}-01"
    # Находим последний день месяца с помощью calendar.monthrange
    _, last_day = pycalendar.monthrange(year, month)
    month_end = f"{year:04d}-{month:02d}-{last_day:02d}"

    # Получаем все задачи с датой в этом диапазоне (включительно)
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

    # Группируем задачи по строковой дате due_date: { '2025-10-05': [task1, task2], ... }
    by_date = {}
    for r in rows:
        by_date.setdefault(r["due_date"], []).append(r)

    # Формируем структуру календаря: список недель, где 0 означает пустую ячейку
    cal = pycalendar.monthcalendar(year, month)  # списки недель, 0 = пустая ячейка
    # Читабельное имя месяца (например, "October")
    month_name = pycalendar.month_name[month]

    # Рендерим шаблон calendar.html и передаём все необходимые данные
    return render_template(
        "calendar.html",
        cal=cal,
        year=year,
        month=month,
        month_name=month_name,
        by_date=by_date,
        today=today,
    )


# Запуск приложения в режиме разработки при непосредственном запуске файла
if __name__ == "__main__":
    # host 0.0.0.0 — слушать на всех интерфейсах; debug=True — автоматический перезапуск и подробные ошибки.
    app.run(host="0.0.0.0", port=5000, debug=True)
