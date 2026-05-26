
# Flask — мини веб-фреймворк для Python
# Через него создается сервер и HTTP API
from flask import Flask

# render_template возвращает HTML страницу пользователю
from flask import render_template

# request — чтение JSON из запроса
# jsonify — возврат JSON ответа
# send_file — отправка PDF файла пользователю
from flask import request, jsonify, send_file

# sqlite3 — встроенная база данных SQLite
# Не требует отдельной установки
import sqlite3

# os — работа с файлами и путями
import os

# io — создание виртуального файла в памяти
# Используется для PDF перед отправкой пользователю
import io

# re — встроенная библиотека Python для работы с регулярными выражениями
# то есть специальными шаблонами поиска текста
# В проекте используется для автоматического поиска маркеров вида {name} или {date} внутри HTML шаблона и их последующей замены на пользовательские значения
import re

# xhtml2pdf (pisa) — библиотека для генерации PDF из HTML
from xhtml2pdf import pisa


# Template — встроенный механизм шаблонизации строк в Python.
# Используется для безопасной и автоматической подстановки
# значений в HTML шаблон документа.
# В отличие от обычного replace(), Template работает
# как полноценный шаблонизатор и поддерживает template strings,
# добавленные в новых версиях Python.
from string import Template



# Flask приложение


# Создаем Flask приложение
# __name__ нужен Flask для поиска файлов проекта
app = Flask(__name__)



# База данных

# Полный путь к файлу SQLite базы данных
# database.db будет лежать рядом с app.py
DATABASE = os.path.join(
    os.path.dirname(__file__),
    "database.db"
)


def get_db():
    """
    Создает подключение к файлу базы данных SQLite
  Если файл database.db не существует — SQLite создаст его автоматически
 Возвращает объект подключения, через который выполняются SQL-запросы
    """

    # Открываем подключение к базе данных
    conn = sqlite3.connect(DATABASE)

    # Настройка:
    # строки из базы будут как словари
    # например row["name"]
    conn.row_factory = sqlite3.Row

    return conn


def init_db():
    """
    Создает таблицу templates для хранения шаблонов
 Таблица содержит три колонки: id (уникальный номер), name (название), content (HTML-код)
 Если таблица уже существует — запрос ничего не меняет
    """

    # Подключение к базе
    conn = get_db()

    # Создаем таблицу templates
    # IF NOT EXISTS — не создавать повторно
    conn.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)

    # Сохраняем изменения
    conn.commit()

    # Закрываем подключение
    conn.close()


# Создаем таблицу при запуске приложения
init_db()



# Главная страница



# GET /
# Возвращает HTML интерфейс приложения
@app.route("/")
def index():
    """
    Возвращает HTML-интерфейс — страницу с редактором шаблонов, кнопками и окном предпросмотра PDF
    Всё, что пользователь видит в браузере, идёт отсюда
    """

    # Flask ищет index.html в папке templates
    return render_template("index.html")



# API шаблонов


# GET /templates
# Возвращает список всех шаблонов
@app.route("/templates", methods=["GET"])
def get_templates():
    """
    Возвращает список всех сохранённых шаблонов в формате JSON
# Запрашивает все строки из таблицы templates, сортирует по id (новые сверху)
# Ответ содержит массив объектов: [{id, name, content}, ...]
    """

    # Подключение к базе
    conn = get_db()

    # Получаем все шаблоны
    # ORDER BY id DESC — новые сверху
    rows = conn.execute("""
        SELECT * FROM templates
        ORDER BY id DESC
    """).fetchall()

    # Закрываем подключение
    conn.close()

    # Итоговый список для JSON
    templates = []

    # Проходим по всем строкам из БД
    for row in rows:

        # Добавляем шаблон в список
        templates.append({
            "id": row["id"],
            "name": row["name"],
            "content": row["content"]
        })

    # Возвращаем JSON
    return jsonify(templates)


# POST /templates
# Создает новый шаблон
@app.route("/templates", methods=["POST"])
def create_template():
    """
 Создает новый шаблон и сохраняет его в базу данных
 Принимает JSON с полями name (название) и content (HTML-код с маркерами)
 Возвращает созданный шаблон с присвоенным id и статус 201 (Created)
    """

    # Читаем JSON из запроса
    data = request.get_json()

    # Проверка:
    # если JSON пустой — ошибка
    if not data:
        return jsonify({
            "error": "Пустой JSON"
        }), 400

    # Получаем название шаблона
    # если name нет — ставим "Без названия"
    name = data.get("name", "Без названия")

    # Получаем HTML шаблона
    content = data.get("content", "")

    # Подключение к базе
    conn = get_db()

    # Добавляем шаблон в таблицу
    cursor = conn.execute("""
        INSERT INTO templates (name, content)
        VALUES (?, ?)
    """, (name, content))

    # Сохраняем изменения
    conn.commit()

    # ID новой записи
    new_id = cursor.lastrowid

    # Закрываем подключение
    conn.close()

    # Возвращаем созданный шаблон
    return jsonify({
        "id": new_id,
        "name": name,
        "content": content
    }), 201


# GET /templates/{id}
# Возвращает один шаблон по ID
@app.route("/templates/<int:id>", methods=["GET"])
def get_template(id):
    """
Возвращает один конкретный шаблон по его ID
 Если шаблон с таким ID не найден — возвращает ошибку 404
 Ответ содержит объект: {id, name, content}
    """

    # Подключение к базе
    conn = get_db()

    # Ищем шаблон по id
    row = conn.execute("""
        SELECT * FROM templates
        WHERE id = ?
    """, (id,)).fetchone()

    # Закрываем подключение
    conn.close()

    # Если шаблон не найден
    if row is None:
        return jsonify({
            "error": "Шаблон не найден"
        }), 404

    # Возвращаем найденный шаблон
    return jsonify({
        "id": row["id"],
        "name": row["name"],
        "content": row["content"]
    })


# PUT /templates/{id}
# Обновляет существующий шаблон
@app.route("/templates/<int:id>", methods=["PUT"])
def update_template(id):
    """
 Обновляет существующий шаблон по ID
 Принимает JSON с новыми значениями name и content
 Полностью заменяет старые данные новыми
 Возвращает обновлённый объект: {id, name, content}

    """

    # Читаем JSON
    data = request.get_json()

    # Проверка пустого JSON
    if not data:
        return jsonify({
            "error": "Пустой JSON"
        }), 400

    # Новое название
    name = data.get("name")

    # Новый HTML
    content = data.get("content")

    # Подключение к базе
    conn = get_db()

    # Обновляем запись
    conn.execute("""
        UPDATE templates
        SET name = ?, content = ?
        WHERE id = ?
    """, (name, content, id))

    # Сохраняем изменения
    conn.commit()

    # Закрываем подключение
    conn.close()

    # Возвращаем обновленный шаблон
    return jsonify({
        "id": id,
        "name": name,
        "content": content
    })


# DELETE /templates/{id}
# Удаляет шаблон
@app.route("/templates/<int:id>", methods=["DELETE"])
def delete_template(id):
    """
     Удаляет шаблон из базы данных по ID
 Возвращает пустой ответ со статусом 204 (No Content — успешное удаление)
    """

    # Подключение к базе
    conn = get_db()

    # Удаляем запись по id
    conn.execute("""
        DELETE FROM templates
        WHERE id = ?
    """, (id,))

    # Сохраняем изменения
    conn.commit()

    # Закрываем подключение
    conn.close()

    # 204 — успешное удаление без ответа
    return "", 204



# Подстановка значений

def replace_markers(template_html, values):
    """
    Выполняет подстановку значений
    через template strings Python 3.14
    """

    # Преобразуем маркеры:
    # {name} -> ${name}

    converted_template = re.sub(
        r"\{([^}]+)\}",    # ищем { и всё внутри скобок до }, [^}]+ — любые символы кроме закрывающей скобки
        r"${\1}",          #Заменяем на ${то_что_нашли}
                          # \1 — вставляет найденный текст из первой группы (...)
        template_html     # Строка, в которой производим замену (исходный HTML шаблона)
    )

    # Создаем template объект
    template = Template(converted_template)

    # Подставляем значения
    result = template.substitute(values)

    return result



# HTML preview


# GET/POST /preview/{id}
# Возвращает HTML с подстановкой значений
@app.route("/preview/<int:id>", methods=["GET", "POST"])
def preview_template(id):
    """
    Возвращает HTML preview — показывает страницу с подставленными значениями.
PDF при этом не создаётся, просто смотрим, как будет выглядеть результат
    """

    # Получаем значения маркеров из JSON
    values = request.get_json() or {}

    # Подключение к базе
    conn = get_db()

    # Получаем шаблон по ID
    row = conn.execute("""
        SELECT * FROM templates
        WHERE id = ?
    """, (id,)).fetchone()

    # Закрываем подключение
    conn.close()

    # Если шаблон не найден
    if row is None:
        return jsonify({
            "error": "Шаблон не найден"
        }), 404

    # HTML шаблона
    template_html = row["content"]

    # Подстановка значений
    result_html = replace_markers(
        template_html,
        values
    )

    # Возвращаем готовый HTML
    return result_html



# Генерация PDF


# POST /render/{id}
# Генерирует PDF документ
@app.route("/render/<int:id>", methods=["POST"])
def render_pdf(id):

    """
    Генерирует PDF документ из шаблона с подставленными значениями

       Принимает JSON с парами ключ-значение для замены маркеров {key} в шаблоне
       Находит шаблон по ID, заменяет маркеры на значения, конвертирует HTML в PDF
       Возвращает готовый PDF файл для скачивания
  """


    # Получаем JSON значения
    values = request.get_json() or {}

    # Подключение к базе
    conn = get_db()

    # Ищем шаблон по ID
    row = conn.execute(
        "SELECT * FROM templates WHERE id = ?",
        (id,)
    ).fetchone()

    # Закрываем подключение
    conn.close()

    # Если шаблон не найден
    if row is None:
        return jsonify({
            "error": "Шаблон не найден"
        }), 404

    # HTML шаблона
    template_html = row["content"]

    # Подстановка значений
    result_html = replace_markers(
        template_html,
        values
    )

    # Абсолютный путь к файлу шрифта DejaVuSans.ttf в папке проекта
    # Шрифт используется при генерации PDF, чтобы русские буквы отображались корректно,
    # а не квадратами. Путь собирается из трёх частей:
    #   1. os.path.dirname(__file__) — папка, где лежит app.py (отбрасывает имя файла)
    #   2. "DejaVuSans.ttf" — имя файла шрифта
    #   3. os.path.abspath() — делает путь полным (без ../ и сокращений)
    font_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "DejaVuSans.ttf"
        )
    )

    # Вывод пути в терминал для проверки
    print(font_path)

    # Полный HTML документ для PDF
    html = f"""
    <html>

    <head>

        <meta charset="UTF-8">

        <style>

            @font-face {{
                font-family: "DejaVu";
                src: url("file://{font_path}");
            }}

            body {{
                font-family: "DejaVu";
                font-size: 14px;
            }}

        </style>

    </head>

    <body>

        {result_html}

    </body>

    </html>
    """

    # Функция для доступа xhtml2pdf к локальным файлам проекта
    def link_callback(uri, rel):
        """
        Функция, которую xhtml2pdf вызывает для загрузки внешних ресурсов.
        Когда в HTML встречается ссылка на файл (например, шрифт через file://),
        xhtml2pdf вызывает эту функцию с параметром uri — адресом ресурса.
        Функция читает файл с диска и возвращает его содержимое.
        """
        # Если путь начинается с file:// — это локальный файл
        if uri.startswith("file://"):
            # Убираем file://, оставляем обычный путь к файлу
            path = uri.replace("file://", "")
            return path
        # Если это не file:// — возвращаем uri как есть
        return uri

    # Виртуальный PDF-файл в памяти (не сохраняется на диск)
    pdf_buffer = io.BytesIO()

    # Генерация PDF документа
    pisa_status = pisa.CreatePDF(
        # подготовленный HTML с подставленными значениями
        html,
        # куда записать результат (в буфер в памяти, не на диск)
        dest=pdf_buffer,
        # русские буквы обрабатывались корректно — кодировка
        encoding="UTF-8",
        # функция для загрузки внешних файлов (шрифтов, картинок)
        link_callback=link_callback
    )

    # Если произошла ошибка генерации PDF
    if pisa_status.err:
        return jsonify({
            "error": "Ошибка генерации PDF"
        }), 500

    # Переходим в начало виртуального файла (чтобы читать с начала)
    pdf_buffer.seek(0)

    # Возвращаем PDF пользователю
    return send_file(
        pdf_buffer,
        # сообщает браузеру, что это PDF-файл, а не HTML-страница
        mimetype="application/pdf",
        # False — открыть PDF в браузере, True — скачать файлом на компьютер
        as_attachment=False
    )


# Запуск сервера
# Этот блок выполняется только при запуске app.py напрямую,
# а не при импорте этого файла в другой скрипт
if __name__ == "__main__":
    # Запуск Flask сервера
    app.run(
        # debug=True — авто-перезагрузка при изменениях кода
        debug=True,
        # port=5000 — сервер доступен по адресу http://localhost:5000
        port=5000
    )
