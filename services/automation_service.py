import sqlite3
from datetime import datetime, timedelta
import requests
from config import SCHEDULE_DB, WEATHER_API_KEY, NOTIFICATION_RECIPIENTS
from services.email_service import send_notification, send_outlook_email
from services.logging_service import log_audit
from services.equipment_service import get_all_equipment  # Import missing function
from services.job_utils import needs_rerouting

def reroute_jobs():
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    today = datetime.now().date().strftime("%Y-%m-%d")
    c.execute("SELECT * FROM schedules WHERE start_date = ? AND status = 'scheduled'", (today,))
    jobs = c.fetchall()
    for job in jobs:
        if needs_rerouting(job):
            new_start = (datetime.strptime(job[3], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            new_end = (datetime.strptime(job[4], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            c.execute("UPDATE schedules SET start_date = ?, end_date = ?, status = 'rescheduled' WHERE id = ?",
                      (new_start, new_end, job[0]))
            log_audit("reroute", "system", job[0], job[7], {"reason": "weather/equipment"})
    conn.commit()
    conn.close()

def check_all_equipment_maintenance():
    equipments = get_all_equipment()  # Now imported
    for equipment in equipments:
        if equipment["hours"] >= equipment["maintenance_threshold"] and equipment["maintenance_threshold"]:
            subject = f"Equipment Maintenance Alert: {equipment['unique_id']}"
            body = f"Equipment '{equipment['unique_id']}' has reached {equipment['hours']} hours (threshold: {equipment['maintenance_threshold']}). Last maintenance: {equipment['last_maintenance'] or 'Never'}."
            send_notification(subject, body, NOTIFICATION_RECIPIENTS)
            log_audit(None, "maintenance_alert", {"equipment_id": equipment["id"], "unique_id": equipment["unique_id"], "hours": equipment["hours"]})

def update_weather(location="Site A"):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={WEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url).json()
        weather = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "location": location,
            "temp": response["main"]["temp"],
            "wind_speed": response["wind"]["speed"],
            "precipitation": response["rain"]["1h"] if "rain" in response else 0,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }
        conn = sqlite3.connect(SCHEDULE_DB)
        c = conn.cursor()
        c.execute("INSERT INTO weather (date, location, temp, wind_speed, precipitation, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                  (weather["date"], weather["location"], weather["temp"], weather["wind_speed"], weather["precipitation"], weather["timestamp"]))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Weather fetch failed: {e}")

def check_equipment_health():
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    # Align with equipment_instances schema
    c.execute("SELECT id, unique_id, hours, maintenance_threshold, last_maintenance FROM equipment_instances")
    equipment = c.fetchall()
    for eq in equipment:
        if eq[2] >= eq[3]:  # hours >= maintenance_threshold
            send_notification(
                f"Equipment Maintenance Needed: {eq[1]}",
                f"Equipment '{eq[1]}' has reached {eq[2]} hours of use (threshold: {eq[3]}). Last maintenance: {eq[4] or 'Never'}.",
                NOTIFICATION_RECIPIENTS
            )
            log_audit("maintenance_alert", "system", None, eq[1], {"usage_hours": eq[2]})
    conn.close()


def send_automated_emails():
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    today = datetime.now().date()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    c.execute("SELECT * FROM automation_rules WHERE active = 1")
    rules = c.fetchall()
    
    for rule in rules:
        rule_id, template_id, trigger_type, trigger_value, recipient_type, recipient_value, created_by, timestamp, active = rule
        
        c.execute("SELECT subject, body, outlook_enabled, cc, bcc, is_html FROM email_templates WHERE id = ?", (template_id,))
        template = c.fetchone()
        if not template:
            continue
        subject_template, body_template, outlook_enabled, cc, bcc, is_html = template
        
        c.execute("SELECT name, email FROM towns")
        city_emails = {row[0]: row[1] for row in c.fetchall()}
        c.execute("SELECT username, email FROM users WHERE role = 'manager'")
        managers = {row[0]: row[1] for row in c.fetchall()}

        if trigger_type == "days_before":
            days_before = int(trigger_value)
            trigger_date = today + timedelta(days=days_before)
            trigger_date_str = trigger_date.strftime("%Y-%m-%d")
            c.execute("SELECT * FROM schedules WHERE start_date <= ? AND end_date >= ? AND status = 'scheduled'", (trigger_date_str, trigger_date_str))
        elif trigger_type == "job_status":
            c.execute("SELECT * FROM schedules WHERE status = ?", (trigger_value,))
        
        jobs = c.fetchall()
        
        for job in jobs:
            job_id, resource_type, resource_name, start_date, end_date, start_time, end_time, job_name, job_number, description, location, user_id, status, timestamp = job
            if not description:
                description = "No description provided"
            if not location:
                location = "TBD"
            
            variables = {
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "start_time": start_time,
                "end_time": end_time,
                "description": description,
                "job_number": job_number or "N/A",
                "job_name": job_name,
                "resource_name": resource_name
            }
            
            subject = subject_template.format(**variables)
            body = body_template.format(**variables)
            
            if recipient_type == "location_city":
                recipient = city_emails.get(location, city_emails.get("TBD", "default.town@example.com"))
            elif recipient_type == "manager":
                recipient = managers.get(user_id, "default.manager@potelco.com")
            else:  # custom
                recipient = recipient_value or "default.town@example.com"

            sent = False
            if outlook_enabled and send_outlook_email(user_id, subject, body, recipient, cc=cc, bcc=bcc, is_html=is_html):
                sent = True
            elif send_notification(subject, body, [recipient], cc=cc, bcc=bcc, is_html=is_html):
                sent = True
            
            c.execute("UPDATE email_templates SET last_used = ? WHERE id = ?", (now, template_id))
            c.execute("INSERT INTO email_logs (template_id, job_id, recipient, subject, sent_timestamp, status) VALUES (?, ?, ?, ?, ?, ?)",
                      (template_id, job_id, recipient, subject, now, "sent" if sent else "failed"))
            log_audit("email_sent", "system", job_id, job_name, {"rule_id": rule_id, "recipient": recipient, "status": "sent" if sent else "failed"})

    conn.commit()
    conn.close()
