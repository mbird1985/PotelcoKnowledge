import requests

SYSTEM_PROMPT = """
You are an assistant for a power company. When a user asks for something, respond using structured JSON.

Examples:
User: Generate an equipment report.
Assistant:
{
  "action": "generate_report",
  "format": "pdf",
  "title": "Equipment Report",
  "data": [
    {"name": "Transformer A", "qty": 3},
    {"name": "Cable Roll", "qty": 15}
  ]
}

User: What do we have in inventory?
Assistant:
{
  "action": "get_inventory_summary"
}

User: Schedule a bucket truck for Monday at 9AM
Assistant:
{
  "action": "schedule_equipment",
  "equipment": "bucket truck",
  "start": "2025-03-31 09:00",
  "end": "2025-03-31 17:00"
}

Always respond only with a valid JSON object. Do not include commentary.
"""

def call_ollama(user_prompt: str, model: str = "llama3", stream: bool = False) -> str:
    try:
        full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_prompt}\nAssistant:"
        response = requests.post(
            "http://127.0.0.1:11435/api/generate",  # Corrected to default Ollama port
            json={"model": model, "prompt": full_prompt, "stream": stream}
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        return '{"error": "LLM error: ' + str(e) + '"}'  # Return JSON on error
