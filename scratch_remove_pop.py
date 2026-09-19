
with open("cortexheal/detection/engine.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
content = re.sub(r"RESUMED_RUNS\.pop\(event\.run_id, None\)", "pass", content)

with open("cortexheal/detection/engine.py", "w", encoding="utf-8") as f:
    f.write(content)

