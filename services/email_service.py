import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from config import SCHEDULE_DB, SMTP_USER, SMTP_PASS, SMTP_SERVER, SMTP_PORT
from services.elasticsearch_client import es
import requests
from services.logging_service import log_audit  # Add this

def get_email_templates():
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT * FROM email_templates")
    templates = c.fetchall()
    conn.close()
    return templates

def get_automation_rules(template_id=None):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    if template_id:
        c.execute("SELECT * FROM automation_rules WHERE template_id = ?", (template_id,))
    else:
        c.execute("SELECT * FROM automation_rules")
    rules = c.fetchall()
    conn.close()
    return rules

def get_template_by_id(template_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT * FROM email_templates WHERE id = ?", (template_id,))
    template = c.fetchone()
    conn.close()
    return template

def get_rule_by_id(rule_id):
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,))
    rule = c.fetchone()
    conn.close()
    return rule

def get_template_preview(template_id, sample_data=None):
    template = get_template_by_id(template_id)
    if not template:
        return None
    _, name, subject, body, cc, bcc, *_rest, is_html = template
    if sample_data is None:
        sample_data = {
            "location": "Example Town", "start_date": "2025-04-01", "end_date": "2025-04-01",
            "start_time": "08:00", "end_time": "17:00", "description": "Example job",
            "job_number": "J0001", "job_name": "Sample Job", "resource_name": "BT001"
        }
    return {
        "subject": subject.format(**sample_data),
        "body": body.format(**sample_data),
        "cc": cc,
        "bcc": bcc,
        "is_html": bool(is_html)
    }

def send_notification(subject, body, recipients, cc=None, bcc=None, is_html=False):
    msg = MIMEText(body, "html" if is_html else "plain")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(recipients)
    if cc:
        msg["Cc"] = ", ".join(cc)
    all_recipients = recipients + (cc if cc else []) + (bcc if bcc else [])
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, all_recipients, msg.as_string())
        print(f"[Email] Notification sent to: {all_recipients}")
        log_audit("send_notification", "system", details={"subject": subject, "recipients": all_recipients})
    except Exception as e:
        print(f"[Email] Failed to send notification: {e}")
        log_audit("send_notification_failed", "system", details={"subject": subject, "recipients": all_recipients, "error": str(e)})
    return True

def send_outlook_email(user_id, subject, body, to_list, cc_list=None, bcc_list=None):
    # Note: Access token should come from integration_service; this is a placeholder
    from services.integration_service import get_token_from_code  # Add this
    # Assume token is stored in session or fetched; this needs integration
    url = "https://graph.microsoft.com/v1.0/me/sendMail"
    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body},
            "toRecipients": [{"emailAddress": {"address": addr}} for addr in to_list],
            "ccRecipients": [{"emailAddress": {"address": addr}} for addr in cc_list or []],
            "bccRecipients": [{"emailAddress": {"address": addr}} for addr in bcc_list or []],
        }
    }
    # Placeholder: Replace with actual token retrieval logic
    headers = {"Authorization": "Bearer REPLACE_WITH_TOKEN", "Content-Type": "application/json"}
    response = requests.post(url, json=message, headers=headers)
    if response.status_code == 202:
        print(f"[Outlook] Email sent via Microsoft Graph API.")
        log_audit(user_id, "send_outlook_email", {"subject": subject, "to": to_list})
    else:
        print(f"[Outlook] Email failed: {response.status_code}, {response.text}")
