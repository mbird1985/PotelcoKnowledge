from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
import sqlite3
from config import SCHEDULE_DB

email_bp = Blueprint("email", __name__)

@email_bp.route("/email_templates", methods=["GET", "POST"])
@login_required
def email_templates():
    if not current_user.is_admin():
        flash('Admin access required.')
        return redirect(url_for('serve_search'))

    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()

    if request.method == 'POST':
        form = request.form

        if 'add_template' in form:
            c.execute("""
                INSERT INTO email_templates (name, subject, body, cc, bcc, created_by, timestamp, outlook_enabled, is_html)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                form.get('name'), form.get('subject'), form.get('body'),
                form.get('cc'), form.get('bcc'), current_user.id,
                datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                1 if form.get('outlook_enabled') == 'on' else 0,
                1 if form.get('is_html') == 'on' else 0
            ))
            flash(f"Template '{form.get('name')}' added.")

        elif 'update_template' in form:
            c.execute("""
                UPDATE email_templates
                SET name=?, subject=?, body=?, cc=?, bcc=?, timestamp=?, outlook_enabled=?, is_html=?
                WHERE id=?
            """, (
                form.get('name'), form.get('subject'), form.get('body'),
                form.get('cc'), form.get('bcc'),
                datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                1 if form.get('outlook_enabled') == 'on' else 0,
                1 if form.get('is_html') == 'on' else 0,
                form.get('template_id')
            ))
            flash(f"Template '{form.get('name')}' updated.")

        elif 'delete_template' in form:
            c.execute("SELECT name FROM email_templates WHERE id = ?", (form.get('template_id'),))
            template_name = c.fetchone()[0]
            c.execute("DELETE FROM email_templates WHERE id = ?", (form.get('template_id'),))
            c.execute("DELETE FROM automation_rules WHERE template_id = ?", (form.get('template_id'),))
            flash(f"Template '{template_name}' deleted.")

        elif 'add_rule' in form:
            c.execute("""
                INSERT INTO automation_rules
                (template_id, trigger_type, trigger_value, recipient_type, recipient_value, created_by, timestamp, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                form.get('template_id'), form.get('trigger_type'), form.get('trigger_value'),
                form.get('recipient_type'), form.get('recipient_value') or None,
                current_user.id,
                datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                1 if form.get('active') == 'on' else 0
            ))
            flash("Automation rule added.")

        elif 'update_rule' in form:
            c.execute("""
                UPDATE automation_rules
                SET template_id=?, trigger_type=?, trigger_value=?, recipient_type=?, recipient_value=?, timestamp=?, active=?
                WHERE id=?
            """, (
                form.get('template_id'), form.get('trigger_type'), form.get('trigger_value'),
                form.get('recipient_type'), form.get('recipient_value') or None,
                datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                1 if form.get('active') == 'on' else 0,
                form.get('rule_id')
            ))
            flash("Automation rule updated.")

        elif 'delete_rule' in form:
            c.execute("DELETE FROM automation_rules WHERE id = ?", (form.get('rule_id'),))
            flash("Automation rule deleted.")

        elif 'preview_template' in form:
            c.execute("SELECT subject, body, cc, bcc, is_html FROM email_templates WHERE id = ?", (form.get('template_id'),))
            template = c.fetchone()
            if template:
                subject, body, cc, bcc, is_html = template
                dummy_data = {
                    "location": "Sample Town",
                    "start_date": "2025-04-01",
                    "end_date": "2025-04-02",
                    "start_time": "08:00",
                    "end_time": "17:00",
                    "description": "Sample maintenance work",
                    "job_number": "J12345",
                    "job_name": "Sample Job",
                    "resource_name": "Sample Truck"
                }
                preview = {
                    "subject": subject.format(**dummy_data),
                    "body": body.format(**dummy_data),
                    "cc": cc,
                    "bcc": bcc,
                    "is_html": is_html
                }
        conn.commit()

    # Load templates and rules
    c.execute("SELECT * FROM email_templates")
    templates = c.fetchall()
    c.execute("SELECT * FROM automation_rules")
    rules = c.fetchall()
    conn.close()

    edit_template_id = request.args.get('edit_template_id')
    edit_rule_id = request.args.get('edit_rule_id')

    edit_template = None
    if edit_template_id:
        conn = sqlite3.connect(SCHEDULE_DB)
        c = conn.cursor()
        c.execute("SELECT * FROM email_templates WHERE id = ?", (edit_template_id,))
        edit_template = c.fetchone()
        conn.close()

    edit_rule = None
    if edit_rule_id:
        conn = sqlite3.connect(SCHEDULE_DB)
        c = conn.cursor()
        c.execute("SELECT * FROM automation_rules WHERE id = ?", (edit_rule_id,))
        edit_rule = c.fetchone()
        conn.close()

    return render_template("email_templates.html",
                           templates=templates,
                           rules=rules,
                           edit_template=edit_template,
                           edit_rule=edit_rule)
