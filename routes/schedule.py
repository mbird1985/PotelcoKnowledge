# routes/schedule.py
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from services.schedule_service import get_schedule_event, get_all_schedules, add_schedule, update_schedule, delete_schedule
from services.equipment_service import get_all_equipment
from services.users_service import get_all_users
from services.db import get_connection
from config import SCHEDULE_DB
import sqlite3
from datetime import datetime, timedelta
import logging

logging.basicConfig(filename='schedule.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

schedule_bp = Blueprint("schedule", __name__, url_prefix="/schedule")

@schedule_bp.route("/")
@login_required
def index():
    try:
        schedules = get_all_schedules()
        events = [
            {
                "id": s["id"],
                "title": s["job"],
                "start": f"{s['start_date']}T{s['start_time']}:00",
                "end": f"{s['end_date']}T{s['end_time']}:00",
                "url": url_for('schedule.schedule_detail', event_id=s["id"]),
                "extendedProps": {
                    "location": s["location"] or "",
                    "user_id": s["user_id"],
                    "status": s["status"],
                    "job_number": s["job_number"] or "",
                    "description": s["description"] or ""
                }
            } for s in schedules
        ]
        equipment = get_all_equipment()
        return render_template(
            "schedule.html",
            events=events,
            equipment=equipment,
            can_edit=current_user.role in ['manager', 'admin']
        )
    except Exception as e:
        flash(f"Error loading schedule: {str(e)}")
        return redirect(url_for('home'))

@schedule_bp.route('/schedule_detail/<int:event_id>', methods=['GET'])
@login_required
def schedule_detail(event_id):
    try:
        event = get_schedule_event(event_id)
        if not event:
            flash('Event not found.')
            return redirect(url_for('home'))
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, resource_type, resource_id, quantity FROM job_resources WHERE schedule_id = ?", (event_id,))
        resources = [
            {
                "id": row[0],
                "resource_type": row[1],
                "resource_id": row[2],
                "quantity": row[3],
                "name": get_resource_name(row[1], row[2])
            } for row in c.fetchall()
        ]
        equipment = get_all_equipment()
        people = get_all_users()
        c.execute("SELECT id, name, quantity FROM consumables")
        consumables = [{"id": row[0], "name": row[1], "stock": row[2]} for row in c.fetchall()]
        conn.close()
        people = [{"id": p["id"], "name": p["username"], "job_title": p.get("job_title", "N/A")} for p in people]
        return render_template(
            'schedule_detail.html',
            event=event,
            resources=resources,
            equipment=equipment,
            people=people,
            consumables=consumables,
            can_edit=current_user.role in ['manager', 'admin']
        )
    except Exception as e:
        flash(f"Error loading schedule details: {str(e)}")
        return redirect(url_for('home'))

def get_resource_name(resource_type, resource_id):
    try:
        conn = get_connection()
        c = conn.cursor()
        if resource_type == "equipment":
            c.execute("SELECT unique_id FROM equipment_instances WHERE id = ?", (resource_id,))
        elif resource_type == "person":
            c.execute("SELECT username FROM users WHERE id = ?", (resource_id,))
        elif resource_type == "consumable":
            c.execute("SELECT name FROM consumables WHERE id = ?", (resource_id,))
        else:
            return "Unknown"
        result = c.fetchone()
        conn.close()
        return result[0] if result else "Unknown"
    except Exception:
        return "Unknown"

@schedule_bp.route("/add", methods=["POST"])
@login_required
def add_event():
    if current_user.role not in ['manager', 'admin']:
        flash("Permission denied")
        return redirect(url_for('schedule.index'))
    try:
        form = request.form
        required_fields = ["job_name", "start_time", "end_time", "equipment_id"]
        for field in required_fields:
            if field not in form:
                raise ValueError(f"Missing required field: {field}")
        job = form["job_name"]
        start = form["start_time"]
        end = form["end_time"]
        equipment_id = form["equipment_id"]
        operator_assigned = form.get("operator_assigned") == "on"
        start_date, start_time = start.split('T')
        end_date, end_time = end.split('T')
        # Validate date range
        start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
        if end_dt < start_dt:
            raise ValueError("End time cannot be before start time")
        if (end_dt - start_dt).days > 7:  # Limit to 7 days
            end_date = (start_dt + timedelta(days=7)).strftime("%Y-%m-%d")
            end_time = start_time
        # Check if equipment requires an operator
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT requires_operator FROM equipment_instances WHERE id = ?", (equipment_id,))
        result = c.fetchone()
        requires_operator = bool(result[0]) if result else False
        conn.close()
        user_id = current_user.id if operator_assigned and requires_operator else None
        logging.info(f"Adding job '{job}' with equipment_id={equipment_id}, user_id={user_id}, operator_assigned={operator_assigned}, requires_operator={requires_operator}, start={start}, end={end}")
        schedule_id = add_schedule(
            job=job,
            start_date=start_date,
            start_time=start_time,
            end_date=end_date,
            end_time=end_time,
            location=form.get("location", ""),
            user_id=user_id,
            equipment_id=equipment_id,
            current_user_id=current_user.id
        )
        flash("Job added successfully")
        return redirect(url_for('schedule.index'))
    except ValueError as e:
        flash(str(e))
        return redirect(url_for('schedule.index'))
    except Exception as e:
        flash(f"Error adding job: {str(e)}")
        return redirect(url_for('schedule.index'))

@schedule_bp.route("/events", methods=["GET"])
@login_required
def get_events():
    try:
        schedules = get_all_schedules()
        events = [
            {
                "id": s["id"],
                "title": s["job"],
                "start": f"{s['start_date']}T{s['start_time']}:00",
                "end": f"{s['end_date']}T{s['end_time']}:00",
                "url": url_for('schedule.schedule_detail', event_id=s["id"]),
                "extendedProps": {
                    "location": s["location"] or "",
                    "user_id": s["user_id"],
                    "status": s["status"],
                    "job_number": s["job_number"] or "",
                    "description": s["description"] or ""
                }
            } for s in schedules
        ]
        return jsonify(events)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch events: {str(e)}"}), 500

@schedule_bp.route("/update/<int:schedule_id>", methods=["PUT"])
@login_required
def update_event(schedule_id):
    if current_user.role not in ['manager', 'admin']:
        return jsonify({"error": "Permission denied"}), 403
    try:
        data = request.json
        required_fields = ["title", "start"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        start_dt = datetime.fromisoformat(data["start"].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(data["end"].replace('Z', '+00:00')) if data.get("end") else start_dt
        update_schedule(
            schedule_id=schedule_id,
            job=data["title"],
            start_date=start_dt.strftime("%Y-%m-%d"),
            start_time=start_dt.strftime("%H:%M"),
            end_date=end_dt.strftime("%Y-%m-%d"),
            end_time=end_dt.strftime("%H:%M"),
            location=data.get("location", ""),
            user_id=data.get("user_id", current_user.id),
            equipment_id=None,
            current_user_id=current_user.id
        )
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Update failed: {str(e)}"}), 500

@schedule_bp.route("/delete/<int:schedule_id>", methods=["DELETE"])
@login_required
def delete_event(schedule_id):
    if current_user.role not in ['manager', 'admin']:
        return jsonify({"error": "Permission denied"}), 403
    try:
        event = get_schedule_event(schedule_id)
        if not event:
            return jsonify({"error": "Schedule not found"}), 404
        delete_schedule(schedule_id, current_user.id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Deletion failed: {str(e)}"}), 500

@schedule_bp.route('/schedule_detail/<int:event_id>', methods=['POST'])
@login_required
def schedule_detail_post(event_id):
    if current_user.role not in ['manager', 'admin']:
        flash("Permission denied")
        return redirect(url_for('schedule.index'))
    try:
        conn = get_connection()
        c = conn.cursor()
        if "delete" in request.form:
            event = get_schedule_event(event_id)
            if not event:
                flash("Schedule not found")
                conn.close()
                return redirect(url_for('schedule.index'))
            delete_schedule(event_id, current_user.id)
            flash("Schedule deleted")
            conn.close()
            return redirect(url_for('schedule.index'))
        if "add_resource" in request.form:
            required_fields = ["resource_type", "resource_id"]
            form = request.form
            for field in required_fields:
                if field not in form:
                    raise ValueError(f"Missing required field: {field}")
            resource_type = form["resource_type"]
            resource_id = form["resource_id"]
            quantity = int(form.get("quantity", 1))
            if resource_type not in ["equipment", "person", "consumable"]:
                raise ValueError("Invalid resource type")
            if resource_type == "equipment":
                c.execute("SELECT 1 FROM equipment_instances WHERE id = ?", (resource_id,))
            elif resource_type == "person":
                c.execute("SELECT 1 FROM users WHERE id = ?", (resource_id,))
            elif resource_type == "consumable":
                c.execute("SELECT 1 FROM consumables WHERE id = ?", (resource_id,))
            if not c.fetchone():
                raise ValueError(f"Invalid {resource_type} ID")
            c.execute("INSERT INTO job_resources (schedule_id, resource_type, resource_id, quantity) VALUES (?, ?, ?, ?)",
                      (event_id, resource_type, resource_id, quantity))
            conn.commit()
            flash("Resource added")
        if "remove_resource" in request.form:
            if "resource_id" not in request.form:
                raise ValueError("Missing resource_id")
            resource_id = request.form["resource_id"]
            c.execute("SELECT 1 FROM job_resources WHERE id = ?", (resource_id,))
            if not c.fetchone():
                raise ValueError("Resource not found")
            c.execute("DELETE FROM job_resources WHERE id = ?", (resource_id,))
            conn.commit()
            flash("Resource removed")
        if not any([k in request.form for k in ["delete", "add_resource", "remove_resource"]]):
            required_fields = ["job", "start_date", "start_time", "end_date", "end_time", "location", "status"]
            form = request.form
            for field in required_fields:
                if field not in form:
                    raise ValueError(f"Missing required field: {field}")
            update_schedule(
                schedule_id=event_id,
                job=form["job"],
                start_date=form["start_date"],
                start_time=form["start_time"],
                end_date=form["end_date"],
                end_time=form["end_time"],
                location=form["location"],
                user_id=current_user.id,
                equipment_id=None,
                current_user_id=current_user.id
            )
            flash("Schedule updated")
        conn.close()
        return redirect(url_for('schedule.schedule_detail', event_id=event_id))
    except ValueError as e:
        conn.close()
        flash(str(e))
        return redirect(url_for('schedule.schedule_detail', event_id=event_id))
    except Exception as e:
        conn.close()
        flash(f"Error processing request: {str(e)}")
        return redirect(url_for('schedule.schedule_detail', event_id=event_id))