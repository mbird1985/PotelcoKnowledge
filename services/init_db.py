# services/init_db.py
import os
import sqlite3
from datetime import datetime
from flask_login import UserMixin
from config import SCHEDULE_DB, DOCUMENT_FOLDER as UPLOAD_FOLDER, ES_HOST, ES_USER, ES_PASS
import json
from elasticsearch import Elasticsearch
from werkzeug.security import generate_password_hash

es = Elasticsearch([ES_HOST], http_auth=(ES_USER, ES_PASS))

# Initialize Elasticsearch index at module level
if not es.indices.exists(index='knowledge_base'):
    es.indices.create(index='knowledge_base', body={
        'mappings': {
            'properties': {
                'text': {'type': 'text'},
                'filename': {'type': 'keyword'}
            }
        }
    })

def init_db():
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()

    # Drop and recreate user_certifications to ensure correct schema
    c.execute("DROP TABLE IF EXISTS user_certifications")
    c.execute('''CREATE TABLE user_certifications (
        user_id INTEGER,
        cert_id INTEGER,
        PRIMARY KEY (user_id, cert_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (cert_id) REFERENCES certifications(id)
    )''')

    # Single, consistent equipment_instances table
    c.execute("DROP TABLE IF EXISTS equipment_instances")
    c.execute('''CREATE TABLE IF NOT EXISTS equipment_instances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_type TEXT NOT NULL,
        unique_id TEXT NOT NULL UNIQUE,
        brand TEXT,
        model TEXT,
        serial_number TEXT,
        hours REAL DEFAULT 0,
        fuel_type TEXT,
        gross_weight REAL,
        requires_operator INTEGER DEFAULT 0,
        required_certification TEXT,
        status TEXT DEFAULT 'available',
        last_maintenance TEXT,
        maintenance_threshold INTEGER
    )''')

    # Initial equipment data
    initial_equipment = [
        ("Boom Truck", "BT001", "Ford", "F-550", "1FT8W3BTXJEB12345", 0, "diesel", 19500, 1, "boom_operator", "available", None, 1000),
        ("Boom Truck", "BT002", "Ford", "F-550", "1FT8W3BTXJEB12346", 0, "diesel", 19500, 1, "boom_operator", "available", None, 1000),
        ("Crane", "CR001", "Terex", "T340-1XL", "123456789", 0, "diesel", 66000, 1, "crane_certified", "available", None, 500),
        ("Drill Rig", "DR001", "Atlas Copco", "FlexiROC D65", "987654321", 0, "diesel", 45000, 0, None, "available", None, 800),
        ("Loader", "LD001", "Caterpillar", "950M", "CAT0950M12345", 0, "diesel", 42500, 1, "forklift", "available", None, 600)
    ]
    for eq_type, unique_id, brand, model, serial, hours, fuel, weight, req_op, cert, status, last_maint, maint_thresh in initial_equipment:
        c.execute("INSERT OR IGNORE INTO equipment_instances (equipment_type, unique_id, brand, model, serial_number, hours, fuel_type, gross_weight, requires_operator, required_certification, status, last_maintenance, maintenance_threshold) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (eq_type, unique_id, brand, model, serial, hours, fuel, weight, req_op, cert, status, last_maint, maint_thresh))

    # Schedules table
    c.execute('''CREATE TABLE IF NOT EXISTS schedules
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  resource_type TEXT NOT NULL,
                  resource_name TEXT NOT NULL,
                  start_date TEXT NOT NULL,
                  end_date TEXT NOT NULL,
                  start_time TEXT NOT NULL,
                  end_time TEXT NOT NULL,
                  job TEXT NOT NULL,
                  job_number TEXT,
                  description TEXT,
                  location TEXT,
                  user_id TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'scheduled',
                  timestamp TEXT NOT NULL)''')

    c.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        uploader_id INTEGER,
        upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
        tags TEXT,
        description TEXT,
        FOREIGN KEY (uploader_id) REFERENCES users(id))""")

    c.execute('''CREATE TABLE IF NOT EXISTS certifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )''')

    # Users table and initial data
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL UNIQUE,
                  full_name TEXT,
                  email TEXT NOT NULL,
                  job_title TEXT,
                  role TEXT NOT NULL,
                  password TEXT NOT NULL,
                  certifications TEXT,
                  timestamp TEXT NOT NULL)''')

    initial_users = [
        ("admin", "Admin User", "admin@potelco.com", "System Administrator", "admin", generate_password_hash("potelco123"), '{"forklift": true, "commercial_driver": true}', datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
        ("manager1", "Jane Manager", "manager1@potelco.com", "Site Manager", "manager", generate_password_hash("mgr2025"), '{"forklift": true}', datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
        ("user1", "John Worker", "user1@potelco.com", "Operator", "user", generate_password_hash("worker123"), '{"boom_operator": true}', datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    ]
    for username, full_name, email, job_title, role, password, certifications, timestamp in initial_users:
        c.execute("INSERT OR IGNORE INTO users (username, full_name, email, job_title, role, password, certifications, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (username, full_name, email, job_title, role, password, certifications, timestamp))

    # Initial certifications
    initial_certifications = [
        ("Crane Operator",),
        ("Forklift Operator",),
        ("Electrical Safety",),
    ]
    c.executemany("INSERT OR IGNORE INTO certifications (name) VALUES (?)", initial_certifications)

    # Assign certifications to admin (user id 1)
    c.execute("INSERT OR IGNORE INTO user_certifications (user_id, cert_id) VALUES (1, (SELECT id FROM certifications WHERE name='Crane Operator'))")
    c.execute("INSERT OR IGNORE INTO user_certifications (user_id, cert_id) VALUES (1, (SELECT id FROM certifications WHERE name='Electrical Safety'))")

    # Consumables table
    c.execute("DROP TABLE IF EXISTS consumables")
    c.execute('''CREATE TABLE consumables
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL UNIQUE,
                  location TEXT,
                  quantity INTEGER DEFAULT 0,
                  supplier TEXT,
                  serial_numbers TEXT,
                  unit TEXT)''')

    initial_consumables = [
        ("Wire", "Warehouse-Bay 3-Shelf 2", 1000, "PowerLine Supplies", None, "feet"),
        ("Connectors", "Warehouse-Bay 5-Shelf 1", 500, "GridTech", None, "units"),
        ("Tape", "Back Lot-Section B", 100, "ElectroMart", None, "rolls"),
        ("PPE Gloves", "Warehouse-Bay 2-Shelf 3", 200, "SafetyGear Inc", None, "pairs"),
        ("Transformer", "Warehouse-Bay 10", 5, "TransCo", '["T001", "T002", "T003", "T004", "T005"]', "units"),
        ("Insulators", "Back Lot-Section A", 150, "GridTech", None, "units"),
        ("Bolts", "Warehouse-Bay 4-Shelf 2", 2000, "Fastener Co", None, "units"),
        ("Crossarms", "Back Lot-Section C", 20, "PowerLine Supplies", None, "units")
    ]
    for name, location, qty, supplier, serials, unit in initial_consumables:
        c.execute("INSERT INTO consumables (name, location, quantity, supplier, serial_numbers, unit) VALUES (?, ?, ?, ?, ?, ?)",
                  (name, location, qty, supplier, serials, unit))

    # Add reorder_threshold to consumables if missing
    c.execute("PRAGMA table_info(consumables)")
    columns = [col[1] for col in c.fetchall()]
    if 'reorder_threshold' not in columns:
        c.execute("ALTER TABLE consumables ADD COLUMN reorder_threshold INTEGER")

    # Other tables
    c.execute('''CREATE TABLE IF NOT EXISTS job_resources
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  schedule_id INTEGER NOT NULL,
                  resource_type TEXT NOT NULL,
                  resource_id INTEGER NOT NULL,
                  quantity INTEGER DEFAULT 1,
                  assigned_user_id INTEGER,
                  FOREIGN KEY (schedule_id) REFERENCES schedules(id))''')
    try:
        c.execute("ALTER TABLE job_resources ADD COLUMN assigned_user_id INTEGER")
    except sqlite3.OperationalError:
        pass

    c.execute('''CREATE TABLE IF NOT EXISTS weather
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL,
                  location TEXT NOT NULL,
                  temp REAL,
                  wind_speed REAL,
                  precipitation REAL,
                  timestamp TEXT NOT NULL)''')

    c.execute('''CREATE TABLE IF NOT EXISTS email_templates
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL UNIQUE,
                  subject TEXT NOT NULL,
                  body TEXT NOT NULL,
                  created_by TEXT NOT NULL,
                  timestamp TEXT NOT NULL)''')

    try:
        c.execute("ALTER TABLE email_templates ADD COLUMN outlook_enabled INTEGER DEFAULT 1")
        c.execute("ALTER TABLE email_templates ADD COLUMN last_used TEXT")
        c.execute("ALTER TABLE email_templates ADD COLUMN cc TEXT")
        c.execute("ALTER TABLE email_templates ADD COLUMN bcc TEXT")
        c.execute("ALTER TABLE email_templates ADD COLUMN is_html INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    c.execute("INSERT OR IGNORE INTO email_templates (name, subject, body, created_by, timestamp, outlook_enabled) VALUES (?, ?, ?, ?, ?, ?)",
              ("Town Notification", "Upcoming Potelco Work in {location}", 
               "Hello,\n\nWork will be conducted at {location} doing {description} on {start_date} from {start_time} to {end_date} at {end_time}. Please let us know if you have any questions.\n\nThanks,\nPotelco", 
               "admin", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), 1))

    c.execute('''CREATE TABLE IF NOT EXISTS automation_rules
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  template_id INTEGER NOT NULL,
                  trigger_type TEXT NOT NULL,
                  trigger_value TEXT NOT NULL,
                  recipient_type TEXT NOT NULL,
                  recipient_value TEXT,
                  created_by TEXT NOT NULL,
                  timestamp TEXT NOT NULL,
                  FOREIGN KEY (template_id) REFERENCES email_templates(id))''')

    try:
        c.execute("ALTER TABLE automation_rules ADD COLUMN active INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    c.execute("INSERT OR IGNORE INTO automation_rules (template_id, trigger_type, trigger_value, recipient_type, recipient_value, created_by, timestamp, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (1, "days_before", "2", "location_city", None, "admin", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), 1))

    c.execute('''CREATE TABLE IF NOT EXISTS towns
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL UNIQUE,
                  email TEXT NOT NULL,
                  phone TEXT,
                  address TEXT,
                  timestamp TEXT NOT NULL)''')
    initial_towns = [
        ("Site A", "sitea.town@example.com", "555-1234", "123 Main St, Site A"),
        ("Site B", "siteb.town@example.com", "555-5678", "456 Oak Ave, Site B"),
        ("TBD", "default.town@example.com", "555-0000", "Unknown")
    ]
    for name, email, phone, address in initial_towns:
        c.execute("INSERT OR IGNORE INTO towns (name, email, phone, address, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (name, email, phone, address, datetime.now().strftime("%Y-%m-%dT%H:%M:%S")))

    c.execute('''CREATE TABLE IF NOT EXISTS email_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  template_id INTEGER,
                  job_id INTEGER,
                  recipient TEXT NOT NULL,
                  subject TEXT NOT NULL,
                  sent_timestamp TEXT NOT NULL,
                  status TEXT NOT NULL,
                  FOREIGN KEY (template_id) REFERENCES email_templates(id))''')

    # Commit and close
    conn.commit()
    conn.close()

    # Upgrade user table
    upgrade_user_table_for_enterprise()

# Run init_db only if this script is executed directly
if __name__ == "__main__":
    init_db()

# User class and static data
users = {
    'admin': {'password': 'potelco123', 'role': 'admin'},
    'employee': {'password': 'emp2025', 'role': 'employee'}
}

class User(UserMixin):
    def __init__(self, identifier, by_username=False):
        conn = sqlite3.connect(SCHEDULE_DB)
        c = conn.cursor()
        if by_username:
            c.execute("SELECT id, username, role FROM users WHERE username = ?", (identifier,))
        else:
            c.execute("SELECT id, username, role FROM users WHERE id = ?", (identifier,))
        user = c.fetchone()
        conn.close()
        if user:
            self.id = str(user[0])  # Flask-Login requires id to be a string
            self.username = user[1]
            self.role = user[2]
        else:
            raise ValueError(f"User with {'username' if by_username else 'id'} {identifier} not found")

    def is_admin(self):
        return self.role == 'admin'

def upgrade_user_table_for_enterprise():
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("PRAGMA table_info(users)")
    existing_columns = [col[1] for col in c.fetchall()]

    if "full_name" not in existing_columns:
        c.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
    if "job_title" not in existing_columns:
        c.execute("ALTER TABLE users ADD COLUMN job_title TEXT")
    if "role" not in existing_columns:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    if "certifications" not in existing_columns:
        c.execute("ALTER TABLE users ADD COLUMN certifications TEXT DEFAULT '[]'")

    conn.commit()
    conn.close()

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)