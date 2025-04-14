from flask import Blueprint, redirect, request, render_template, session, url_for, flash
from flask_login import login_required
from config import CLIENT_ID, CLIENT_SECRET, AUTHORITY, REDIRECT_PATH, SCOPES
from msal import ConfidentialClientApplication
import requests

integration_bp = Blueprint("integration", __name__)

@integration_bp.route("/outlook_auth")
@login_required
def outlook_auth():
    session["state"] = "secure_state"
    auth_app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )
    auth_url = auth_app.get_authorization_request_url(
        scopes=SCOPES,
        state=session["state"],
        redirect_uri=REDIRECT_PATH
    )
    return redirect(auth_url)

@integration_bp.route("/outlook_callback")
@login_required
def outlook_callback():
    if request.args.get("state") != session.get("state"):
        return redirect(url_for("dashboard"))

    code = request.args.get("code")
    auth_app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )
    token = auth_app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_PATH
    )

    if "access_token" in token:
        session["access_token"] = token["access_token"]
        flash("Outlook integration successful!")
    else:
        flash("Failed to authenticate with Microsoft.")

    return redirect(url_for("dashboard"))

@integration_bp.route("/integrate")
@login_required
def integrate():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("integration.outlook_auth"))

    headers = {"Authorization": f"Bearer {access_token}"}
    graph_url = "https://graph.microsoft.com/v1.0/me/events"
    response = requests.get(graph_url, headers=headers)

    if response.status_code == 200:
        events = response.json().get("value", [])
        return render_template("outlook_events.html", events=events)
    else:
        flash("Failed to fetch events.")
        return redirect(url_for("dashboard"))
