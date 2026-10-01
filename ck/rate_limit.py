import time
from collections import defaultdict
from functools import wraps
from flask import request, flash, redirect, url_for

# Хранилище неудачных попыток: IP -> [timestamp1, timestamp2, ...]
FAILED_ATTEMPTS = defaultdict(list)
MAX_ATTEMPTS = 5       # Максимум 5 попыток
LOCKOUT_TIME = 300     # Блокировка на 5 минут (300 секунд)

def get_remote_address() -> str:
    """Получение IP-адреса клиента."""
    return request.headers.get('X-Forwarded-For', request.remote_addr)

def is_rate_limited(ip: str) -> bool:
    """Проверка, превышен ли лимит попыток."""
    now = time.time()
    # Удаление попыток старше LOCKOUT_TIME
    FAILED_ATTEMPTS[ip] = [t for t in FAILED_ATTEMPTS[ip] if now - t < LOCKOUT_TIME]
    return len(FAILED_ATTEMPTS[ip]) >= MAX_ATTEMPTS

def record_failed_attempt(ip: str):
    """Фиксация неудачной попытки входа."""
    FAILED_ATTEMPTS[ip].append(time.time())

def clear_failed_attempts(ip: str):
    """Сброс неудачных попыток при успешном входе."""
    if ip in FAILED_ATTEMPTS:
        del FAILED_ATTEMPTS[ip]

def limit_login_attempts(f):
    """Декоратор ограничения попыток авторизации."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = get_remote_address()
        if is_rate_limited(ip):
            flash("Слишком много неудачных попыток входа. Доступ заблокирован на 5 минут.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function