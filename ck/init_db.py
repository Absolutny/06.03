import sqlite3
from config import Config
from security import hash_password

def init_db():
    conn = sqlite3.connect(Config.DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'client',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            event_type TEXT NOT NULL,
            description TEXT,
            ip_address TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Тестовые аккаунты
    users = [
        ('admin', hash_password('Admin123'), 'Администратор Комплекса', 'admin'),
        ('trainer', hash_password('Trainer123'), 'Тренер Тренеров', 'trainer'),
        ('client', hash_password('Client123'), 'Иванов Иван', 'client')
    ]

    for username, pwd_hash, full_name, role in users:
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES (?, ?, ?, ?)
            ''', (username, pwd_hash, full_name, role))

    # Тестовые услуги
    services = [
        ('Бассейн', 'Посещение плавательного бассейна 50m', 500.0),
        ('Тренажерный зал', 'Разовое посещение зала', 400.0)
    ]

    for title, desc, price in services:
        cursor.execute("SELECT id FROM services WHERE title = ?", (title,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO services (title, description, price) VALUES (?, ?, ?)", (title, desc, price))

    conn.commit()
    conn.close()
    print("[OK] База данных успешно инициализирована.")

if __name__ == '__main__':
    init_db()