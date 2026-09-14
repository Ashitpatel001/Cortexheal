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
        "examples/demo_budget_overrun.py"
    ]
    
    iteration = 0
    while True:
        iteration += 1
        logger.info(f"--- Starting Demo Iteration {iteration} (org_id={DEMO_ORG_ID}) ---")
        
        for scenario in scenarios:
            run_scenario(scenario)
            
            # Wait a few seconds between scenarios to allow observers to see 
            # the dashboard state settle before the next one hits.
            logger.info("Waiting 30 seconds before next scenario...")
            time.sleep(30)
            
        # Wait 3 minutes before restarting the entire loop
        # This ensures visitors see a continuous stream of events if they stay on the page.
        logger.info("Iteration complete. Waiting 3 minutes before restarting...")
        time.sleep(180)

if __name__ == "__main__":
    main()
