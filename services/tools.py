from services.report_service import generate_pdf_report
from services.inventory_service import get_inventory_summary
from services.schedule_service import schedule_equipment_by_name, get_schedule_summary  # Add this
from services.equipment_service import get_equipment_status
from services.logging_service import log_audit  # Add this
import os
from werkzeug.utils import secure_filename  # Add this for safe filenames

TOOLS = {}

def register_tool(name):
    def wrapper(func):
        TOOLS[name] = func
        return func
    return wrapper

@register_tool("generate_report")
def handle_generate_report(params):
    title = params.get("title", "AI Report")
    data = params.get("data", [])
    report_type = params.get("format", "pdf")

    safe_title = secure_filename(title.replace(' ', '_'))
    filename = f"static/reports/{safe_title}.{report_type}"
    os.makedirs("static/reports", exist_ok=True)

    if report_type == "pdf":
        generate_pdf_report(filename, title, data)
        log_audit(None, "generate_report", {"title": title, "filename": filename})
        return {
            "message": f"Report '{title}' generated.",
            "download_url": f"/{filename}"
        }
    else:
        return {"message": "Only PDF reports are supported right now."}

@register_tool("get_inventory_summary")
def handle_inventory_summary(_params):
    summary = get_inventory_summary()
    return {"message": "Inventory Summary:\n" + "\n".join(summary)}

@register_tool("schedule_equipment")
def handle_schedule_equipment(params):
    equipment = params.get("equipment")
    start = params.get("start")
    end = params.get("end")
    job = params.get("job", f"Scheduled via assistant for {equipment}")

    if not (equipment and start and end):
        return {"message": "Missing required fields: equipment, start, end."}

    message = schedule_equipment_by_name(equipment, start, end, job)
    log_audit(None, "schedule_equipment", {"equipment": equipment, "start": start, "end": end})
    return {"message": message}

@register_tool("get_schedule_summary")
def handle_schedule_summary(params):
    days = params.get("days", 1)
    try:
        days = int(days)
    except ValueError:
        days = 1

    summary = get_schedule_summary(days_ahead=days)
    return {"message": "Upcoming Schedule:\n" + "\n".join(summary)}

@register_tool("get_equipment_status")
def handle_equipment_status(params):
    keyword = params.get("filter")
    status_list = get_equipment_status(keyword)
    return {"message": "Equipment Status:\n" + "\n".join(status_list)}

def route_action(action_name, params):
    handler = TOOLS.get(action_name)
    if handler:
        return handler(params)
    return {"message": f"No handler found for action '{action_name}'"}