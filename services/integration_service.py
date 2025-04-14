import requests
from msal import ConfidentialClientApplication
from config import CLIENT_ID, CLIENT_SECRET, AUTHORITY, SCOPES, REDIRECT_PATH
from flask import session  # Add this

def build_msal_app():
    return ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

def get_auth_url(session):
    session["state"] = "secure_state"
    app = build_msal_app()
    return app.get_authorization_request_url(
        scopes=SCOPES,
        state=session["state"],
        redirect_uri=REDIRECT_PATH
    )

def get_token_from_code(code):
    app = build_msal_app()
    try:
        result = app.acquire_token_by_authorization_code(
            code,
            scopes=SCOPES,
            redirect_uri=REDIRECT_PATH
        )
        return result
    except Exception as e:
        print(f"MSAL token error: {e}")
        return None

def fetch_calendar_events(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    graph_url = "https://graph.microsoft.com/v1.0/me/events"
    try:
        response = requests.get(graph_url, headers=headers)
        response.raise_for_status()
        return response.json().get("value", [])
    except requests.RequestException as e:
        print(f"Failed to fetch events: {e}")
        return []