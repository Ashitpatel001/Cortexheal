
from cortexheal.storage.postgres import get_audit_events_for_run
import sys

run_id = "17edc7cb-c392-45a4-abc3-bd839eb58c71"
audits = get_audit_events_for_run(run_id)
for a in audits:
    print(f"[{a.timestamp}] {a.action} ({a.result}): {a.reason}")

