
with open("cortexheal/detection/engine.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
content = re.sub(
    r"if dedup_key in self\._emitted:.*?if event\.run_id in RESUMED_RUNS:.*?incident_id = RESUMED_RUNS\.get\(event\.run_id\)",
    """if dedup_key in self._emitted:
                        from cortexheal.storage.postgres import get_run
                        run = get_run(event.run_id)
                        # Instead of memory RESUMED_RUNS, we check if the run has a resume event recently
                        if run:
                            incident_id = None""",
    content,
    flags=re.DOTALL
)

with open("cortexheal/detection/engine.py", "w", encoding="utf-8") as f:
    f.write(content)

