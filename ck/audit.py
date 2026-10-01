import sqlite3
from flask import request, session
from config import Config

def log_event(event_type: str, description: str, user_id: int = None, username: str = None):
    """Запись события безопасности в журнал аудита."""
    try:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr) if request else '127.0.0.1'
        uid = user_id or session.get('user_id')
        uname = username or session.get('username', 'system')

        conn = sqlite3.connect(Config.DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (user_id, username, event_type, description, ip_address)
            VALUES (?, ?, ?, ?, ?)
        ''', (uid, uname, event_type, description, ip))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AUDIT LOG ERROR] Не удалось записать событие: {e}")