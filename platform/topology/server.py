#!/usr/bin/env python3
"""Serves the lab topology page on :3002, plus two read-only JSON feeds for it.

/state.json  each tenant's Run:ai GPU quota, BNK rate limit and 1-minute request rates
/trace.json  the steps of the last agent-team run, parsed from the log agents/run.sh records

Read-only: it runs `labctl tenant list --json` and queries Prometheus. It never writes anything.
"""
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("TOPOLOGY_PORT", "3002"))
LABCTL = os.environ.get("LABCTL", "/usr/local/bin/labctl")
TRACE_LOG = os.environ.get("AGENTS_TRACE_LOG", "/var/log/bnk-agents/last-run.log")
CACHE_SECONDS = 4
_cache = {"at": 0.0, "body": b""}


def prometheus_url():
    if os.environ.get("PROMETHEUS_URL"):
        return os.environ["PROMETHEUS_URL"]
    ip = subprocess.run(["kubectl", "-n", "monitoring", "get", "svc", "kube-prometheus-stack-prometheus",
                         "-o", "jsonpath={.spec.clusterIP}"], capture_output=True, text=True, timeout=10).stdout.strip()
    return f"http://{ip}:9090" if ip else ""


def rates(prom, expr):
    """Instant query, returned as {project: value}. None when Prometheus can't be reached, so the
    page shows the rate as unknown instead of 0."""
    if not prom:
        return None
    try:
        url = prom + "/api/v1/query?" + urllib.parse.urlencode({"query": expr})
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.load(r)
        return {s["metric"].get("project", ""): round(float(s["value"][1]), 1) for s in data["data"]["result"]}
    except Exception:
        return None


def state():
    now = time.time()
    if now - _cache["at"] < CACHE_SECONDS:
        return _cache["body"]
    out = {"at": int(now), "tenants": [], "error": None}
    try:
        res = subprocess.run([LABCTL, "tenant", "list", "--json"], capture_output=True, text=True, timeout=20)
        tenants = json.loads(res.stdout) if res.returncode == 0 else []
        if res.returncode != 0:
            out["error"] = (res.stderr.strip().splitlines() or ["labctl tenant list failed"])[-1]
    except Exception as e:  # labctl missing or cluster not up yet
        tenants, out["error"] = [], str(e)
    prom = prometheus_url()
    served = rates(prom, 'sum by (project) (rate(bnk_requests_total{code!="429"}[1m]))')
    refused = rates(prom, 'sum by (project) (rate(bnk_requests_total{code="429"}[1m]))')
    if served is None or refused is None:
        out["error"] = out["error"] or "Prometheus not reachable, request rates unknown"
    for t in tenants:
        p = t.get("project")
        out["tenants"].append({
            "project": p,
            "gpu": t.get("gpuDeserved"),
            "rateLimitRps": t.get("rateLimitRps"),
            "vip": t.get("vip"),
            "phase": t.get("phase"),
            "servedRps": None if served is None else served.get(p, 0.0),
            "refusedRps": None if refused is None else refused.get(p, 0.0),
        })
    _cache.update(at=now, body=json.dumps(out).encode())
    return _cache["body"]


ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\r")
MARKERS = [  # NeMo Agent Toolkit's ReAct log lines, in the order they appear
    ("action", re.compile(r"^Action:\s*(.+)")),
    ("input", re.compile(r"^Action Input:\s*(.+)")),
    ("final", re.compile(r"^Final Answer:\s*(.*)")),
    ("prompt", re.compile(r"(Run:ai dry run for project .+?Approve this change\?)")),
    ("reply", re.compile(r"^\s*(yes|no)\s*$", re.I)),
    ("result", re.compile(r"^((?:Applied|Declined by the operator|Refused):.*)")),
]


def trace():
    if not os.path.exists(TRACE_LOG):
        return json.dumps({"at": None, "steps": [], "note": "No agent run yet. Run labctl agents."}).encode()
    with open(TRACE_LOG, errors="replace") as f:
        lines = [ANSI.sub("", l).rstrip() for l in f]
    steps, question = [], None
    for line in lines:
        if question is None and line.startswith("# question: "):
            question = line[len("# question: "):]
            continue
        for kind, rx in MARKERS:
            m = rx.search(line)
            if not m:
                continue
            text = m.group(1).strip()
            if kind == "input" and steps and steps[-1]["kind"] == "action":
                steps[-1]["input"] = text
            elif kind == "prompt" and steps and steps[-1]["kind"] == "prompt":
                pass  # NAT prints the prompt twice
            else:
                steps.append({"kind": kind, "text": text})
            break
    return json.dumps({"at": int(os.path.getmtime(TRACE_LOG)), "question": question, "steps": steps}).encode()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/state.json", "/trace.json"):
            body = state() if path == "/state.json" else trace()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path not in ("/", "/topology.html"):
            self.send_error(404)  # serve the page only, not the rest of the directory
            return
        self.path = "/topology.html"
        super().do_GET()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
