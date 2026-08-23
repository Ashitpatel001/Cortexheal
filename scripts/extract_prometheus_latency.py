"""
Extracts the exact cortexheal_ingestion_latency_seconds histogram samples and quantiles.
"""
import sys
from prometheus_client import REGISTRY, generate_latest

def extract_histogram_metrics():
    found = False
    for metric in REGISTRY.collect():
        if metric.name == "cortexheal_ingestion_latency_seconds":
            found = True
            print("=" * 75)
            print("  PROMETHEUS HISTOGRAM: cortexheal_ingestion_latency_seconds")
            print("=" * 75)
            print(f"Metric Documentation: {metric.documentation}")
            print(f"Metric Type:          {metric.type}")
            print("-" * 75)
            
            samples = metric.samples
            total_count = 0
            total_sum = 0.0
            buckets = []
            
            for s in samples:
                if s.name.endswith("_count"):
                    total_count = s.value
                elif s.name.endswith("_sum"):
                    total_sum = s.value
                elif s.name.endswith("_bucket"):
                    le = s.labels.get("le")
                    buckets.append((float(le) if le != "+Inf" else float("inf"), s.value))
                    
            print(f"Total Observed Events (Count): {int(total_count)}")
            print(f"Total Ingestion Sum:           {total_sum:.6f} seconds ({total_sum*1000:.3f} ms)")
            if total_count > 0:
                avg_latency = (total_sum / total_count) * 1000
                print(f"Average Ingestion Latency:     {avg_latency:.3f} ms")
            
            print("\nCumulative Histogram Buckets (Raw Seconds & Milliseconds):")
            print("-" * 75)
            prev_val = 0
            for upper_bound, count in buckets:
                delta = count - prev_val
                prev_val = count
                bound_str = f"{upper_bound*1000:.2f} ms" if upper_bound != float("inf") else "+Inf"
                print(f"  <= {bound_str:<12} : {int(count):<6} cumulative ({int(delta)} events in bucket)")
            print("=" * 75)

if __name__ == "__main__":
    extract_histogram_metrics()
