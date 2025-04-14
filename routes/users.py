from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from services.users_service import (
    get_all_users,
    get_user_by_id,
    add_user,
    update_user,
    delete_user,
    get_all_certifications,
    get_user_certifications,
)
import csv
import io
import json

users_bp = Blueprint("users", __name__, url_prefix="/users")


def admin_only():
    if not current_user.role == "admin":
        flash("Admin access only.")
        return False
    return True


@users_bp.route("/people")
@login_required
def people():
    if not admin_only():
        return redirect(url_for("system.dashboard"))

    role_filter = request.args.get("role")
    users = get_all_users(role_filter)

    for user in users:
        user["certifications_display"] = get_user_certifications(user["id"])

    return render_template("people.html", users=users, can_edit=True)


@users_bp.route("/profile/<int:user_id>")
@login_required
def profile(user_id):
    user = get_user_by_id(user_id)
    if not user:
        flash("User not found.")
        return redirect(url_for("users.people"))

    certs = get_user_certifications(user_id)
    return render_template("profile.html", user=user, user_certs=certs)


@users_bp.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    if not admin_only():
        return redirect(url_for("users.people"))

    user = get_user_by_id(user_id)
    if not user:
        flash("User not found.")
        return redirect(url_for("users.people"))

    if request.method == "POST":
        certs = request.form.getlist("certifications")
        update_user(
            user_id,
            username=request.form.get("username"),
            email=request.form.get("email"),
            role=request.form.get("role"),
            full_name=request.form.get("full_name"),
            job_title=request.form.get("job_title"),
            certifications=certs
        )
        flash("User updated.")
        return redirect(url_for("users.people"))

    all_certs = get_all_certifications()
    user_certs = get_user_certifications(user_id)
    return render_template("edit_user.html", user=user, all_certs=all_certs, user_certs=user_certs)


@users_bp.route("/add_user", methods=["GET", "POST"])
@login_required
def add_user_route():
    if not admin_only():
        return redirect(url_for("users.people"))

    if request.method == "POST":
        certs = request.form.getlist("certifications")
        add_user(
            username=request.form.get("username"),
            email=request.form.get("email"),
            password=request.form.get("password"),
            role=request.form.get("role"),
            full_name=request.form.get("full_name"),
            job_title=request.form.get("job_title"),
            certifications=certs
        )
        flash("User added.")
        return redirect(url_for("users.people"))

    all_certs = get_all_certifications()
    return render_template("add_user.html", all_certs=all_certs)


@users_bp.route("/delete_user/<int:user_id>", methods=["POST"])
@login_required
def delete_user_route(user_id):
    if not admin_only():
        return redirect(url_for("users.people"))

    delete_user(user_id)
    flash("User deleted.")
    return redirect(url_for("users.people"))


@users_bp.route("/export", methods=["GET"])
@login_required
def export_users_csv():
    if not admin_only():
        return redirect(url_for("users.people"))

    users = get_all_users()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Username", "Email", "Full Name", "Job Title", "Role", "Certifications"])

    for user in users:
        certs = get_user_certifications(user["id"])
        writer.writerow([
            user["username"],
            user["email"],
            user.get("full_name", ""),
            user.get("job_title", ""),
            user["role"],
            ", ".join(certs)
        ])

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=users_export.csv"}
    )
