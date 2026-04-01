import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Путь к БД — /tmp на Render доступен для записи
DB_DIR = os.environ.get("DB_DIR", ".")
DB_PATH = os.path.join(DB_DIR, "chatbot.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'Новый чат',
            model TEXT DEFAULT 'gemini',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            model_used TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_conv_user
            ON conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_msg_conv
            ON messages(conversation_id);
    ''')
    conn.commit()
    conn.close()
    print(f"✅ БД инициализирована: {DB_PATH}")


# ============ ПОЛЬЗОВАТЕЛИ ============

def create_user(username, email, password):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, generate_password_hash(password))
        )
        conn.commit()
        return True, "Регистрация успешна"
    except sqlite3.IntegrityError:
        return False, "Пользователь с таким именем или email уже существует"
    finally:
        conn.close()


def verify_user(email, password):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(user) if user else None


# ============ ДИАЛОГИ ============

def create_conversation(user_id, model='gemini'):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO conversations (user_id, model) VALUES (?, ?)",
        (user_id, model)
    )
    conv_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return conv_id


def get_user_conversations(user_id):
    conn = get_db()
    convs = conn.execute(
        """SELECT * FROM conversations
           WHERE user_id = ?
           ORDER BY updated_at DESC
           LIMIT 50""",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(c) for c in convs]


def get_conversation(conv_id, user_id):
    conn = get_db()
    conv = conn.execute(
        "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
        (conv_id, user_id)
    ).fetchone()
    conn.close()
    return dict(conv) if conv else None


def update_conversation_title(conv_id, title):
    conn = get_db()
    conn.execute(
        "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
        (title, datetime.now().isoformat(), conv_id)
    )
    conn.commit()
    conn.close()


def delete_conversation(conv_id, user_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM conversations WHERE id = ? AND user_id = ?",
        (conv_id, user_id)
    )
    conn.commit()
    conn.close()


# ============ СООБЩЕНИЯ ============

def add_message(conversation_id, role, content, model_used=None):
    conn = get_db()
    conn.execute(
        """INSERT INTO messages (conversation_id, role, content, model_used)
           VALUES (?, ?, ?, ?)""",
        (conversation_id, role, content, model_used)
    )
    conn.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), conversation_id)
    )
    conn.commit()
    conn.close()


def get_messages(conversation_id):
    conn = get_db()
    msgs = conn.execute(
        """SELECT * FROM messages
           WHERE conversation_id = ?
           ORDER BY created_at ASC""",
        (conversation_id,)
    ).fetchall()
    conn.close()
    return [dict(m) for m in msgs]
