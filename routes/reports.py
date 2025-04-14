from flask import Blueprint, request, send_file, flash, render_template
from flask_login import login_required
from services.report_service import generate_pdf_report, generate_csv_report, parse_report_data, generate_filtered_report
import os

report_bp = Blueprint("report", __name__, url_prefix="/reports")

@report_bp.route("/reports")
@login_required
def reports():
    # TODO: Show available reports
    return render_template("reports.html", reports=[])

@report_bp.route("/", methods=["GET", "POST"])
@login_required
def generate_report():
    if request.method == "POST":
        report_type = request.form.get("report_type")
        title = request.form.get("title", "Untitled Report")
        data_raw = request.form.get("data")

        data = parse_report_data(data_raw)
        filename = f"static/reports/{title.replace(' ', '_')}.{report_type}"

        os.makedirs("static/reports", exist_ok=True)

        if report_type == "pdf":
            generate_pdf_report(filename, title, data)
        elif report_type == "csv":
            generate_csv_report(filename, data)
        else:
            flash("Invalid report type.")
            return render_template("report_form.html")

        flash("Report generated successfully.")
        return send_file(filename, as_attachment=True)

    return render_template("report_form.html")

def report_dashboard():
    report_type = request.args.get("type", "summary")
    date_range = request.args.get("range", "30d")

    report_data = generate_filtered_report(report_type, date_range)
    return render_template("reports.html", report_data=report_data, type=report_type, range=date_range)