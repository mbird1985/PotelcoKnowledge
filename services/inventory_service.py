# services/inventory_service.py
import sqlite3
import logging
from config import SCHEDULE_DB, NOTIFICATION_RECIPIENTS
from services.logging_service import log_audit
from services.email_service import send_notification

logging.basicConfig(filename='inventory.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_inventory_item(item_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT id, name, location, quantity, supplier, serial_numbers, unit, reorder_threshold FROM consumables WHERE id = ?", (item_id,))
    item = c.fetchone()
    conn.close()
    return {"id": item[0], "name": item[1], "location": item[2], "quantity": item[3], "supplier": item[4], "serial_numbers": item[5], "unit": item[6], "reorder_threshold": item[7]} if item else None

def get_inventory_summary():
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT name, quantity, unit FROM consumables")
    rows = c.fetchall()
    conn.close()
    return [f"{name}: {qty} {unit}" for name, qty, unit in rows]

def get_inventory_quantity(item_name):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT quantity FROM consumables WHERE name = ?", (item_name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_all_consumables():
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT id, name, location, quantity, supplier, serial_numbers, unit, reorder_threshold FROM consumables")
    items = [
        {
            "id": row[0],
            "name": row[1],
            "location": row[2] or "",
            "quantity": row[3],
            "supplier": row[4] or "",
            "serial_numbers": eval(row[5]) if row[5] else [],
            "unit": row[6] or "",
            "reorder_threshold": row[7]
        } for row in c.fetchall()
    ]
    conn.close()
    logging.info(f"Fetched {len(items)} consumables: {[item['name'] for item in items]}")
    return items

def add_consumable(name, location, quantity, supplier, serial_numbers, unit, reorder_threshold, user_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("INSERT INTO consumables (name, location, quantity, supplier, serial_numbers, unit, reorder_threshold) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (name, location, quantity, supplier, serial_numbers, unit, reorder_threshold))
    item_id = c.lastrowid
    conn.commit()
    conn.close()
    log_audit(user_id, "add_consumable", {"item_id": item_id, "name": name})
    check_reorder_alert(item_id, user_id)
    return item_id

def update_consumable(item_id, name, location, quantity, supplier, serial_numbers, unit, reorder_threshold, user_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("UPDATE consumables SET name=?, location=?, quantity=?, supplier=?, serial_numbers=?, unit=?, reorder_threshold=? WHERE id=?",
              (name, location, quantity, supplier, serial_numbers, unit, reorder_threshold, item_id))
    conn.commit()
    conn.close()
    log_audit(user_id, "update_consumable", {"item_id": item_id, "name": name})
    check_reorder_alert(item_id, user_id)

def delete_consumable(item_id, user_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT name FROM consumables WHERE id = ?", (item_id,))
    result = c.fetchone()
    if result:
        name = result[0]
        c.execute("DELETE FROM consumables WHERE id = ?", (item_id,))
        conn.commit()
        log_audit(user_id, "delete_consumable", {"item_id": item_id, "name": name})
    conn.close()

def check_reorder_alert(item_id, user_id):
    item = get_inventory_item(item_id)
    if item and item["quantity"] <= item["reorder_threshold"]:
        subject = f"Inventory Reorder Alert: {item['name']}"
        body = f"Item '{item['name']}' at {item['location']} has {item['quantity']} {item['unit']} remaining (threshold: {item['reorder_threshold']}). Please reorder."
        send_notification(subject, body, NOTIFICATION_RECIPIENTS)
        log_audit(user_id, "reorder_alert", {"item_id": item_id, "name": item["name"], "quantity": item["quantity"]})