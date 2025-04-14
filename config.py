import os
from dotenv import load_dotenv
load_dotenv()

# Flask App Config
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")

# External Services
ES_URL = os.getenv("ES_URL")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# Database
SCHEDULE_DB = os.getenv("SCHEDULE_DB", "schedule.db")

if not SMTP_USER or not SMTP_PASS:
    raise RuntimeError("SMTP credentials not set in .env file.")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTHORITY = "https://login.microsoftonline.com/common"
REDIRECT_PATH = "http://localhost:5000/outlook_callback"
SCOPES = ["Calendars.Read"]
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
NOTIFICATION_RECIPIENTS = ["recipient1@example.com", "recipient2@example.com"]
OUTLOOK_CLIENT_ID = "your-client-id"
OUTLOOK_CLIENT_SECRET = "your-client-secret"
OUTLOOK_AUTHORITY = "https://login.microsoftonline.com/common"
OUTLOOK_REDIRECT_URI = "http://localhost:5000/outlook_callback"
OUTLOOK_SCOPES = ["https://graph.microsoft.com/Mail.Send", "https://graph.microsoft.com/User.Read"]
ES_HOST = os.getenv("ES_HOST")
ES_USER = os.getenv("ES_USER")
ES_PASS = os.getenv("ES_PASS")
DOCUMENT_FOLDER = os.getenv("DOCUMENT_FOLDER", "uploads")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")



