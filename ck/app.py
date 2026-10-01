from flask import Flask, render_template, request, redirect, url_for, session, flash
from config import Config
from db import close_db, execute_query, execute_commit
from security import (
    hash_password, verify_password, validate_password_policy,
    sanitize_input, login_required, admin_required, trainer_required, set_security_headers
)
from rate_limit import limit_login_attempts, record_failed_attempt, clear_failed_attempts, get_remote_address
from audit import log_event

app = Flask(__name__)
app.config.from_object(Config)

app.teardown_appcontext(close_db)
app.after_request(set_security_headers)

# --- Главная страница ---
@app.route('/')
def index():
    services = execute_query("SELECT * FROM services ORDER BY id DESC")
    return render_template('dashboard.html', services=services)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Самостоятельная регистрация клиентов."""
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username', ''))
        password = request.form.get('password', '')
        full_name = sanitize_input(request.form.get('full_name', ''))

        # Проверка сложности пароля
        is_valid, err_msg = validate_password_policy(password)
        if not is_valid:
            flash(err_msg, "danger")
            return render_template('register.html')

        # Проверка существования логина
        existing = execute_query("SELECT id FROM users WHERE username = ?", (username,), one=True)
        if existing:
            flash("Пользователь с таким логином уже существует.", "danger")
            return render_template('register.html')

        pwd_hash = hash_password(password)
        execute_commit(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, 'client')",
            (username, pwd_hash, full_name)
        )

        log_event("REGISTER", f"Зарегистрирован новый клиент: {username}")
        flash("Регистрация успешна! Теперь вы можете войти.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')
# --- Авторизация и Выход ---
@app.route('/login', methods=['GET', 'POST'])
@limit_login_attempts
def login():
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username', ''))
        password = request.form.get('password', '')

        user = execute_query("SELECT * FROM users WHERE username = ?", (username,), one=True)

        if user and verify_password(user['password_hash'], password):
            clear_failed_attempts(get_remote_address())
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']

            log_event("LOGIN_SUCCESS", f"Вход пользователя {username} ({user['role']})", user_id=user['id'], username=username)
            flash("Вы успешно вошли в систему.", "success")
            return redirect(url_for('index'))
        else:
            record_failed_attempt(get_remote_address())
            log_event("LOGIN_FAILED", f"Неудачный вход: {username}")
            flash("Неверный логин или пароль.", "danger")

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_event("LOGOUT", "Пользователь вышел из системы")
    session.clear()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for('login'))

# --- Функционал АДМИНИСТРАТОРА ---

@app.route('/admin/add_service', methods=['GET', 'POST'])
@admin_required
def add_service():
    """Создание новой услуги (Админ)."""
    if request.method == 'POST':
        title = sanitize_input(request.form.get('title', ''))
        description = sanitize_input(request.form.get('description', ''))
        try:
            price = float(request.form.get('price', 0))
        except ValueError:
            flash("Некорректная цена.", "danger")
            return render_template('add_service.html')

        execute_commit(
            "INSERT INTO services (title, description, price) VALUES (?, ?, ?)",
            (title, description, price)
        )
        log_event("SERVICE_CREATED", f"Администратор создал услугу '{title}' ({price} руб.)")
        flash(f"Услуга '{title}' успешно добавлена!", "success")
        return redirect(url_for('index'))

    return render_template('add_service.html')

@app.route('/admin/hire_trainer', methods=['GET', 'POST'])
@admin_required
def hire_trainer():
    """Найм нового тренера (Админ)."""
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username', ''))
        password = request.form.get('password', '')
        full_name = sanitize_input(request.form.get('full_name', ''))

        is_valid, err_msg = validate_password_policy(password)
        if not is_valid:
            flash(err_msg, "danger")
            return render_template('hire_trainer.html')

        existing = execute_query("SELECT id FROM users WHERE username = ?", (username,), one=True)
        if existing:
            flash("Пользователь с таким логином уже зарегистрирован.", "danger")
            return render_template('hire_trainer.html')

        pwd_hash = hash_password(password)
        execute_commit(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, 'trainer')",
            (username, pwd_hash, full_name)
        )
        log_event("TRAINER_HIRED", f"Администратор зарегистрировал тренера {full_name} ({username})")
        flash(f"Тренер '{full_name}' успешно нанят!", "success")
        return redirect(url_for('index'))

    return render_template('hire_trainer.html')

# --- Функционал КЛИЕНТА ---

@app.route('/book_service/<int:service_id>', methods=['POST'])
@login_required
def book_service(service_id):
    """Отправка заявки на запись клиентом."""
    booking_date = sanitize_input(request.form.get('booking_date', ''))
    if not booking_date:
        flash("Укажите дату записи.", "warning")
        return redirect(url_for('index'))

    execute_commit(
        "INSERT INTO bookings (client_id, service_id, booking_date, status) VALUES (?, ?, ?, 'pending')",
        (session['user_id'], service_id, booking_date)
    )
    log_event("BOOKING_SUBMITTED", f"Клиент {session['username']} создал заявку на услугу #{service_id}")
    flash("Заявка успешно отправлена! Ожидайте подтверждения тренера.", "success")
    return redirect(url_for('my_bookings'))

@app.route('/my_bookings')
@login_required
def my_bookings():
    """Просмотр клиентом своих заявок."""
    bookings = execute_query('''
        SELECT b.id, s.title, s.price, b.booking_date, b.status, b.created_at
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        WHERE b.client_id = ?
        ORDER BY b.created_at DESC
    ''', (session['user_id'],))
    return render_template('my_bookings.html', bookings=bookings)

# --- Функционал ТРЕНЕРА ---

@app.route('/trainer/bookings')
@trainer_required
def trainer_bookings():
    """Просмотр заявкок тренером."""
    bookings = execute_query('''
        SELECT b.id, u.full_name as client_name, s.title as service_title, b.booking_date, b.status, b.created_at
        FROM bookings b
        JOIN users u ON b.client_id = u.id
        JOIN services s ON b.service_id = s.id
        ORDER BY CASE WHEN b.status = 'pending' THEN 0 ELSE 1 END, b.created_at DESC
    ''')
    return render_template('trainer_bookings.html', bookings=bookings)

@app.route('/trainer/booking/<int:booking_id>/<action>', methods=['POST'])
@trainer_required
def process_booking(booking_id, action):
    """Принятие или отклонение заявки тренером."""
    if action not in ['accept', 'reject']:
        flash("Недопустимое действие.", "danger")
        return redirect(url_for('trainer_bookings'))

    new_status = 'accepted' if action == 'accept' else 'rejected'
    execute_commit("UPDATE bookings SET status = ? WHERE id = ?", (new_status, booking_id))
    
    status_text = "принята" if action == 'accept' else "отклонена"
    log_event("BOOKING_PROCESSED", f"Тренер {session['username']} изменил статус заявки #{booking_id} на {new_status}")
    flash(f"Заявка #{booking_id} {status_text}.", "info")
    return redirect(url_for('trainer_bookings'))

@app.route('/audit_log')
@admin_required
def audit_log():
    logs = execute_query("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 100")
    return render_template('audit_log.html', logs=logs)

# Обработка ошибок
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # host='0.0.0.0' позволяет открывать сайт не только с текущего компьютера, но и с других устройств в локальной сети
    app.run(host='0.0.0.0', port=5000, debug=True)
