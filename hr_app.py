import os
import shutil
import sqlite3

from flask import Flask, jsonify, request, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
DB = os.path.join(DATA, "hr.db")
CV_ROOT = os.path.join(DATA, "cvs")

# A candidate's status is also the name of the folder holding their CV.
FOLDERS = [
    "submitted",
    "interview",
    "submission_rejected",
    "interview_rejected",
    "selected_final",
]

# status -> (status after green button, status after red button)
FLOW = {
    "submitted": ("interview", "submission_rejected"),
    "interview": ("selected_final", "interview_rejected"),
}

app = Flask(__name__)

for folder in FOLDERS:
    os.makedirs(os.path.join(CV_ROOT, folder), exist_ok=True)


def run(sql, args=()):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, args)
    rows = cur.fetchall()
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return rows, last_id


run(
    """CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        job_role TEXT NOT NULL,
        message TEXT,
        status TEXT NOT NULL DEFAULT 'submitted',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )"""
)


def cv_path(status, app_id):
    return os.path.join(CV_ROOT, status, f"{app_id}.pdf")


@app.after_request
def allow_form(resp):
    # The applicant form is a separate page, so it needs cross-origin access.
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.get("/")
def home():
    return send_from_directory(BASE, "hr_page.html")


@app.post("/api/applications")
def submit_application():
    f = request.form
    _, app_id = run(
        "INSERT INTO applications (full_name, email, job_role, message) VALUES (?, ?, ?, ?)",
        (f["full_name"], f["email"], f["job_role"], f.get("message", "")),
    )
    request.files["cv"].save(cv_path("submitted", app_id))
    return jsonify(id=app_id), 201


@app.get("/api/applications")
def list_applications():
    status = request.args.get("status", "submitted")
    rows, _ = run(
        "SELECT id, full_name, email, job_role, message, created_at "
        "FROM applications WHERE status = ? ORDER BY id",
        (status,),
    )
    return jsonify([dict(r) for r in rows])


def move(app_id, index):
    rows, _ = run("SELECT status FROM applications WHERE id = ?", (app_id,))
    old = rows[0]["status"]
    new = FLOW[old][index]
    shutil.move(cv_path(old, app_id), cv_path(new, app_id))
    run("UPDATE applications SET status = ? WHERE id = ?", (new, app_id))
    return jsonify(status=new)


@app.post("/api/applications/<int:app_id>/accept")
def accept(app_id):
    return move(app_id, 0)


@app.post("/api/applications/<int:app_id>/reject")
def reject(app_id):
    return move(app_id, 1)


@app.get("/cv/<int:app_id>")
def get_cv(app_id):
    rows, _ = run("SELECT status FROM applications WHERE id = ?", (app_id,))
    return send_from_directory(os.path.join(CV_ROOT, rows[0]["status"]), f"{app_id}.pdf")


if __name__ == "__main__":
    app.run(port=5000)
