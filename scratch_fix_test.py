
import re

with open("test_unrecoverable.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the API resume with local resume
content = re.sub(
    r"req4 = urllib\.request.*?urllib\.request\.urlopen\(req4\)",
    "from cortexheal.protection.controller import ProtectionController\n        ProtectionController().resume(run_id, \"dev-operator\", \"Manual Resume\", incident_id)",
    content,
    flags=re.DOTALL
)

with open("test_unrecoverable.py", "w", encoding="utf-8") as f:
    f.write(content)

