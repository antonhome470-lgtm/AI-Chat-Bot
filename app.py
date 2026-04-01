from flask import (
    Flask, render_template, request,
    jsonify, redirect, url_for
)
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    login_required, current_user
)
from database import *
from ai_models import get_ai_response, AVAILABLE_MODELS
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-12345")

# ============ FLASK-LOGIN ============

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Войдите в аккаунт'


class User(UserMixin):
    def __init__(self, data):
        self.id = data['id']
        self.username = data['username']
        self.email = data['email']


@login_manager.user_loader
def load_user(user_id):
    data = get_user_by_id(int(user_id))
    return User(data) if data else None


# ============ СТРАНИЦЫ ============

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if len(username) < 3:
            return render_template('register.html',
                                   error="Имя минимум 3 символа")
        if len(password) < 6:
            return render_template('register.html',
                                   error="Пароль минимум 6 символов")
        if '@' not in email:
            return render_template('register.html',
                                   error="Некорректный email")

        success, msg = create_user(username, email, password)
        if success:
            return redirect(url_for('login', registered='true'))
        return render_template('register.html', error=msg)

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user_data = verify_user(email, password)
        if user_data:
            login_user(User(user_data), remember=True)
            return redirect(url_for('chat'))
        return render_template('login.html',
                               error="Неверный email или пароль")

    return render_template('login.html',
                           registered=request.args.get('registered'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/chat')
@login_required
def chat():
    convs = get_user_conversations(current_user.id)
    return render_template('chat.html',
                           user=current_user,
                           conversations=convs,
                           models=AVAILABLE_MODELS)


# ============ API ============

@app.route('/api/conversations/<int:conv_id>/messages')
@login_required
def api_get_messages(conv_id):
    conv = get_conversation(conv_id, current_user.id)
    if not conv:
        return jsonify({"error": "Не найдено"}), 404
    messages = get_messages(conv_id)
    return jsonify({"messages": messages})


@app.route('/api/conversations/<int:conv_id>', methods=['DELETE'])
@login_required
def api_delete_conversation(conv_id):
    delete_conversation(conv_id, current_user.id)
    return jsonify({"success": True})


@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.json
    message = data.get('message', '').strip()
    model = data.get('model', 'gemini')
    conv_id = data.get('conversation_id')

    if not message:
        return jsonify({"error": "Пустое сообщение"}), 400

    if len(message) > 5000:
        return jsonify({"error": "Сообщение слишком длинное"}), 400

    # Создаём или проверяем диалог
    if not conv_id:
        conv_id = create_conversation(current_user.id, model)
    else:
        conv = get_conversation(conv_id, current_user.id)
        if not conv:
            return jsonify({"error": "Диалог не найден"}), 404

    # Сохраняем сообщение
    add_message(conv_id, "user", message)

    # История (последние 20 сообщений для контекста)
    db_msgs = get_messages(conv_id)
    history = [
        {"role": m['role'], "content": m['content']}
        for m in db_msgs[-21:-1]
    ]

    # Название по первому сообщению
    if len(db_msgs) == 1:
        title = message[:50] + ("..." if len(message) > 50 else "")
        update_conversation_title(conv_id, title)

    # Ответ ИИ
    reply = get_ai_response(message, history, model)

    # Сохраняем ответ
    add_message(conv_id, "assistant", reply, model)

    return jsonify({
        "reply": reply,
        "conversation_id": conv_id,
        "model": model
    })


# ============ HEALTH CHECK ============

@app.route('/health')
def health():
    return jsonify({"status": "ok", "db": DB_PATH})


# ============ ЗАПУСК ============

# Инициализация БД при старте
init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
