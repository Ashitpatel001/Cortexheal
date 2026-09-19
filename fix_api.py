
with open("cortexheal/server/api.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "pattern = PatternEngine().get_or_create_pattern(incident, trigger_event)",
    "pattern = PatternEngine().get_or_create_pattern(incident, trigger_event, incident_run.org_id)"
)

# We need to fetch run to get org_id in api.py
content = content.replace(
    "from cortexheal.storage.postgres import get_events_for_run",
    "from cortexheal.storage.postgres import get_events_for_run, get_run"
)
content = content.replace(
    "events = get_events_for_run(incident.run_id)",
    "events = get_events_for_run(incident.run_id)\n            incident_run = get_run(incident.run_id)"
)

with open("cortexheal/server/api.py", "w", encoding="utf-8") as f:
    f.write(content)

