// User Management — connects to Flask REST API at /api/users

const form          = document.getElementById("userForm");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const list          = document.getElementById("userList");
const statusEl      = document.getElementById("status");
const errorEl       = document.getElementById("error");
const addButton     = document.getElementById("addButton");

// ── API wrapper ────────────────────────────────────────────────────────────────

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

// ── UI helpers ─────────────────────────────────────────────────────────────────

function setStatus(msg) {
  statusEl.textContent = msg || "";
}

function setError(msg) {
  errorEl.textContent = msg || "";
}

function setLoading(isLoading) {
  list.innerHTML = isLoading
    ? '<li class="loading">Loading…</li>'
    : "";
}

// ── Load & render users ────────────────────────────────────────────────────────

async function loadUsers() {
  setLoading(true);
  setError("");
  try {
    const { data } = await api("/api/users");
    list.innerHTML = "";

    if (data.length === 0) {
      list.innerHTML = "<li>No users found.</li>";
      return;
    }

    for (const u of data) {
      const li  = document.createElement("li");
      const span = document.createElement("span");
      span.textContent = u.username;

      const del = document.createElement("button");
      del.textContent = "Delete";
      del.addEventListener("click", async () => {
        del.disabled = true;
        setError("");
        try {
          await api(`/api/users/${u.id}`, { method: "DELETE" });
          await loadUsers();
        } catch (e) {
          setError(e.message);
          del.disabled = false;
        }
      });

      li.appendChild(span);
      li.appendChild(del);
      list.appendChild(li);
    }
  } catch (e) {
    list.innerHTML = "";
    setError("Could not load users: " + e.message);
  }
}

// ── Add user form ──────────────────────────────────────────────────────────────

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  setError("");
  setStatus("");

  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();

  // Client-side validation
  if (!username) {
    return setError("Username is required.");
  }
  if (!password) {
    return setError("Password is required.");
  }
  if (password.length < 6) {
    return setError("Password must be at least 6 characters.");
  }

  addButton.disabled = true;
  setStatus("Adding user…");

  try {
    await api("/api/users", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });

    usernameInput.value = "";
    passwordInput.value = "";
    setStatus("User added successfully.");
    await loadUsers();
  } catch (err) {
    setError(err.message);
    setStatus("");
  } finally {
    addButton.disabled = false;
  }
});

// ── Init ───────────────────────────────────────────────────────────────────────

loadUsers();
