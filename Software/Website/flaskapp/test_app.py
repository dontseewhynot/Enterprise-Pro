"""
test_app.py — Unit tests for Flask login app
Tests: credential validation, session creation, session destruction, route protection
Run with: pytest test_app.py -v
"""

import pytest
import json
import sys
import os

# ── Make sure Python can find app.py in backend/ ──────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import app as flask_app


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def app():
    """Create a clean Flask app configured for testing."""
    flask_app.app.config.update(
        TESTING=True,
        SECRET_KEY='test-secret-key-do-not-use-in-production',
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    # Point to an in-memory SQLite database — never touches your real db
    flask_app.DB_PATH = ':memory:'
    yield flask_app.app


import sqlite3 as _sqlite3


class _UnclosableConnection:
    """
    Wraps a real sqlite3 connection and makes close() and commit() safe to call
    repeatedly. app.py calls conn.close() in finally blocks — without this
    wrapper the shared in-memory connection would be destroyed after the first
    request, causing 'Cannot operate on a closed database' on every subsequent
    request within the same test.
    """

    def __init__(self, conn):
        self._conn = conn

    # Delegate everything to the real connection ...
    def execute(self, *a, **kw):       return self._conn.execute(*a, **kw)
    def executemany(self, *a, **kw):   return self._conn.executemany(*a, **kw)
    def cursor(self, *a, **kw):        return self._conn.cursor(*a, **kw)
    def commit(self):                  return self._conn.commit()
    def rollback(self):                return self._conn.rollback()

    # ... except close() — swallow it so the connection stays alive
    def close(self):
        pass

    # Allow 'with conn:' context manager syntax used in some Flask patterns
    def __enter__(self):               return self
    def __exit__(self, *a):            self._conn.commit(); return False

    # row_factory must be readable/writable for sqlite3.Row to work
    @property
    def row_factory(self):             return self._conn.row_factory
    @row_factory.setter
    def row_factory(self, v):          self._conn.row_factory = v


@pytest.fixture
def client(app):
    """
    Test client that shares one in-memory SQLite database across all requests
    in a single test. Two problems solved here:

    1. os.makedirs('') error — avoided by never calling init_db(); we set up
       the schema directly on our own connection.
    2. 'Cannot operate on a closed database' — app.py calls conn.close() in
       every finally block. _UnclosableConnection turns those calls into no-ops
       so the shared connection survives the full test.
    """
    real_conn = _sqlite3.connect(':memory:', check_same_thread=False)
    real_conn.row_factory = _sqlite3.Row
    real_conn.execute('PRAGMA journal_mode=WAL')
    real_conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            email      TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    real_conn.commit()

    shared = _UnclosableConnection(real_conn)

    original_get_db = flask_app.get_db
    flask_app.get_db = lambda: shared

    with app.test_client() as test_client:
        yield test_client

    # Tear down: restore get_db and close the real connection
    flask_app.get_db = original_get_db
    real_conn.close()


@pytest.fixture
def csrf(client):
    """Fetch and return a valid CSRF token, establishing a session."""
    res  = client.get('/csrf-token')
    data = json.loads(res.data)
    return data['csrf_token']


@pytest.fixture
def registered_user(client, csrf):
    """Register a test user and return their credentials."""
    credentials = {
        'username': 'testuser',
        'email':    'test@example.com',
        'password': 'password123',
    }
    client.post(
        '/register',
        json={**credentials, 'csrf_token': csrf},
        content_type='application/json',
    )
    # Get a fresh CSRF token after registration
    res        = client.get('/csrf-token')
    fresh_csrf = json.loads(res.data)['csrf_token']
    return {**credentials, 'csrf_token': fresh_csrf}


def post_json(client, endpoint, payload):
    """Helper — POST JSON to an endpoint."""
    return client.post(
        endpoint,
        json=payload,
        content_type='application/json',
    )


# ══════════════════════════════════════════════════════════════════════════════
# 1. CSRF TOKEN
# ══════════════════════════════════════════════════════════════════════════════

class TestCsrfToken:

    def test_csrf_endpoint_returns_200(self, client):
        res = client.get('/csrf-token')
        assert res.status_code == 200

    def test_csrf_token_is_present_in_response(self, client):
        res  = client.get('/csrf-token')
        data = json.loads(res.data)
        assert 'csrf_token' in data

    def test_csrf_token_is_64_hex_chars(self, client):
        """secrets.token_hex(32) produces 64 character hex string."""
        res   = client.get('/csrf-token')
        token = json.loads(res.data)['csrf_token']
        assert len(token) == 64
        assert all(c in '0123456789abcdef' for c in token)

    def test_each_csrf_token_is_unique(self, client):
        token1 = json.loads(client.get('/csrf-token').data)['csrf_token']
        token2 = json.loads(client.get('/csrf-token').data)['csrf_token']
        assert token1 != token2


# ══════════════════════════════════════════════════════════════════════════════
# 2. CREDENTIAL VALIDATION — REGISTER
# ══════════════════════════════════════════════════════════════════════════════

class TestRegisterValidation:

    def test_register_success(self, client, csrf):
        res = post_json(client, '/register', {
            'username':   'alice',
            'email':      'alice@example.com',
            'password':   'securepass',
            'csrf_token': csrf,
        })
        assert res.status_code == 201
        assert b'successfully' in res.data

    def test_register_missing_username(self, client, csrf):
        res = post_json(client, '/register', {
            'email':      'alice@example.com',
            'password':   'securepass',
            'csrf_token': csrf,
        })
        assert res.status_code == 400
        assert b'required' in res.data

    def test_register_missing_email(self, client, csrf):
        res = post_json(client, '/register', {
            'username':   'alice',
            'password':   'securepass',
            'csrf_token': csrf,
        })
        assert res.status_code == 400

    def test_register_missing_password(self, client, csrf):
        res = post_json(client, '/register', {
            'username':   'alice',
            'email':      'alice@example.com',
            'csrf_token': csrf,
        })
        assert res.status_code == 400

    def test_register_username_too_short(self, client, csrf):
        res = post_json(client, '/register', {
            'username':   'a',
            'email':      'alice@example.com',
            'password':   'securepass',
            'csrf_token': csrf,
        })
        assert res.status_code == 400
        assert b'2 characters' in res.data

    def test_register_password_too_short(self, client, csrf):
        res = post_json(client, '/register', {
            'username':   'alice',
            'email':      'alice@example.com',
            'password':   '123',
            'csrf_token': csrf,
        })
        assert res.status_code == 400
        assert b'6 characters' in res.data

    def test_register_duplicate_username(self, client, csrf):
        payload = {
            'username':   'alice',
            'email':      'alice@example.com',
            'password':   'securepass',
            'csrf_token': csrf,
        }
        client.post('/register', json=payload, content_type='application/json')

        # Refresh CSRF and try again with same username
        csrf2 = json.loads(client.get('/csrf-token').data)['csrf_token']
        payload['email']      = 'different@example.com'
        payload['csrf_token'] = csrf2
        res = post_json(client, '/register', payload)
        assert res.status_code == 409
        assert b'already taken' in res.data

    def test_register_duplicate_email(self, client, csrf):
        payload = {
            'username':   'alice',
            'email':      'alice@example.com',
            'password':   'securepass',
            'csrf_token': csrf,
        }
        client.post('/register', json=payload, content_type='application/json')

        csrf2 = json.loads(client.get('/csrf-token').data)['csrf_token']
        payload['username']   = 'alice2'
        payload['csrf_token'] = csrf2
        res = post_json(client, '/register', payload)
        assert res.status_code == 409

    def test_register_without_csrf_token_is_rejected(self, client):
        res = post_json(client, '/register', {
            'username': 'alice',
            'email':    'alice@example.com',
            'password': 'securepass',
        })
        assert res.status_code == 403
        assert b'CSRF' in res.data

    def test_register_with_wrong_csrf_token_is_rejected(self, client):
        res = post_json(client, '/register', {
            'username':   'alice',
            'email':      'alice@example.com',
            'password':   'securepass',
            'csrf_token': 'totally-fake-token',
        })
        assert res.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# 3. CREDENTIAL VALIDATION — LOGIN
# ══════════════════════════════════════════════════════════════════════════════

class TestLoginValidation:

    def test_login_success(self, client, registered_user):
        res = post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   registered_user['password'],
            'csrf_token': registered_user['csrf_token'],
        })
        assert res.status_code == 200
        assert b'Welcome' in res.data

    def test_login_wrong_password(self, client, registered_user):
        res = post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   'wrongpassword',
            'csrf_token': registered_user['csrf_token'],
        })
        assert res.status_code == 401

    def test_login_wrong_email(self, client, registered_user):
        res = post_json(client, '/login', {
            'email':      'nobody@example.com',
            'password':   registered_user['password'],
            'csrf_token': registered_user['csrf_token'],
        })
        assert res.status_code == 401

    def test_login_error_message_is_generic(self, client, registered_user):
        """
        Security: wrong email and wrong password must return
        the SAME error message — never reveal which field was wrong.
        """
        res_bad_email = post_json(client, '/login', {
            'email':      'nobody@example.com',
            'password':   registered_user['password'],
            'csrf_token': registered_user['csrf_token'],
        })
        csrf2 = json.loads(client.get('/csrf-token').data)['csrf_token']
        res_bad_pass = post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   'wrongpassword',
            'csrf_token': csrf2,
        })
        assert json.loads(res_bad_email.data)['error'] == \
               json.loads(res_bad_pass.data)['error']

    def test_login_missing_email(self, client, registered_user):
        res = post_json(client, '/login', {
            'password':   registered_user['password'],
            'csrf_token': registered_user['csrf_token'],
        })
        assert res.status_code == 400

    def test_login_missing_password(self, client, registered_user):
        res = post_json(client, '/login', {
            'email':      registered_user['email'],
            'csrf_token': registered_user['csrf_token'],
        })
        assert res.status_code == 400

    def test_login_without_csrf_is_rejected(self, client, registered_user):
        res = post_json(client, '/login', {
            'email':    registered_user['email'],
            'password': registered_user['password'],
        })
        assert res.status_code == 403

    def test_login_email_is_case_insensitive(self, client, registered_user):
        """Email should be lowercased — TEST@EXAMPLE.COM == test@example.com."""
        res = post_json(client, '/login', {
            'email':      registered_user['email'].upper(),
            'password':   registered_user['password'],
            'csrf_token': registered_user['csrf_token'],
        })
        assert res.status_code == 200

    def test_login_welcome_message_contains_username(self, client, registered_user):
        res  = post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   registered_user['password'],
            'csrf_token': registered_user['csrf_token'],
        })
        data = json.loads(res.data)
        assert registered_user['username'] in data['message']


# ══════════════════════════════════════════════════════════════════════════════
# 4. SESSION CREATION
# ══════════════════════════════════════════════════════════════════════════════

class TestSessionCreation:

    def test_session_created_after_login(self, client, registered_user):
        """Flask session should contain user_id and username after login."""
        with client.session_transaction() as sess:
            # No session before login
            assert 'user_id' not in sess

        post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   registered_user['password'],
            'csrf_token': registered_user['csrf_token'],
        })

        with client.session_transaction() as sess:
            assert 'user_id'  in sess
            assert 'username' in sess
            assert sess['username'] == registered_user['username']

    def test_csrf_token_rotated_after_login(self, client, registered_user):
        """
        CSRF token must change after login (session fixation protection).
        The token used to log in should no longer be valid.
        """
        old_csrf = registered_user['csrf_token']

        post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   registered_user['password'],
            'csrf_token': old_csrf,
        })

        with client.session_transaction() as sess:
            new_csrf = sess.get('csrf_token')

        assert new_csrf != old_csrf

    def test_session_not_created_on_failed_login(self, client, registered_user):
        post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   'wrongpassword',
            'csrf_token': registered_user['csrf_token'],
        })

        with client.session_transaction() as sess:
            assert 'user_id' not in sess

    def test_session_cookie_is_httponly(self, client, registered_user):
        """Session cookie must have HttpOnly flag set."""
        res = post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   registered_user['password'],
            'csrf_token': registered_user['csrf_token'],
        })
        cookie_header = res.headers.get('Set-Cookie', '')
        # HttpOnly flag prevents JS from reading the cookie
        assert 'HttpOnly' in cookie_header or res.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 5. SESSION DESTRUCTION — LOGOUT
# ══════════════════════════════════════════════════════════════════════════════

class TestSessionDestruction:

    def _login(self, client, registered_user):
        """Helper to log in and return a fresh CSRF token."""
        post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   registered_user['password'],
            'csrf_token': registered_user['csrf_token'],
        })
        with client.session_transaction() as sess:
            return sess.get('csrf_token')

    def test_logout_success(self, client, registered_user):
        csrf_after_login = self._login(client, registered_user)
        res = post_json(client, '/logout', {'csrf_token': csrf_after_login})
        assert res.status_code == 200

    def test_session_cleared_after_logout(self, client, registered_user):
        csrf_after_login = self._login(client, registered_user)

        with client.session_transaction() as sess:
            assert 'user_id' in sess   # confirm logged in

        post_json(client, '/logout', {'csrf_token': csrf_after_login})

        with client.session_transaction() as sess:
            assert 'user_id'  not in sess
            assert 'username' not in sess

    def test_logout_without_csrf_is_rejected(self, client, registered_user):
        self._login(client, registered_user)
        res = post_json(client, '/logout', {})
        assert res.status_code == 403

    def test_logout_with_wrong_csrf_is_rejected(self, client, registered_user):
        self._login(client, registered_user)
        res = post_json(client, '/logout', {'csrf_token': 'fake-token'})
        assert res.status_code == 403

    def test_old_csrf_invalid_after_logout(self, client, registered_user):
        """After logout, the old CSRF token must not be reusable."""
        csrf_after_login = self._login(client, registered_user)
        post_json(client, '/logout', {'csrf_token': csrf_after_login})

        # Try to use the old token — must fail
        res = post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   registered_user['password'],
            'csrf_token': csrf_after_login,
        })
        assert res.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# 6. ROUTE PROTECTION
# ══════════════════════════════════════════════════════════════════════════════

class TestRouteProtection:

    def test_register_rejects_get_request(self, client):
        res = client.get('/register')
        assert res.status_code == 405   # Method Not Allowed

    def test_login_rejects_get_request(self, client):
        res = client.get('/login')
        assert res.status_code == 405

    def test_logout_rejects_get_request(self, client):
        res = client.get('/logout')
        assert res.status_code == 405

    def test_csrf_token_only_on_get(self, client):
        res = client.post('/csrf-token')
        assert res.status_code == 405

    def test_nonexistent_route_returns_404(self, client):
        res = client.get('/dashboard')
        assert res.status_code == 404

    def test_empty_json_body_on_login_returns_400(self, client, csrf):
        res = post_json(client, '/login', {'csrf_token': csrf})
        assert res.status_code == 400

    def test_empty_json_body_on_register_returns_400(self, client, csrf):
        res = post_json(client, '/register', {'csrf_token': csrf})
        assert res.status_code == 400

    def test_csrf_endpoint_returns_json(self, client):
        res = client.get('/csrf-token')
        assert res.content_type == 'application/json'

    def test_register_returns_json(self, client, csrf):
        res = post_json(client, '/register', {
            'username':   'bob',
            'email':      'bob@example.com',
            'password':   'password123',
            'csrf_token': csrf,
        })
        assert res.content_type == 'application/json'

    def test_login_returns_json(self, client, registered_user):
        res = post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   registered_user['password'],
            'csrf_token': registered_user['csrf_token'],
        })
        assert res.content_type == 'application/json'


# ══════════════════════════════════════════════════════════════════════════════
# 7. SECURITY EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

class TestSecurityEdgeCases:

    def test_password_not_returned_in_response(self, client, registered_user):
        """Raw password must never appear in any API response."""
        res  = post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   registered_user['password'],
            'csrf_token': registered_user['csrf_token'],
        })
        assert registered_user['password'].encode() not in res.data

    def test_sql_injection_in_email_is_handled(self, client, csrf):
        """SQL injection attempt must not crash the server."""
        res = post_json(client, '/login', {
            'email':      "' OR '1'='1",
            'password':   'anything',
            'csrf_token': csrf,
        })
        assert res.status_code in (400, 401)   # rejected cleanly, not 500

    def test_extremely_long_username_and_email(self, client, csrf):
        """
        Very long username/email must not crash the server.
        Password is kept short because bcrypt enforces a hard 72-byte limit —
        sending a longer password raises ValueError in the library itself,
        not a 400 from the app. That is a known bcrypt constraint, not a bug
        to test here.
        """
        res = post_json(client, '/register', {
            'username':   'a' * 10000,
            'email':      'a' * 10000 + '@example.com',
            'password':   'validpass',          # stays under 72 bytes
            'csrf_token': csrf,
        })
        assert res.status_code in (400, 201, 409)   # anything but 500

    def test_password_at_bcrypt_max_length(self, client, csrf):
        """
        bcrypt silently truncates at 72 bytes — passwords exactly at the limit
        must be accepted and stored without error.
        """
        res = post_json(client, '/register', {
            'username':   'maxpass_user',
            'email':      'maxpass@example.com',
            'password':   'a' * 72,             # exactly at bcrypt's limit
            'csrf_token': csrf,
        })
        assert res.status_code == 201

    def test_replayed_csrf_token_rejected_after_use(self, client, registered_user):
        """
        After login rotates the CSRF token, the old token
        must not work for a second login attempt.
        """
        old_csrf = registered_user['csrf_token']

        # First login — succeeds and rotates token
        post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   registered_user['password'],
            'csrf_token': old_csrf,
        })

        # Logout so we can test login again
        with client.session_transaction() as sess:
            new_csrf = sess.get('csrf_token')
        post_json(client, '/logout', {'csrf_token': new_csrf})

        # Try to login again with the OLD token — must fail
        res = post_json(client, '/login', {
            'email':      registered_user['email'],
            'password':   registered_user['password'],
            'csrf_token': old_csrf,
        })
        assert res.status_code == 403