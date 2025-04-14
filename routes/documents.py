from flask import Blueprint, request, redirect, url_for, render_template, flash, send_from_directory, abort
from flask_login import login_required, current_user
from services.document_service import (
    save_uploaded_document, get_all_documents, get_document_by_id,
    update_document, delete_document, get_document_versions, allowed_file, index_document
)
from werkzeug.utils import secure_filename
from config import DOCUMENT_FOLDER, UPLOAD_FOLDER
import os

document_bp = Blueprint("documents", __name__, url_prefix="/documents")

@document_bp.route("/")
@login_required
def document_list():
    documents = get_all_documents()
    return render_template("documents.html", documents=documents)

@document_bp.route('/upload', methods=['POST'])
@login_required
def upload_document():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        save_uploaded_document(file, user_id=current_user.id)  # Save to SQLite
        index_document(file_path, filename, current_user.id)   # Index in Elasticsearch
        flash('Document uploaded and indexed successfully.')
        return redirect(url_for('documents.document_list'))  # Fix redirect to correct endpoint
    else:
        flash('Invalid file type.')
        return redirect(url_for('documents.document_list'))  # Consistent redirect

@document_bp.route("/uploads/<filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory("uploads", filename)

@document_bp.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_document(id):
    document = get_document_by_id(id)
    if not document:
        flash("Document not found.")
        return redirect(url_for("documents.document_list"))
    if request.method == "POST":
        new_title = request.form.get("title")
        update_document(id, new_title, current_user.id)
        flash("Document updated.")
        return redirect(url_for("documents.document_list"))
    return render_template("edit_document.html", document=document)

@document_bp.route("/delete/<int:id>")
@login_required
def delete_document_route(id):
    delete_document(id)
    flash("Document deleted.")
    return redirect(url_for("documents.document_list"))

@document_bp.route("/versions/<title>")
@login_required
def document_versions(title):
    versions = get_document_versions(title)
    return render_template("versions.html", versions=versions, title=title)

@document_bp.route("/view/<filename>")
@login_required
def view_document(filename):
    # Sanitize file path
    safe_path = os.path.join(DOCUMENT_FOLDER, filename)
    if not os.path.exists(safe_path):
        flash("Document not found.")
        return redirect(url_for("documents.document_list"))

    # Display inline in browser
    return send_from_directory(DOCUMENT_FOLDER, filename, as_attachment=False)

