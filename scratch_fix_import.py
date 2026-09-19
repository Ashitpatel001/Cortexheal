
with open("cortexheal/detection/engine.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
content = re.sub(
    r"ProtectionController\(\)\.request_pause",
    "from cortexheal.protection.controller import ProtectionController\n                                      ProtectionController().request_pause",
    content
)

with open("cortexheal/detection/engine.py", "w", encoding="utf-8") as f:
    f.write(content)

