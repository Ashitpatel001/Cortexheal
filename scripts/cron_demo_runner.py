#!/usr/bin/env python3
import time
import subprocess
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def run_scenario(script_path: str):
    logger.info(f"Starting simulated scenario: {script_path}")
    try:
        # Run the demo script as a subprocess
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300  # Max 5 minutes per scenario
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
    """
    Infinite loop that drives the live public marketing demo.
    It sequentially fires the stuck loop and budget overrun scenarios to ensure
    the public-facing dashboard always has fresh, live data for visitors.
    """
    logger.info("Initializing CortexHeal Live Demo Cron Engine...")
    
    scenarios = [
        "examples/demo_stuck_loop_with_recovery.py",
        "examples/demo_budget_overrun.py"
    ]
    
    iteration = 0
    while True:
        iteration += 1
        logger.info(f"--- Starting Demo Iteration {iteration} ---")
        
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
