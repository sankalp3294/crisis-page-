from flask import Flask, render_template, request, redirect
import sqlite3
import google.generativeai as genai
import os
from dotenv import load_dotenv
from flask import session

load_dotenv()

app = Flask(__name__)
app.secret_key = "crisislink_secret_key"
DB_PATH = "database/incidents.db"

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")


# create db
def init_db():
    conn = sqlite3.connect("database/incidents.db")
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS incidents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        room TEXT,
        emergency_type TEXT,
        description TEXT,
        ai_result TEXT,
        status TEXT DEFAULT 'Pending'
    )
    """)

    conn.commit()
    conn.close()


def analyze_emergency(text):
    try:
        response = model.generate_content(
            f"Classify this emergency and give severity in short: {text}"
        )
        return response.text

    except Exception:
        text = text.lower()

        if "fire" in text or "smoke" in text:
            return "Critical - Fire Emergency"

        elif "blood" in text or "heart" in text or "medical" in text:
            return "High - Medical Emergency"

        elif "fight" in text or "weapon" in text:
            return "High - Security Threat"

        else:
            return "Medium - Needs Attention"


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    name = request.form["name"]
    room = request.form["room"]
    emergency_type = request.form["type"]
    description = request.form["description"]

    ai_result = analyze_emergency(description)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO incidents(name, room, emergency_type, description, ai_result, status)
VALUES (?, ?, ?, ?, ?, ?)
    """, (name, room, emergency_type, description, ai_result, "Pending"))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if session.get("role") != "staff":
        return redirect("/login")

    conn = sqlite3.connect("database/incidents.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM incidents ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()

    return render_template("dashboard.html", data=data)


@app.route("/update_status/<int:id>/<status>", methods=["GET", "POST"])
def update_status(id, status):
    if session.get("role") != "staff":
        return redirect("/login")

    conn = sqlite3.connect("database/incidents.db")
    cur = conn.cursor()

    cur.execute(
        "UPDATE incidents SET status=? WHERE id=?",
        (status, id)
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "staff" and password == "1234":
            session["role"] = "staff"
            return redirect("/dashboard")

    return render_template("login.html")

@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
    
