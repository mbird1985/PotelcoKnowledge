# services/job_utils.py
from services.db import get_connection

def needs_rerouting(job):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT wind_speed, precipitation FROM weather WHERE date = ? AND location = ?", (job[3], job[10] or "Site A"))
    weather = c.fetchone()
    conn.close()
    if weather and (weather[0] > 15 or weather[1] > 5):  # Wind > 15 m/s or rain > 5mm
        return True
    return False