
with open("cortexheal/server/api.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add import for get_patterns_by_org and TrustEngine
content = content.replace(
    "from cortexheal.storage.postgres import (",
    "from cortexheal.storage.postgres import (\n    get_patterns_by_org,"
)

if "from cortexheal.learning.trust import TrustEngine" not in content:
    content = content.replace(
        "from cortexheal.recovery.engine import RecoveryEngine",
        "from cortexheal.recovery.engine import RecoveryEngine\nfrom cortexheal.learning.trust import TrustEngine"
    )

new_endpoint = """
@app.get("/api/patterns")
def get_patterns_api(user: User = Depends(verify_api_key)):
    if user.role not in ["ADMIN", "OPERATOR", "VIEWER"]:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    patterns = get_patterns_by_org(user.org_id)
    trust_engine = TrustEngine()
    
    results = []
    for p in patterns:
        evidence = trust_engine.calculate_trust(p.pattern_id)
        actions_summary = []
        for action, stats in evidence.actions.items():
            actions_summary.append({
                "action": action,
                "attempted": stats.attempted,
                "verified_success": stats.verified_success,
                "verified_failure": stats.verified_failure,
                "success_rate": stats.success_rate,
                "trust_score": stats.trust_score,
                "risk_level": stats.risk_level
            })
            
        results.append({
            "pattern_id": p.pattern_id,
            "fingerprint": p.fingerprint,
            "failure_type": p.failure_type,
            "agent_id": p.agent_id,
            "occurrences": p.occurrences,
            "actions": actions_summary,
            "updated_at": p.updated_at
        })
        
    return {"data": results}
"""

if "@app.get(\"/api/patterns\")" not in content:
    # Insert it before the mount
    idx = content.find("# --- STATIC FILES ---")
    content = content[:idx] + new_endpoint + "\n\n" + content[idx:]
    
with open("cortexheal/server/api.py", "w", encoding="utf-8") as f:
    f.write(content)

