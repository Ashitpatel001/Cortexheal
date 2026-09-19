export interface Incident {
  incident_id: string;
  run_id: string;
  agent_id: string;
  failure_type: "STUCK_LOOP" | "BUDGET_EXCEEDED" | string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status: "OPEN" | "RESOLVED";
  detector: string;
  detector_version: string;
  trigger_event_id: string;
  evidence: Record<string, unknown>;
  observed_value?: number;
  threshold?: number;
  description: string;
  triggered_at: string;
  run_status: string;
  protection_mode: string;
}

export interface RecoveryPlanAction {
  action_id: string;
  run_id: string;
  incident_id: string;
  action_type: string;
  reason: string;
  status: string;
}

export interface RecoveryPlan {
  plan_id: string;
  incident_id: string;
  run_id: string;
  status: string;
  risk_level: string;
  diagnosis: string;
  proposed_actions: RecoveryPlanAction[];
  planner_type: string;
  verification_status: string;
  snapshot_run_status: string;
  pattern_trust?: any;
  snapshot_sequence_number: number;
  created_at: string;
}

export interface Run {
  run_id: string;
  agent_id: string;
  framework: string;
  status: "running" | "pause_requested" | "paused" | "resume_requested" | "completed" | "failed" | string;
  protection_mode: string;
  start_time: string;
  last_updated: string;
}

export interface TimelineEntry {
  type: "event" | "incident" | "audit";
  timestamp: string;
  data: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  skip: number;
  limit: number;
}
