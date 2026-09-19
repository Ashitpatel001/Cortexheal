
with open("cortexheal/recovery/engine.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "pattern = self.pattern_engine.get_or_create_pattern(incident, trigger_event)",
    "pattern = self.pattern_engine.get_or_create_pattern(incident, trigger_event, run.org_id)"
)

with open("cortexheal/recovery/engine.py", "w", encoding="utf-8") as f:
    f.write(content)

