from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "dev-change-me"

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="enterprise_db"
    )

def login_required():
    """Return a 401 JSON response if the session has no user, else None."""
    if "user" not in session:
        return jsonify({"error": "Unauthorised"}), 401
    return None

# ── Auth routes ────────────────────────────────────────────────────────────────

@app.get("/login")
def login_page():
    err = request.args.get("err")
    return render_template("login.html", err=err)

@app.post("/login")
def login_submit():
    username = (request.form.get("user") or "").strip()
    password = (request.form.get("pass") or "").strip()

    if not username or not password:
        return redirect(url_for("login_page", err="missing"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and check_password_hash(user["password"], password):
        session["user"] = username
        return redirect("/dashboard/")

    return redirect(url_for("login_page", err="invalid"))

@app.get("/welcome")
def welcome():
    if "user" not in session:
        return redirect(url_for("login_page"))
    return render_template("welcome.html", user=session["user"])

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# ── Dashboard static serving ───────────────────────────────────────────────────

@app.get("/dashboard/")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login_page"))
    return send_from_directory("../dashboard", "index.html")

@app.get("/dashboard/css/<path:filename>")
def dashboard_css(filename):
    return send_from_directory("../dashboard/css", filename)

@app.get("/dashboard/js/<path:filename>")
def dashboard_js(filename):
    return send_from_directory("../dashboard/js", filename)

@app.get("/dashboard/img/<path:filename>")
def dashboard_img(filename):
    return send_from_directory("../dashboard/img", filename)

# ── User management page ───────────────────────────────────────────────────────

@app.get("/users")
def users_page():
    if "user" not in session:
        return redirect(url_for("login_page"))
    # index.html lives one level up from Login-Py/
    return send_from_directory(os.path.join(app.root_path, ".."), "index.html")

@app.get("/users/Scripts/<path:filename>")
def users_scripts(filename):
    return send_from_directory(os.path.join(app.root_path, "..", "Scripts"), filename)

# ── REST API: /api/users ───────────────────────────────────────────────────────

@app.get("/api/users")
def api_get_users():
    guard = login_required()
    if guard:
        return guard

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username FROM users ORDER BY id")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"data": rows})


@app.post("/api/users")
def api_create_user():
    guard = login_required()
    if guard:
        return guard

    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "").strip()

    if not username:
        return jsonify({"error": "Username is required"}), 400
    if not password:
        return jsonify({"error": "Password is required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    hashed = generate_password_hash(password)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hashed)
        )
        conn.commit()
        new_id = cursor.lastrowid
    except mysql.connector.errors.IntegrityError:
        cursor.close()
        conn.close()
        return jsonify({"error": f"Username '{username}' already exists"}), 409
    else:
        cursor.close()
        conn.close()

    return jsonify({"data": {"id": new_id, "username": username}}), 201


@app.delete("/api/users/<int:user_id>")
def api_delete_user(user_id):
    guard = login_required()
    if guard:
        return guard

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
    target = cursor.fetchone()

    if not target:
        cursor.close()
        conn.close()
        return jsonify({"error": "User not found"}), 404

    # Prevent a logged-in admin from deleting their own account
    if target["username"] == session.get("user"):
        cursor.close()
        conn.close()
        return jsonify({"error": "You cannot delete your own account"}), 403

    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "User deleted"}), 200


if __name__ == "__main__":
    app.run(debug=True)
