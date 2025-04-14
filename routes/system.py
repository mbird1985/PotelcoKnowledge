from flask import Blueprint, render_template
from flask_login import login_required
from services.db import get_connection
from services.equipment_service import get_all_equipment
from datetime import datetime, timedelta  # Add datetime import
import sqlite3
from config import SCHEDULE_DB

system_bp = Blueprint('system', __name__)

@system_bp.route('/dashboard')
@login_required
def dashboard():
    # Get current week boundaries (Monday to Sunday)
    today = datetime.now().date()
    # Find the Monday of the current week
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    conn = get_connection()
    c = conn.cursor()
    
    # Jobs scheduled this week
    c.execute("""
        SELECT COUNT(*) 
        FROM schedules 
        WHERE date(start_date) BETWEEN ? AND ?
    """, (monday.isoformat(), sunday.isoformat()))
    jobs_this_week = c.fetchone()[0]
    
    # Total hours for jobs this week
    c.execute("""
        SELECT start_date, start_time, end_date, end_time 
        FROM schedules 
        WHERE date(start_date) BETWEEN ? AND ?
    """, (monday.isoformat(), sunday.isoformat()))
    total_hours = 0
    for row in c.fetchall():
        start_dt = datetime.fromisoformat(f"{row[0]}T{row[1]}")
        end_dt = datetime.fromisoformat(f"{row[2]}T{row[3]}")
        hours = (end_dt - start_dt).total_seconds() / 3600
        total_hours += hours
    
    conn.close()
    
    # Equipment due for maintenance
    equipment_list = get_all_equipment()
    maintenance_due = [
        equip for equip in equipment_list
        if equip["maintenance_threshold"] and equip["hours"] >= equip["maintenance_threshold"]
    ]
    maintenance_due_count = len(maintenance_due)
    maintenance_due_labels = [equip["unique_id"] for equip in maintenance_due]
    maintenance_due_hours = [equip["hours"] for equip in maintenance_due]
    
    return render_template(
        "dashboard.html",
        jobs_this_week=jobs_this_week,
        total_hours=round(total_hours, 2),
        maintenance_due_count=maintenance_due_count,
        maintenance_due_labels=maintenance_due_labels,
        maintenance_due_hours=maintenance_due_hours
    )

@system_bp.route("/status")
@login_required
def health_check():
    return jsonify({"status": "ok", "message": "System operational"})
def status():
    return render_template("status.html")

@system_bp.route("/audit")
@login_required
def audit():
    logs = get_audit_logs()
    return render_template("audit.html", logs=logs)

@system_bp.route("/health")
def health():
    try:
        # Database check
        conn = sqlite3.connect(SCHEDULE_DB)
        conn.execute("SELECT 1")
        conn.close()

        # LLM check
        r = requests.post("http://127.0.0.1:11435/api/generate", json={"model": "llama3", "prompt": "ping"})
        llm_status = r.status_code == 200

        return jsonify({
            "status": "healthy",
            "database": "ok",
            "llm": "ok" if llm_status else "error"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

