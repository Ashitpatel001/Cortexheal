with open('tests/e2e/test_e2e.py', 'r') as f:
    text = f.read()

# Revert debug prints
text = text.replace('    print(\"\\nRUNS:\", mock_db[\"runs\"])\n    print(\"\\nINCIDENTS:\", mock_db[\"incidents\"])\n', '')

clean_db_pattern = '''def clean_db():
    from cortexheal.storage.postgres import init_db, get_connection
    init_db()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE audit_events, recovery_plans, notification_records, webhook_configs, incidents, events, runs, api_keys CASCADE")
            conn.commit()
    from cortexheal.runtime.collector import collector
    collector.engine._emitted.clear()
    
    yield
    
    collector._queue.join()'''

lines = text.split('\n')
new_lines = []
in_mock_db = False
for line in lines:
    if line.startswith('def mock_db():'):
        in_mock_db = True
        new_lines.extend(clean_db_pattern.split('\n'))
        continue
    if in_mock_db:
        if line.startswith('def test_full_lifecycle_e2e(mock_db):'):
            in_mock_db = False
            new_lines.append(line.replace('mock_db', 'clean_db'))
        else:
            continue
    elif line.startswith('def test_full_lifecycle_unrecoverable_loop_e2e(mock_db):'):
        new_lines.append(line.replace('mock_db', 'clean_db'))
    else:
        # replace mock_db with postgres queries in the test body
        if 'mock_db["runs"].get(run_id)' in line:
            new_lines.append(line.replace('mock_db["runs"].get(run_id)', 'get_run(run_id)'))
        elif 'mock_db["plans"].get(incident_id)' in line:
            new_lines.append(line.replace('mock_db["plans"].get(incident_id)', 'get_recovery_plan_by_incident(incident_id)'))
        elif 'mock_db["audits"]' in line:
            new_lines.append(line.replace('mock_db["audits"]', 'get_audit_events_for_run(run_id)'))
        else:
            new_lines.append(line)

with open('tests/e2e/test_e2e.py', 'w') as f:
    f.write('\n'.join(new_lines))

with open('tests/e2e/test_e2e.py', 'r') as f:
    text2 = f.read()
    if 'get_run(run_id)' in text2 and 'from cortexheal.storage.postgres import get_run' not in text2:
        text2 = text2.replace('import pytest', 'import pytest\nfrom cortexheal.storage.postgres import get_run, get_recovery_plan_by_incident, get_audit_events_for_run')
        with open('tests/e2e/test_e2e.py', 'w') as f:
            f.write(text2)
