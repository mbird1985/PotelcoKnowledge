from flask import Blueprint, render_template
from flask_login import login_required
import sqlite3
from config import SCHEDULE_DB

towns_bp = Blueprint("towns", __name__)

@towns_bp.route("/towns")
@login_required
def towns():
    conn = sqlite3.connect(SCHEDULE_DB)
    c = conn.cursor()
    c.execute("SELECT DISTINCT location FROM schedules ORDER BY location")
    towns = c.fetchall()
    conn.close()
    return render_template("towns.html", towns=towns)
