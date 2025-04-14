from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from services.equipment_service import get_equipment_detail, get_all_equipment, get_equipment_by_id, update_equipment, delete_equipment, add_equipment
from services.users_service import get_all_certifications

equipment_bp = Blueprint("equipment", __name__)

@equipment_bp.route("/equipment")
@login_required
def equipment():
    return redirect(url_for("equipment.equipment_list"))

@equipment_bp.route("/list")
@login_required
def equipment_list():
    equipment = get_all_equipment()
    return render_template("equipment.html", equipment=equipment)

@equipment_bp.route('/equipment_detail/<int:equipment_id>', methods=['GET'])
@login_required
def equipment_detail(equipment_id):
    equipment = get_equipment_detail(equipment_id)
    if not equipment:
        flash('Equipment not found.')
        return redirect(url_for('equipment.equipment_list'))
    return render_template('equipment_detail.html', equipment=equipment, can_edit=current_user.role in ['manager', 'admin'])

@equipment_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_equipment_route():
    if request.method == "POST":
        add_equipment(request.form)
        flash("Equipment added.")
        return redirect(url_for("equipment.equipment_list"))

    certs = get_all_certifications()
    return render_template("add_equipment.html", all_certs=certs)

@equipment_bp.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_equipment(id):
    equipment = get_equipment_by_id(id)
    if not equipment:
        flash("Equipment not found.")
        return redirect(url_for("equipment.equipment_list"))

    if request.method == "POST":
        update_equipment(id, request.form)
        flash("Equipment updated.")
        return redirect(url_for("equipment.equipment_list"))

    certs = get_all_certifications()
    return render_template("edit_equipment.html", equipment=equipment, all_certs=certs)

@equipment_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete_equipment_route(id):
    delete_equipment(id)
    flash("Equipment deleted.")
    return redirect(url_for("equipment.equipment_list"))