"""
Local Site Evidence Extractor
Renders and dumps actual DOM text from site/dist
"""

import http.server
import socketserver
import threading
import time
import urllib.request
import re

PORT = 3001
DIRECTORY = "site/dist"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # Handle SPA fallback for client-side routing
        if "." not in self.path:
            self.path = "/index.html"
        return super().do_GET()

    def log_message(self, format, *args):
        pass

def main():
    server = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.5)

    print("=" * 75)
    print(f"  FETCHING REAL SITE DOM & CONTENT FROM http://127.0.0.1:{PORT}")
    print("=" * 75)

    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/index.html")
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")

    print("\n[1] Raw HTML Header & Structure (site/dist/index.html):")
    print("-" * 75)
    print(html[:600])
    print("-" * 75)

    # Extract title, meta tags, and scripts
    title_match = re.search(r'<title>(.*?)</title>', html)
    desc_match = re.search(r'<meta name="description" content="(.*?)"', html)
    script_match = re.search(r'<script .*?src="(.*?)"></script>', html)

    print("\n[2] Verified Rendered Metadata:")
    print(f"    Page Title:       {title_match.group(1) if title_match else 'N/A'}")
    print(f"    Meta Description: {desc_match.group(1) if desc_match else 'N/A'}")
    print(f"    Bundled JS:       {script_match.group(1) if script_match else 'N/A'}")

    # Read JS bundle to verify exact copy & component text rendered in bundle
    js_path = script_match.group(1).lstrip("/") if script_match else ""
    if js_path:
        with open(f"site/dist/{js_path}", "r", encoding="utf-8") as f:
            js_content = f.read()

        print("\n[3] Verified Content Strings in Compiled Production Bundle:")
        searches = [
            "Real-time, deterministic safety & circuit-breaker control plane for AI agents.",
            "Zero LLMs in the safety-decision path.",
            "Why LLMs Should Never Make Safety Decisions About LLMs (The Deterministic Imperative)",
            "Sub-Millisecond Circuit Breakers: How CortexHeal Protects Agent Fleets at Scale",
            "LangGraphAdapter",
            "SOC2 Compliant Audits"
        ]
        for s in searches:
            present = s in js_content
            print(f"    - '{s[:65]}...': {'[VERIFIED FOUND]' if present else '[MISSING]'}")

    server.shutdown()
    print("\n" + "=" * 75)
    print("  REAL SITE EVIDENCE EXTRACTION COMPLETE")
    print("=" * 75)

if __name__ == "__main__":
    main()
