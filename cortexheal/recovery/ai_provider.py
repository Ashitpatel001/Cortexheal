from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from cortexheal.models.recovery import RecoveryAnalysis
from cortexheal.models.incident import Incident
from cortexheal.models.run import AgentRun
from cortexheal.models.events import RuntimeEvent

class RecoveryAIProvider(ABC):
    @abstractmethod
    def analyze_incident(self, incident: Incident, run: AgentRun, events: List[RuntimeEvent]) -> RecoveryAnalysis:
        pass

class MockAIProvider(RecoveryAIProvider):
    """
    A robust mock provider for testing and deterministic fallback.
    Returns a highly structured analysis indicating the most logical action.
    """
    def analyze_incident(self, incident: Incident, run: AgentRun, events: List[RuntimeEvent]) -> RecoveryAnalysis:
        if incident.failure_type == "STUCK_LOOP":
            return RecoveryAnalysis(
                diagnosis="The agent appears to be repeatedly invoking the same tool without observable progress.",
                evidence=f"Tool execution repeated beyond threshold ({incident.threshold}).",
                confidence=0.91,
                contributing_factors=["Lack of state change between identical tool calls"],
                proposed_actions=[
                    {"action_type": "KEEP_PAUSED", "reason": "Safest default posture for infinite loops"},
                    {"action_type": "RESUME", "reason": "Requires human confirmation that loop is broken out-of-band"}
                ],
                recommended_action="KEEP_PAUSED",
                risk_level="LOW",
                reasoning_summary="Resuming without modifying execution context may reproduce the same failure.",
                limitations="Cannot determine semantic intent behind repeated calls."
            )
        elif incident.failure_type == "BUDGET_EXCEEDED":
            return RecoveryAnalysis(
                diagnosis="The agent run exceeded its maximum allowed cost budget.",
                evidence=f"Run accumulated cost > {incident.threshold}.",
                confidence=0.99,
                contributing_factors=["High volume of operations", "Expensive tool usage"],
                proposed_actions=[
                    {"action_type": "KEEP_PAUSED", "reason": "Prevent further unapproved spend"}
                ],
                recommended_action="KEEP_PAUSED",
                risk_level="LOW",
                reasoning_summary="Automatic resumption would violate strict financial constraints.",
                limitations="Does not analyze individual token costs."
            )
        
        # Default fallback
        return RecoveryAnalysis(
            diagnosis="Incident detected. Cause requires further investigation.",
            evidence="See raw incident properties.",
            confidence=0.50,
            contributing_factors=[],
            proposed_actions=[{"action_type": "KEEP_PAUSED", "reason": "Default safety action"}],
            recommended_action="KEEP_PAUSED",
            risk_level="UNKNOWN", # Unknown risk triggers policy rejection for execution
            reasoning_summary="Lacking specific signature analysis.",
            limitations="Fallback heuristic applied."
        )

import os
import json

class RealAIProvider(RecoveryAIProvider):
    """
    A real AI Provider integration (e.g. OpenAI/Anthropic/Gemini).
    Configured strictly through environment variables.
    """
    def __init__(self):
        self.api_key = os.environ.get("CORTEXHEAL_AI_API_KEY")
        self.provider_url = os.environ.get("CORTEXHEAL_AI_URL")
        
    def analyze_incident(self, incident: Incident, run: AgentRun, events: List[RuntimeEvent]) -> RecoveryAnalysis:
        if not self.api_key:
            raise ValueError("AI Provider configured but CORTEXHEAL_AI_API_KEY is missing.")
            
        # In a real environment, this would build a prompt with strict system instructions:
        # 1. System rules (CortexHeal policy is supreme)
        # 2. Schema definition (RecoveryAnalysis)
        # 3. Untrusted Data (Agent/Tool output)
        
        # Here we simulate the external call that parses JSON strictly into the Pydantic model
        raise NotImplementedError("Real API connection requires external network access. For tests, fallback is triggered.")
