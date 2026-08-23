import pytest
from cortexheal.storage.postgres import (
    get_all_runs, get_incidents, get_audit_export_records,
    get_api_keys_by_org, get_webhook_configs_by_org, init_db
)
from scripts.reseed_demo_data import reseed
from examples.demo_budget_overrun import main as run_budget_demo
from examples.demo_stuck_loop_with_recovery import main as run_stuck_loop_demo
from examples.demo_multi_agent_fleet import main as run_fleet_demo

def test_reseed_script_execution():
    """Verify that reseed_demo_data resets and populates realistic demo entities."""
    init_db()
    reseed()
    
    runs = get_all_runs()
    assert len(runs) >= 9
    
    incidents = get_incidents()
    assert len(incidents) >= 4
    
    # Check failure types
    failure_types = {i.failure_type for i in incidents}
    assert "STUCK_LOOP" in failure_types
    assert "BUDGET_EXCEEDED" in failure_types

    # Check API keys seeded
    keys = get_api_keys_by_org("default_org")
    assert len(keys) >= 3

    # Check Webhooks seeded
    webhooks = get_webhook_configs_by_org("default_org")
    assert len(webhooks) >= 1

    # Check Audit Export records
    export_records = get_audit_export_records(org_id="default_org")
    assert len(export_records) >= 4

def test_demo_budget_overrun_lifecycle():
    """Verify budget overrun demo executes end-to-end and triggers BUDGET_EXCEEDED incident."""
    run_budget_demo()
    
    incidents = get_incidents()
    budget_incidents = [i for i in incidents if i.failure_type == "BUDGET_EXCEEDED"]
    assert len(budget_incidents) >= 1
    assert budget_incidents[0].observed_value >= 1.00

def test_demo_stuck_loop_recovery_lifecycle():
    """Verify stuck loop demo triggers STUCK_LOOP incident, generates plan, and verifies recovery."""
    run_stuck_loop_demo()
    
    incidents = get_incidents()
    loop_incidents = [i for i in incidents if i.failure_type == "STUCK_LOOP"]
    assert len(loop_incidents) >= 1
    assert loop_incidents[0].observed_value >= 4

def test_demo_multi_agent_fleet():
    """Verify multi-agent fleet simulation executes across diverse frameworks."""
    run_fleet_demo()
    
    runs = get_all_runs()
    frameworks = {r.framework for r in runs}
    assert "langgraph" in frameworks
    assert "autogen" in frameworks
    assert "crewai" in frameworks
