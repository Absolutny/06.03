import os

class Config:
    # Секретный ключ для подписи сессий (32 случайных байта)
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
    
    # Путь к базе данных SQLite
    DATABASE = os.path.join(os.path.dirname(__file__), 'sport.db')
    
    # Безопасные параметры cookie для сессий
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # В боевом режиме (HTTPS) установить True
    
    # Отключение отладочного режима в продакшене для скрытия трассировок ошибок
    DEBUG = True