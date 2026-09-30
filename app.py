from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "skillbridge-demo-secret"
DB = Path(__file__).with_name("skillbridge.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        department TEXT NOT NULL,
        year INTEGER NOT NULL,
        skills TEXT NOT NULL,
        goals TEXT NOT NULL,
        availability TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        partner_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        reason TEXT NOT NULL,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(partner_id) REFERENCES students(id)
    );
    """)
    count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if count == 0:
        sample = [
            ("Aarav Kumar","aarav@example.com","CSE",3,"Python, SQL, Flask","Build web applications","Evenings"),
            ("Meera Reddy","meera@example.com","AIML",2,"Python, Machine Learning, Pandas","Learn backend development","Weekends"),
            ("Rahul Varma","rahul@example.com","ECE",3,"JavaScript, HTML, CSS","Learn data analytics","Evenings"),
            ("Sana Ali","sana@example.com","CSE",4,"SQL, Power BI, Python","Improve dashboard design","Mornings"),
            ("Vikram Rao","vikram@example.com","IT",2,"JavaScript, React, CSS","Learn Python","Weekends"),
            ("Ananya Singh","ananya@example.com","AIML",3,"Machine Learning, Python, SQL","Create an AI project","Evenings")
        ]
        conn.executemany("""
            INSERT INTO students(name,email,department,year,skills,goals,availability)
            VALUES(?,?,?,?,?,?,?)
        """, sample)
        conn.commit()
    conn.close()

def skill_set(text):
    return {x.strip().lower() for x in text.split(",") if x.strip()}

def calculate_match(a, b):
    a_skills = skill_set(a["skills"])
    b_skills = skill_set(b["skills"])
    a_goals = skill_set(a["goals"].replace("Build ","").replace("Learn ","").replace("Improve ","").replace("Create ",""))
    b_goals = skill_set(b["goals"].replace("Build ","").replace("Learn ","").replace("Improve ","").replace("Create ",""))
    shared = a_skills & b_skills
    teach_a = any(goal in " ".join(a_skills) for goal in [b["goals"].lower()])
    teach_b = any(goal in " ".join(b_skills) for goal in [a["goals"].lower()])
    score = min(100, len(shared)*15 + (20 if teach_a else 0) + (20 if teach_b else 0) + (15 if a["availability"] == b["availability"] else 0))
    if score < 25 and shared:
        score = 25
    reason_parts = []
    if shared:
        reason_parts.append("shared skills: " + ", ".join(sorted(shared)))
    if teach_a or teach_b:
        reason_parts.append("their skills align with each other's learning goals")
    if a["availability"] == b["availability"]:
        reason_parts.append("matching availability")
    if not reason_parts:
        reason_parts.append("similar academic interests")
    return score, "; ".join(reason_parts)

@app.route("/")
def index():
    conn = get_db()
    students = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    total = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    matches = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    conn.close()
    return render_template("index.html", students=students, total=total, matches=matches)

@app.route("/add", methods=["GET","POST"])
def add_student():
    if request.method == "POST":
        data = (
            request.form["name"].strip(), request.form["email"].strip(),
            request.form["department"], int(request.form["year"]),
            request.form["skills"].strip(), request.form["goals"].strip(),
            request.form["availability"]
        )
        conn = get_db()
        try:
            conn.execute("""INSERT INTO students
                (name,email,department,year,skills,goals,availability)
                VALUES(?,?,?,?,?,?,?)""", data)
            conn.commit()
            flash("Student profile created successfully.", "success")
            return redirect(url_for("index"))
        except sqlite3.IntegrityError:
            flash("That email already exists. Please use another email.", "error")
        finally:
            conn.close()
    return render_template("add.html")

@app.route("/match/<int:student_id>")
def match(student_id):
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    others = conn.execute("SELECT * FROM students WHERE id != ?", (student_id,)).fetchall()
    results = []
    for other in others:
        score, reason = calculate_match(student, other)
        results.append({"student": other, "score": score, "reason": reason})
    results.sort(key=lambda x: x["score"], reverse=True)
    conn.execute("DELETE FROM matches WHERE student_id=?", (student_id,))
    for r in results[:5]:
        conn.execute("INSERT INTO matches(student_id,partner_id,score,reason) VALUES(?,?,?,?)",
                     (student_id, r["student"]["id"], r["score"], r["reason"]))
    conn.commit()
    conn.close()
    return render_template("matches.html", student=student, results=results[:5])

@app.route("/students")
def students():
    conn = get_db()
    rows = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    conn.close()
    return render_template("students.html", students=rows)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
