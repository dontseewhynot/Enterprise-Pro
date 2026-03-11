from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "dev-change-me"

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="enterprise_db"
    )



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

    cursor.execute(
    "SELECT * FROM users WHERE username = %s",
    (username,)
)

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


if __name__ == "__main__":
    app.run(debug=True)

