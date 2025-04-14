# services/schedule_service.py
import sqlite3
import logging
from config import SCHEDULE_DB, NOTIFICATION_RECIPIENTS
from datetime import datetime
from services.email_service import send_notification
from services.logging_service import log_audit

logging.basicConfig(filename='scheduling.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def check_conflicts(start_time, end_time, user_id, equipment_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    conflicts = []
    if user_id:
        c.execute("SELECT id, job, start_date, start_time, end_date, end_time FROM schedules WHERE user_id = ? AND ((start_date || ' ' || start_time < ? AND end_date || ' ' || end_time > ?) OR (start_date || ' ' || start_time < ? AND end_date || ' ' || end_time > ?))",
                  (user_id, end_time, start_time, start_time, end_time))
        user_conflicts = [f"User conflict with schedule {row[0]}: {row[1]} ({row[2]} {row[3]} to {row[4]} {row[5]})" for row in c.fetchall()]
        conflicts.extend(user_conflicts)
    if equipment_id:
        c.execute("SELECT id, job, start_date, start_time, end_date, end_time FROM schedules WHERE resource_name = ? AND ((start_date || ' ' || start_time < ? AND end_date || ' ' || end_time > ?) OR (start_date || ' ' || start_time < ? AND end_date || ' ' || end_time > ?))",
                  (equipment_id, end_time, start_time, start_time, end_time))
        equip_conflicts = [f"Equipment conflict with schedule {row[0]}: {row[1]} ({row[2]} {row[3]} to {row[4]} {row[5]})" for row in c.fetchall()]
        conflicts.extend(equip_conflicts)
    conn.close()
    if conflicts:
        logging.info(f"Conflicts detected for start={start_time}, end={end_time}, user_id={user_id}, equipment_id={equipment_id}: {conflicts}")
    return conflicts

def add_schedule(job, start_date, start_time, end_date, end_time, location, user_id, equipment_id, current_user_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    start_dt = f"{start_date} {start_time}"
    end_dt = f"{end_date} {end_time}"
    logging.info(f"Checking conflicts for job '{job}', equipment_id={equipment_id}, user_id={user_id}, start={start_dt}, end={end_dt}")
    conflicts = check_conflicts(start_dt, end_dt, user_id, equipment_id)
    if conflicts:
        subject = f"Schedule Conflict Alert: {job}"
        body = f"Cannot schedule '{job}' from {start_dt} to {end_dt} due to conflicts: {', '.join(conflicts)}"
        logging.error(f"Conflict error: {body}")
        send_notification(subject, body, NOTIFICATION_RECIPIENTS)
        raise ValueError(f"Schedule conflicts with existing events: {', '.join(conflicts)}")
    c.execute("INSERT INTO schedules (resource_type, resource_name, start_date, end_date, start_time, end_time, job, job_number, description, location, user_id, status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              ("equipment", equipment_id, start_date, end_date, start_time, end_time, job, None, None, location, user_id, "scheduled", datetime.now().isoformat()))
    schedule_id = c.lastrowid
    conn.commit()
    conn.close()
    try:
        log_audit(current_user_id, "add_schedule", {"schedule_id": schedule_id, "job": job})
    except Exception as e:
        logging.error(f"Audit logging failed for schedule {schedule_id}: {str(e)}")
        print(f"Warning: Audit logging failed for schedule {schedule_id}: {str(e)}")
    return schedule_id

def get_all_schedules():
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT id, job, start_date, start_time, end_date, end_time, location, user_id, status, job_number, description FROM schedules")
    schedules = [
        {
            "id": row[0],
            "job": row[1],
            "start_date": row[2],
            "start_time": row[3],
            "end_date": row[4],
            "end_time": row[5],
            "location": row[6],
            "user_id": row[7],
            "status": row[8],
            "job_number": row[9],
            "description": row[10]
        } for row in c.fetchall()
    ]
    conn.close()
    return schedules

def get_schedule_event(event_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT id, job, start_date, start_time, end_date, end_time, location, user_id, status, job_number, description, resource_name FROM schedules WHERE id = ?", (event_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return {
            "id": result[0],
            "job": result[1],
            "start_date": result[2],
            "start_time": result[3],
            "end_date": result[4],
            "end_time": result[5],
            "location": result[6],
            "user_id": result[7],
            "status": result[8],
            "job_number": result[9],
            "description": result[10],
            "resource_name": result[11]
        }
    return None

def update_schedule(schedule_id, job, start_date, start_time, end_date, end_time, location, user_id, equipment_id, current_user_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("UPDATE schedules SET resource_name=?, start_date=?, end_date=?, start_time=?, end_time=?, job=?, location=?, user_id=?, status=? WHERE id=?",
              (equipment_id, start_date, end_date, start_time, end_time, job, location, user_id, "scheduled", schedule_id))
    conn.commit()
    conn.close()
    log_audit(current_user_id, "update_schedule", {"schedule_id": schedule_id, "job": job})

def delete_schedule(schedule_id, current_user_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT job FROM schedules WHERE id = ?", (schedule_id,))
    result = c.fetchone()
    if result:
        job = result[0]
        c.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        conn.commit()
        log_audit(current_user_id, "delete_schedule", {"schedule_id": schedule_id, "job": job})
    conn.close()

def schedule_equipment_by_name(equipment_name, start_date, start_time, end_date, end_time, job):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT id, unique_id FROM equipment_instances WHERE unique_id LIKE ?", (f"%{equipment_name}%",))
    matches = c.fetchall()
    if not matches:
        conn.close()
        return f"No equipment found matching '{equipment_name}'."
    for equipment_id, equipment_label in matches:
        start_dt = f"{start_date} {start_time}"
        end_dt = f"{end_date} {end_time}"
        c.execute("SELECT 1 FROM schedules WHERE resource_name = ? AND NOT (end_date || ' ' || end_time <= ? OR start_date || ' ' || start_time >= ?)",
                  (equipment_id, start_dt, end_dt))
        if not c.fetchone():
            c.execute("INSERT INTO schedules (resource_type, resource_name, start_date, end_date, start_time, end_time, job, user_id, status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      ("equipment", equipment_id, start_date, end_date, start_time, end_time, job, None, "scheduled", datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"{equipment_label} scheduled from {start_dt} to {end_dt}."
    conn.close()
    return f"All units of '{equipment_name}' are currently in use or under maintenance."

def get_schedule_summary(days_ahead=1):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    today = datetime.now().date()
    future = today + timedelta(days=days_ahead)
    c.execute("""
        SELECT s.start_date, s.start_time, s.end_date, s.end_time, s.job, e.unique_id 
        FROM schedules s
        JOIN equipment_instances e ON s.resource_name = e.id
        WHERE date(s.start_date) BETWEEN ? AND ?
        ORDER BY s.start_date, s.start_time ASC
    """, (today.isoformat(), future.isoformat()))
    rows = c.fetchall()
    conn.close()
    return [f"{start_date} {start_time} - {end_date} {end_time} | {job} ({equip})" for start_date, start_time, end_date, end_time, job, equip in rows] or ["No jobs scheduled."]

def get_schedule_status(schedule_job):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT status FROM schedules WHERE job = ?", (schedule_job,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def check_availability(resource_name, start_date, end_date, start_time, end_time, cursor):
    start_dt = f"{start_date} {start_time}"
    end_dt = f"{end_date} {end_time}"
    cursor.execute("""
        SELECT s.job, s.start_date, s.start_time, s.end_date, s.end_time 
        FROM schedules s 
        WHERE s.resource_name = ? AND (
            (s.start_date || ' ' || s.start_time <= ? AND s.end_date || ' ' || s.end_time >= ?) OR
            (s.start_date || ' ' || s.start_time <= ? AND s.end_date || ' ' || s.end_time >= ?) OR
            (s.start_date || ' ' || s.start_time >= ? AND s.end_date || ' ' || s.end_time <= ?)
        )
    """, (resource_name, end_dt, start_dt, end_dt, start_dt, start_dt, end_dt))
    conflict = cursor.fetchone()
    if conflict:
        job, s_date, s_time, e_date, e_time = conflict
        return False, f"{resource_name} is booked for '{job}' from {s_date} {s_time} to {e_date} {e_time}."
    return True, ""

def get_inventory_quantity(item_name):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT quantity FROM consumables WHERE name = ?", (item_name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None