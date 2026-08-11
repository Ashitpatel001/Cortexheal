import argparse
from cortexheal.storage.postgres import get_run, get_events_for_run

def main():
    parser = argparse.ArgumentParser(description="CortexHeal Protect V1 - Local Debug")
    parser.add_argument("run_id", help="The UUID of the run to inspect")
    args = parser.parse_args()

    run = get_run(args.run_id)
    if not run:
        print(f"Run {args.run_id} not found.")
        return

    print(f"RUN {run.run_id} | Agent: {run.agent_id} | Status: {run.status}")
    print(f"Start: {run.start_time} | End: {run.end_time}")
    print("-" * 50)
    
    events = get_events_for_run(args.run_id)
    for event in events:
        tokens_info = f" | Tokens: {event.tokens.total}" if event.tokens and event.tokens.total > 0 else ""
        latency_info = f" | {event.latency_ms}ms" if event.latency_ms else ""
        tool_info = f" {event.tool}" if event.tool else ""
        print(f"{event.sequence_number} {event.event_type}{tool_info} [{event.status}]{latency_info}{tokens_info}")

if __name__ == "__main__":
    main()
