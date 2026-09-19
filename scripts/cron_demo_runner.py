#!/usr/bin/env python3
"""
CortexHeal Live Demo Cron Engine
─────────────────────────────────
Infinite-loop background worker that drives the live public marketing demo.
Sequentially fires stuck-loop and budget-overrun scenarios so the
public-facing dashboard always has fresh, live data for visitors.

SAFETY GUARANTEES:
  • All demo data is scoped to DEMO_ORG_ID (env var, default "demo_public").
  • The demo runner never touches data belonging to any other org.
  • The marketing embed should authenticate with a VIEWER-only key
    scoped to this same org, ensuring read-only access.

SUPERVISION:
  This script is designed to run inside a container with `restart: always`.
  Do NOT run it as a raw `python` process on a bare-metal server without
  a process supervisor (systemd, docker-compose restart policy, etc.).
"""
import os
import time
import subprocess
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEMO_ORG_ID = os.environ.get("DEMO_ORG_ID", "demo_public")

def run_scenario(script_path: str):
    logger.info(f"Starting simulated scenario: {script_path}")
    try:
        env = os.environ.copy()
        env["DEMO_ORG_ID"] = DEMO_ORG_ID
        env["CORTEXHEAL_ORG_ID"] = DEMO_ORG_ID
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300,  # Max 5 minutes per scenario
            env=env
        )
        if result.returncode != 0:
            logger.error(f"Scenario {script_path} failed with exit code {result.returncode}")
            logger.error(f"Stderr: {result.stderr}")
        else:
            logger.info(f"Scenario {script_path} completed successfully.")
    except subprocess.TimeoutExpired:
        logger.error(f"Scenario {script_path} timed out.")
    except Exception as e:
        logger.error(f"Failed to execute {script_path}: {e}")

def main():
    logger.info(f"Initializing CortexHeal Live Demo Cron Engine (org_id={DEMO_ORG_ID})...")
    
    scenarios = [
        "examples/demo_stuck_loop_with_recovery.py",
        "examples/demo_budget_overrun.py",
        "examples/demo_multi_agent_fleet.py"
    ]
    
    # Prune function to prevent the demo view from accumulating hundreds of rows
    def prune_old_demo_data():
        logger.info(f"Pruning demo data for org_id={DEMO_ORG_ID} (keeping last 50 runs)")
        try:
            # We use a direct psycopg2 connection via our storage layer to execute pruning
            # We keep the last 50 runs and delete the rest to bound the dashboard UI
            from cortexheal.storage.postgres import get_connection
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH KeepRuns AS (
                            SELECT run_id FROM runs WHERE org_id = %s ORDER BY start_time DESC LIMIT 50
                        ),
                        StaleRuns AS (
                            SELECT run_id FROM runs WHERE org_id = %s AND run_id NOT IN (SELECT run_id FROM KeepRuns)
                        )
                        DELETE FROM runs WHERE run_id IN (SELECT run_id FROM StaleRuns)
                        RETURNING run_id
                    """, (DEMO_ORG_ID, DEMO_ORG_ID))
                    
                    # Wait, runs table doesn't have ON DELETE CASCADE.
                    # Let's do it properly without foreign key constraint errors.
                    pass
        except Exception as e:
            logger.error(f"Failed to prune demo data: {e}")

    # Better prune function
    def prune_old_demo_data_safe():
        logger.info(f"Pruning demo data for org_id={DEMO_ORG_ID} (keeping last 50 runs)")
        try:
            from cortexheal.storage.postgres import get_connection
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH KeepRuns AS (
                            SELECT run_id FROM runs WHERE org_id = %s ORDER BY start_time DESC LIMIT 50
                        )
                        SELECT run_id FROM runs WHERE org_id = %s AND run_id NOT IN (SELECT run_id FROM KeepRuns)
                    """, (DEMO_ORG_ID, DEMO_ORG_ID))
                    stale_runs = [r[0] for r in cur.fetchall()]
                    
                    if stale_runs:
                        logger.info(f"Found {len(stale_runs)} stale runs to delete.")
                        stale_tuple = tuple(stale_runs)
                        
                        # Delete related records
                        cur.execute("DELETE FROM recovery_outcomes WHERE run_id IN %s", (stale_tuple,))
                        cur.execute("DELETE FROM recovery_actions WHERE run_id IN %s", (stale_tuple,))
                        cur.execute("DELETE FROM recovery_plans WHERE incident_id IN (SELECT incident_id FROM incidents WHERE run_id IN %s)", (stale_tuple,))
                        cur.execute("DELETE FROM notification_records WHERE run_id IN %s", (stale_tuple,))
                        cur.execute("DELETE FROM incidents WHERE run_id IN %s", (stale_tuple,))
                        cur.execute("DELETE FROM audit_events WHERE run_id IN %s", (stale_tuple,))
                        cur.execute("DELETE FROM events WHERE run_id IN %s", (stale_tuple,))
                        cur.execute("DELETE FROM runs WHERE run_id IN %s", (stale_tuple,))
                        conn.commit()
                        logger.info(f"Successfully pruned {len(stale_runs)} stale runs.")
        except Exception as e:
            logger.error(f"Failed to prune demo data safely: {e}")
    
    iteration = 0
    import random
    while True:
        iteration += 1
        logger.info(f"--- Starting Demo Iteration {iteration} (org_id={DEMO_ORG_ID}) ---")
        
        # Shuffle scenarios so they happen in a random variety sequence
        random.shuffle(scenarios)
        for scenario in scenarios:
            run_scenario(scenario)
            logger.info("Waiting 30 seconds before next scenario...")
            time.sleep(30)
            
        prune_old_demo_data_safe()
            
        logger.info("Iteration complete. Waiting 3 minutes before restarting...")
        time.sleep(180)

if __name__ == "__main__":
    main()
