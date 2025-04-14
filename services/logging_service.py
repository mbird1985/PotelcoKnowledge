# services/logging_service.py
import sqlite3
from datetime import datetime
from config import SCHEDULE_DB
from services.elasticsearch_client import es  # Use shared client
import logging

# Configure fallback logging
logging.basicConfig(filename='audit_fallback.log', level=logging.WARNING,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def log_analytics(event_type, data):
    try:
        if not es.indices.exists(index="analytics"):
            es.indices.create(index="analytics")
        es.index(index="analytics", body={
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        })
        es.indices.refresh(index="analytics")
    except Exception as e:
        logging.error(f"Failed to log analytics event '{event_type}': {str(e)}")
        print(f"Analytics logging failed: {str(e)}")

def log_audit(action, user_id, document_id=None, document_title=None, details=None):
    try:
        if not es.indices.exists(index="audit"):
            es.indices.create(index="audit")
        audit_entry = {
            "action": action,
            "user_id": user_id,
            "document_id": document_id,
            "document_title": document_title,
            "details": details or {},
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }
        es.index(index="audit", body=audit_entry)
        es.indices.refresh(index="audit")
        print(f"Audit logged: {audit_entry}")
    except Exception as e:
        logging.error(f"Failed to log audit action '{action}' for user {user_id}: {str(e)}")
        print(f"Audit logging failed: {str(e)}")

CITY_EMAILS = {
    "Site A": "sitea.town@example.com",
    "Site B": "siteb.town@example.com",
    "TBD": "default.town@example.com"
}

def get_audit_logs():
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT * FROM audit_log ORDER BY timestamp DESC")
    logs = c.fetchall()
    conn.close()
    return logs