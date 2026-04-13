const API = 'http://127.0.0.1:5000';
let csrfToken = '';

// ── CSRF ────────────────────────────────────────────────────────────────────

async function loadCsrfToken() {
  try {
    const res  = await fetch(`${API}/csrf-token`, { credentials: 'include' });
    const data = await res.json();
    csrfToken  = data.csrf_token;
  } catch {
    showMessage('Cannot reach server. Is Flask running?', 'error');
  }
}

// ── Tabs ────────────────────────────────────────────────────────────────────

function switchTab(tab) {
  const isLogin = tab === 'login';

  document.getElementById('login-form')
    .classList.toggle('hidden', !isLogin);
  document.getElementById('register-form')
    .classList.toggle('hidden', isLogin);

  document.querySelectorAll('.tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });

  hideMessage();
}

// ── Messages ────────────────────────────────────────────────────────────────

function showMessage(text, type) {
  const el = document.getElementById('msg');
  el.textContent = text;
  el.className   = `message ${type}`;
  el.classList.remove('hidden');
}

function hideMessage() {
  document.getElementById('msg').classList.add('hidden');
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function setLoading(btnId, loading, defaultLabel) {
  const btn      = document.getElementById(btnId);
  btn.disabled   = loading;
  btn.textContent = loading ? 'Please wait…' : defaultLabel;
}

async function post(endpoint, body) {
  return fetch(`${API}/${endpoint}`, {
    method:      'POST',
    credentials: 'include',           // sends session cookie
    headers:     { 'Content-Type': 'application/json' },
    body:        JSON.stringify({ ...body, csrf_token: csrfToken }),
  });
}

// ── Login ───────────────────────────────────────────────────────────────────

async function handleLogin(e) {
  e.preventDefault();
  setLoading('login-btn', true, 'Login');

  try {
    const res  = await post('login', {
      email:    document.getElementById('login-email').value.trim(),
      password: document.getElementById('login-password').value,
    });
    const data = await res.json();

    if (res.ok) {
      showMessage(data.message, 'success');
      document.getElementById('login-form').reset();
      await loadCsrfToken();           // server rotated the token — refresh it
    } else {
      showMessage(data.error, 'error');
    }
  } catch {
    showMessage('Network error. Please try again.', 'error');
  }

  setLoading('login-btn', false, 'Login');
}

// ── Register ─────────────────────────────────────────────────────────────────

async function handleRegister(e) {
  e.preventDefault();
  setLoading('register-btn', true, 'Create Account');

  try {
    const res  = await post('register', {
      username: document.getElementById('reg-username').value.trim(),
      email:    document.getElementById('reg-email').value.trim(),
      password: document.getElementById('reg-password').value,
    });
    const data = await res.json();

    if (res.ok) {
      showMessage(data.message + ' You can now log in.', 'success');
      document.getElementById('register-form').reset();
      switchTab('login');
      await loadCsrfToken();
    } else {
      showMessage(data.error, 'error');
    }
  } catch {
    showMessage('Network error. Please try again.', 'error');
  }

  setLoading('register-btn', false, 'Create Account');
}

// ── Init ─────────────────────────────────────────────────────────────────────

loadCsrfToken();