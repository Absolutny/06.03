import html
import re
from functools import wraps
from flask import session, redirect, url_for, flash, request, abort
from werkzeug.security import generate_password_hash, check_password_hash

# --- 1. Криптография и пароли ---

def hash_password(password: str) -> str:
    """Безопасное хэширование пароля с использованием pbkdf2:sha256."""
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def verify_password(password_hash: str, password: str) -> bool:
    """Проверка совпадения открытого пароля с хэшем."""
    if not password_hash or not password:
        return False
    return check_password_hash(password_hash, password)

def validate_password_policy(password: str) -> tuple[bool, str]:
    """
    Проверка соблюдения политики сложности паролей:
    - Длина минимум 8 символов
    - Наличие заглавной буквы
    - Наличие цифры
    - Наличие специального символа
    """
    if len(password) < 8:
        return False, "Пароль должен содержать не менее 8 символов."
    if not re.search(r"[A-ZА-Я]", password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву."
    if not re.search(r"\d", password):
        return False, "Пароль должен содержать хотя бы одну цифру."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Пароль должен содержать хотя бы один спецсимвол (!@#$%^&*)."
    return True, ""

# --- 2. Санитизация ввода (Защита от XSS) ---

def sanitize_input(text: str) -> str:
    """Очистка строк от потенциально опасных HTML-тегов."""
    if not isinstance(text, str):
        return text
    return html.escape(text.strip())

# --- 3. Разграничение прав и авторизация (RBAC) ---

def login_required(f):
    """Декоратор: доступ разрешен только вошедшим пользователям."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Для доступа к этой странице необходимо авторизоваться.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Декоратор: доступ только для администратора."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Требуется авторизация.", "warning")
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash("У вас недостаточно прав для выполнения этой операции.", "danger")
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

def trainer_required(f):
    """Декоратор: доступ только для тренеров и администраторов."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Требуется авторизация.", "warning")
            return redirect(url_for('login'))
        if session.get('role') not in ['trainer', 'admin']:
            flash("Доступ разрешен только тренерскому составу.", "danger")
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function
# --- 4. Защитные HTTP-заголовки ---

def set_security_headers(response):
    """Добавление заголовков безопасности в HTTP-ответ."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    return response