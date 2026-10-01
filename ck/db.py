import sqlite3
from flask import g
from config import Config

def get_db():
    """Получение подключения к базе данных SQLite."""
    if 'db' not in g:
        g.db = sqlite3.connect(Config.DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """Закрытие подключения к базе данных по завершении запроса."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def execute_query(query, args=(), one=False):
    """
    Безопасный параметризованный SQL-запрос для исключения SQL-инъекций.
    """
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_commit(query, args=()):
    """Выполнение операции запись/изменение с commit."""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id