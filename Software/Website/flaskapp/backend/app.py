from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
import sqlite3
import bcrypt
import secrets
import os

# .env is one level up from backend/
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    raise RuntimeError("SECRET_KEY not set — add it to flaskapp/.env")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,    # JS cannot read the cookie
    SESSION_COOKIE_SAMESITE='None',   # blocks cross-site request forgery
    SESSION_COOKIE_SECURE=True,     # flip to True when you move to HTTPS
)

CORS(app,
     supports_credentials=True,
     origins=["http://127.0.0.1:5500", "http://localhost:5500",
               "http://127.0.0.1:5000", "http://localhost:5000",
               "null"])

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'mydb.db')


# ── Database ───────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            email      TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


# ── CSRF helpers ───────────────────────────────────────────────────────────

def generate_csrf_token():
    token = secrets.token_hex(32)
    session['csrf_token'] = token
    return token


def validate_csrf(token_from_request):
    stored = session.get('csrf_token')
    if not stored or not token_from_request:
        return False
    return secrets.compare_digest(stored, token_from_request)


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route('/csrf-token', methods=['GET'])
def csrf_token():
    return jsonify({'csrf_token': generate_csrf_token()})


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}

    if not validate_csrf(data.get('csrf_token')):
        return jsonify({'error': 'Invalid or missing CSRF token'}), 403

    username = data.get('username', '').strip()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400
    if len(username) < 2:
        return jsonify({'error': 'Username must be at least 2 characters'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    conn = None
    try:
        conn = get_db()
        conn.execute(
            'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
            (username, email, hashed.decode())
        )
        conn.commit()
        return jsonify({'message': 'Account created successfully!'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or email already taken'}), 409
    finally:
        if conn:
            conn.close()


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}

    if not validate_csrf(data.get('csrf_token')):
        return jsonify({'error': 'Invalid or missing CSRF token'}), 403

    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    conn = None
    try:
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()
    finally:
        if conn:
            conn.close()

    if not user or not bcrypt.checkpw(password.encode(), user['password'].encode()):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Rotate CSRF token after login (prevents session fixation)
    generate_csrf_token()
    session['user_id']  = user['id']
    session['username'] = user['username']

    return jsonify({'message': f"Welcome back, {user['username']}!"}), 200


@app.route('/logout', methods=['POST'])
def logout():
    data = request.get_json(silent=True) or {}
    if not validate_csrf(data.get('csrf_token')):
        return jsonify({'error': 'Invalid CSRF token'}), 403
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200


if __name__ == '__main__':
    init_db()
    app.run(debug=True)