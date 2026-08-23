"""
Alerting and escalation subsystem for dispatching real-time notifications
(Slack Block Kit, generic webhooks) and automated on-call escalations.
"""

from cortexheal.alerting.dispatcher import AlertDispatcher

__all__ = ["AlertDispatcher"]
