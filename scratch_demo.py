
with open("examples/demo_stuck_loop_with_recovery.py", "r", encoding="utf-8") as f:
    content = f.read()

import re

old_code = """    update_run_status(run_id, "completed")"""
new_code = """    collector.ingest_event(RuntimeEvent(
        run_id=run_id,
        agent_id=agent_id,
        framework="langgraph",
        event_type="RUN_COMPLETED",
        sequence_number=10,
        idempotency_key=f"{run_id}_completed",
        status="success"
    ))
    collector._queue.join()
    time.sleep(0.5)"""

content = content.replace(old_code, new_code)

with open("examples/demo_stuck_loop_with_recovery.py", "w", encoding="utf-8") as f:
    f.write(content)

