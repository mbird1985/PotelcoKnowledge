import sqlite3
from datetime import datetime  # Add this
from config import SCHEDULE_DB
from werkzeug.security import generate_password_hash
from services.logging_service import log_audit  # Add this

def get_all_users(role_filter=None):
    conn = sqlite3.connect(SCHEDULE_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if role_filter:
        c.execute("SELECT * FROM users WHERE role = ? ORDER BY username ASC", (role_filter,))
    else:
        c.execute("SELECT * FROM users ORDER BY username ASC")
    users = [dict(u) for u in c.fetchall()]
    conn.close()
    return users

def get_user_by_id(user_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def add_user(username, full_name, email, job_title, role, password, certifications, user_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    hashed_password = generate_password_hash(password)
    c.execute("INSERT INTO users (username, full_name, email, job_title, role, password, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (username, full_name, email, job_title, role, hashed_password, datetime.now().isoformat()))
    new_user_id = c.lastrowid
    for cert_id in certifications or []:  # Handle None or empty list
        c.execute("INSERT OR IGNORE INTO user_certifications (user_id, cert_id) VALUES (?, ?)", (new_user_id, cert_id))
    conn.commit()
    conn.close()
    log_audit(user_id, "add_user", {"new_user_id": new_user_id, "username": username})
    return new_user_id

def update_user(user_id, username, full_name, email, job_title, role, certifications, current_user_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("UPDATE users SET username=?, full_name=?, email=?, job_title=?, role=? WHERE id=?", 
              (username, full_name, email, job_title, role, user_id))
    c.execute("DELETE FROM user_certifications WHERE user_id=?", (user_id,))
    for cert_id in certifications or []:  # Handle None or empty list
        c.execute("INSERT OR IGNORE INTO user_certifications (user_id, cert_id) VALUES (?, ?)", (user_id, cert_id))
    conn.commit()
    conn.close()
    log_audit(current_user_id, "update_user", {"user_id": user_id, "username": username})

def delete_user(user_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("DELETE FROM user_certifications WHERE user_id = ?", (user_id,))
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    log_audit(None, "delete_user", {"user_id": user_id})

def get_user_certifications(user_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT c.id, c.name FROM certifications c JOIN user_certifications uc ON c.id = uc.cert_id WHERE uc.user_id = ?", (user_id,))
    certs = [{"id": row[0], "name": row[1]} for row in c.fetchall()]
    conn.close()
    return certs

def resolve_certifications(cert_names):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    cert_ids = []
    for name in cert_names or []:  # Handle None or empty list
        name = name.strip().lower()
        if not name:
            continue
        c.execute("SELECT id FROM certifications WHERE name = ?", (name,))
        result = c.fetchone()
        if result:
            cert_ids.append(result[0])
        else:
            c.execute("INSERT INTO certifications (name) VALUES (?)", (name,))
            cert_ids.append(c.lastrowid)
    conn.commit()
    conn.close()
    return cert_ids

def get_all_certifications():
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT id, name FROM certifications")
    certs = [{"id": row[0], "name": row[1]} for row in c.fetchall()]
    conn.close()
    return certs