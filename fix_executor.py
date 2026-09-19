
with open("cortexheal/recovery/executor.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "pattern = PatternEngine().get_or_create_pattern(incident, trigger_event)",
    "pattern = PatternEngine().get_or_create_pattern(incident, trigger_event, get_run(plan.run_id).org_id)"
)

with open("cortexheal/recovery/executor.py", "w", encoding="utf-8") as f:
    f.write(content)

