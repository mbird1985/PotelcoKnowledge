from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, flash, Response
from flask_login import LoginManager, login_required, current_user
from search import search
import os
from werkzeug.utils import secure_filename
from elasticsearch import Elasticsearch
from io import BytesIO, StringIO
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
import csv
import requests
import re
import sqlite3
import json
from apscheduler.schedulers.background import BackgroundScheduler
from msal import ConfidentialClientApplication
from routes.chat import chat_bp
from routes.equipment import equipment_bp
from routes.inventory import inventory_bp
from routes.schedule import schedule_bp
from routes.auth import auth_bp
from routes.documents import document_bp
from routes.reports import report_bp
from routes.system import system_bp
from routes.users import users_bp
from routes.towns import towns_bp
from routes.email import email_bp
from routes.integrations import integration_bp
from config import SECRET_KEY, SCHEDULE_DB, SMTP_USER, SMTP_PASS, UPLOAD_FOLDER, WEATHER_API_KEY
from services.init_db import init_db
from services.logging_service import log_analytics, log_audit
from services.schedule_service import check_availability
from services.equipment_service import check_all_equipment_maintenance
from services.document_service import extract_text, allowed_file
from services.email_service import send_notification, send_outlook_email
from services.automation_service import update_weather, reroute_jobs, check_equipment_health, send_automated_emails
from services.elasticsearch_client import es
from services.db import get_connection
from services.auth_service import User
from services.job_utils import needs_rerouting

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

init_db()

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"  # Use auth blueprint's login
app.config['TEMPLATES_AUTO_RELOAD'] = True
# Register routes
app.register_blueprint(chat_bp)
app.register_blueprint(equipment_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(schedule_bp)
app.register_blueprint(document_bp)
app.register_blueprint(report_bp)
app.register_blueprint(system_bp)
app.register_blueprint(email_bp)
app.register_blueprint(integration_bp)
app.register_blueprint(users_bp)
app.register_blueprint(towns_bp)
app.register_blueprint(auth_bp)

app.config["SECRET_KEY"] = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@login_manager.user_loader
def load_user(user_id):
    try:
        return User(user_id)
    except ValueError:
        return None

@app.route("/")
@login_required
def home():
    return redirect(url_for('system.dashboard'))

@app.route("/search_page")
@login_required
def serve_search():
    return render_template('search.html')

@app.route("/upload_page")
@login_required
def serve_upload():
    return render_template('upload.html')

@app.route("/search")
def api_search():
    query = request.args.get("q", "")
    category = request.args.get("category", None)
    job_site = request.args.get("job_site", None)
    people = request.args.get("people", None)
    date_from = request.args.get("date_from", None)
    date_to = request.args.get("date_to", None)
    tags = request.args.get("tags", None)
    version = request.args.get("version", None)
    source = request.args.get("source", None)
    results = search(query, category, job_site, people, date_from, date_to, tags, version, source)
    log_analytics("search", {"query": query, "category": category, "job_site": job_site, "people": people, "date_from": date_from, "date_to": date_to, "tags": tags, "version": version, "source": source, "results_count": len(results)})
    return jsonify([{
        "title": hit["_source"]["title"],
        "score": hit["_score"],
        "content": hit["_source"]["content"][:200],
        "url": hit["_source"]["metadata"]["url"] if "metadata" in hit["_source"] else "",
        "highlight": hit.get("highlight", {}),
        "id": hit["_id"]
    } for hit in results])

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('static', 'sw.js')

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json')

scheduler = BackgroundScheduler()
scheduler.add_job(send_automated_emails, 'interval', days=1, next_run_time=datetime.now())
scheduler.add_job(reroute_jobs, 'interval', hours=1)
scheduler.add_job(update_weather, 'interval', hours=3)
scheduler.add_job(check_equipment_health, 'interval', days=1)
scheduler.start()
scheduler.add_job(check_all_equipment_maintenance, 'interval', days=1)

if __name__ == "__main__":
    app.run(port=5000)