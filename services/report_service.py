# In services/report_service.py
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
import csv
import json
from services.logging_service import log_audit  # Ensure this is imported

def generate_pdf_report(filepath, title, data):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    elements = [Paragraph(title, styles['Title']), Spacer(1, 12)]
    if data:
        keys = list(data[0].keys())
        table_data = [keys] + [list(d.values()) for d in data]
        table = Table(table_data)
        elements.append(table)
    doc.build(elements)
    log_audit(None, "generate_pdf_report", {"filepath": filepath, "title": title})

def generate_csv_report(filepath, data):
    if not data:
        return
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    log_audit(None, "generate_csv_report", {"filepath": filepath})

def parse_report_data(data_raw):
    try:
        return json.loads(data_raw)
    except json.JSONDecodeError:
        return []

def generate_filtered_report(filepath, title, data, filter_key, filter_value):
    """Generate a PDF report with filtered data."""
    filtered_data = [item for item in data if item.get(filter_key) == filter_value]
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    elements = [Paragraph(f"{title} (Filtered by {filter_key}={filter_value})", styles['Title']), Spacer(1, 12)]
    if filtered_data:
        keys = list(filtered_data[0].keys())
        table_data = [keys] + [list(d.values()) for d in filtered_data]
        table = Table(table_data)
        elements.append(table)
    else:
        elements.append(Paragraph("No data matches the filter.", styles['Normal']))
    doc.build(elements)
    log_audit(None, "generate_filtered_report", {"filepath": filepath, "title": title, "filter_key": filter_key})