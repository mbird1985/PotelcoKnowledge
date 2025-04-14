from services.db import get_connection
from config import SCHEDULE_DB, NOTIFICATION_RECIPIENTS
from services.logging_service import log_audit  # Add this
from services.email_service import send_notification  # Add this
from flask_login import current_user  # Add this

def get_equipment_status(equipment_filter=None):
    conn = get_connection()
    c = conn.cursor()
    if equipment_filter:
        c.execute("SELECT unique_id, status FROM equipment_instances WHERE unique_id LIKE ?", (f"%{equipment_filter}%",))
    else:
        c.execute("SELECT unique_id, status FROM equipment_instances")
    rows = c.fetchall()
    conn.close()
    return [f"{unique_id}: {status}" for unique_id, status in rows] or ["No equipment found."]

def add_equipment(equipment_type, unique_id, brand, model, serial_number, hours, fuel_type, gross_weight, requires_operator, required_certification, status, last_maintenance, maintenance_threshold, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO equipment_instances (equipment_type, unique_id, brand, model, serial_number, hours, fuel_type, gross_weight, requires_operator, required_certification, status, last_maintenance, maintenance_threshold) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (equipment_type, unique_id, brand, model, serial_number, hours, fuel_type, gross_weight, requires_operator, required_certification, status, last_maintenance, maintenance_threshold))
    equipment_id = c.lastrowid
    conn.commit()
    conn.close()
    log_audit(user_id, "add_equipment", {"equipment_id": equipment_id, "unique_id": unique_id})
    return equipment_id

def update_equipment(equipment_id, equipment_type, unique_id, brand, model, serial_number, hours, fuel_type, gross_weight, requires_operator, required_certification, status, last_maintenance, maintenance_threshold, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE equipment_instances SET equipment_type=?, unique_id=?, brand=?, model=?, serial_number=?, hours=?, fuel_type=?, gross_weight=?, requires_operator=?, required_certification=?, status=?, last_maintenance=?, maintenance_threshold=? WHERE id=?",
              (equipment_type, unique_id, brand, model, serial_number, hours, fuel_type, gross_weight, requires_operator, required_certification, status, last_maintenance, maintenance_threshold, equipment_id))
    conn.commit()
    conn.close()
    log_audit(user_id, "update_equipment", {"equipment_id": equipment_id, "unique_id": unique_id})
    check_maintenance_alert(equipment_id, user_id)

def check_maintenance_alert(equipment_id, user_id):
    equipment = get_equipment_detail(equipment_id)
    if equipment and equipment["hours"] >= equipment["maintenance_threshold"] and equipment["maintenance_threshold"]:
        subject = f"Equipment Maintenance Alert: {equipment['unique_id']}"
        body = f"Equipment '{equipment['unique_id']}' has reached {equipment['hours']} hours (threshold: {equipment['maintenance_threshold']}). Last maintenance: {equipment['last_maintenance'] or 'Never'}."
        send_notification(subject, body, NOTIFICATION_RECIPIENTS)
        log_audit(user_id, "maintenance_alert", {"equipment_id": equipment_id, "unique_id": equipment["unique_id"], "hours": equipment["hours"]})

def check_all_equipment_maintenance():
    """Check maintenance status for all equipment and trigger alerts if needed."""
    equipment_list = get_all_equipment()
    for equipment in equipment_list:
        if equipment["hours"] >= equipment["maintenance_threshold"] and equipment["maintenance_threshold"]:
            subject = f"Equipment Maintenance Alert: {equipment['unique_id']}"
            body = f"Equipment '{equipment['unique_id']}' has reached {equipment['hours']} hours (threshold: {equipment['maintenance_threshold']}). Last maintenance: {equipment['last_maintenance'] or 'Never'}."
            send_notification(subject, body, NOTIFICATION_RECIPIENTS)
            log_audit(None, "maintenance_alert", {
                "equipment_id": equipment["id"],
                "unique_id": equipment["unique_id"],
                "hours": equipment["hours"]
            })

def get_equipment_detail(equipment_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, equipment_type, unique_id, brand, model, serial_number, hours, fuel_type, gross_weight, requires_operator, required_certification, status, last_maintenance, maintenance_threshold FROM equipment_instances WHERE id = ?", (equipment_id,))
    equipment = c.fetchone()
    conn.close()
    return {
        "id": equipment[0], "equipment_type": equipment[1], "unique_id": equipment[2], "brand": equipment[3],
        "model": equipment[4], "serial_number": equipment[5], "hours": equipment[6], "fuel_type": equipment[7],
        "gross_weight": equipment[8], "requires_operator": equipment[9], "required_certification": equipment[10],
        "status": equipment[11], "last_maintenance": equipment[12], "maintenance_threshold": equipment[13]
    } if equipment else None

def get_all_equipment():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, equipment_type, unique_id, brand, model, serial_number, hours, fuel_type, gross_weight, requires_operator, required_certification, status, last_maintenance, maintenance_threshold FROM equipment_instances")
    rows = c.fetchall()
    conn.close()
    return [{
        "id": row[0], "equipment_type": row[1], "unique_id": row[2], "brand": row[3], "model": row[4],
        "serial_number": row[5], "hours": row[6], "fuel_type": row[7], "gross_weight": row[8],
        "requires_operator": bool(row[9]), "required_certification": row[10], "status": row[11],
        "last_maintenance": row[12], "maintenance_threshold": row[13]
    } for row in rows]

def get_equipment_by_id(equipment_id):
    return get_equipment_detail(equipment_id)

def delete_equipment(equipment_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM equipment_instances WHERE id = ?", (equipment_id,))
    conn.commit()
    conn.close()
    log_audit(current_user.id if current_user.is_authenticated else None, "delete_equipment", {"equipment_id": equipment_id})