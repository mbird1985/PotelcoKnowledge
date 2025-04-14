from elasticsearch import Elasticsearch
from config import ES_HOST, ES_USER, ES_PASS
import os

# Optional: load from .env/config.py
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_USER = os.getenv("ES_USER", "elastic")
ES_PASS = os.getenv("ES_PASS", "changeme")  # Replace in .env or override in production

# Create a single, shared ES client
es = Elasticsearch(
    ES_HOST,
    basic_auth=(ES_USER, ES_PASS),
    timeout=30,
    max_retries=3,
    retry_on_timeout=True
)

# Optional: Test connection on import
try:
    if not es.ping():
        print("[Elastic] ❌ Could not connect to Elasticsearch.")
    else:
        print("[Elastic] ✅ Connected to Elasticsearch.")
except Exception as e:
    print(f"[Elastic] ❌ Elasticsearch error: {e}")
