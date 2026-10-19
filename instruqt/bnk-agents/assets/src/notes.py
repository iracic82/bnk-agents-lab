#!/usr/bin/env python3
"""Writes the dark 1600x900 notes slides (notes-*.html), shown while a challenge's sandbox starts.
render.sh turns them into ../notes-*.png. Each card: (accent, kicker, title, text)."""
import html, os

G, R, B, C, P = "#76b900", "#e4002b", "#6c9aff", "#3fd0e0", "#9b7bff"
SLIDES = {
    "notes-01-hero": ("Challenge 1 · Meet the factory",
        'Agents <g>propose</g>. You <c>approve</c>.<br>BNK <r>follows by itself</r>.',
        "An agent team built with NVIDIA NeMo Agent Toolkit runs this AI factory through MCP. It reads BNK, proposes a "
        "Run:ai GPU quota, and changes nothing until you say yes. BNK then follows Run:ai with no one touching it.",
        [(G, "NVIDIA Run:ai", "Holds the GPU quota", "Every tenant is a Run:ai project with its own share of GPUs."),
         (R, "F5 BNK 2.4", "Enforces it at the edge", "Each tenant's rate limit comes from its quota: 20 req/s per GPU."),
         (C, "Agent team", "Watches and proposes", "Three NeMo Agent Toolkit agents on NVIDIA Nemotron, over two MCP servers.")]),
    "notes-01-real": ("Challenge 1 · What is real here",
        'Real software. <r>Simulated</r> hardware.',
        "BNK 2.4, open-source Run:ai, both MCP servers, NeMo Agent Toolkit and Nemotron are all real. "
        "The GPUs, the model servers and the DPU stand in for hardware this sandbox doesn't have.",
        [(G, "Real", "The whole control path", "Run:ai control plane and scheduler, BNK, the controller, the agents and their tools."),
         (R, "Simulated", "GPUs and models", "NVIDIA's fake-gpu-operator, vLLM simulators and Dynamo's Mocker return filler text."),
         (B, "Simulated", "The BlueField DPU", "A separate node with a tunnel. The request path is real, DPU offload isn't measured.")]),
    "notes-02": ("Challenge 2 · The tools agents get",
        'Two MCP servers. <c>One</c> can write.',
        "Before any agent runs, call the same tools by hand. Both servers speak MCP 2026-07-28 with no sessions.",
        [(R, "bnk-tenancy-mcp", "Four read-only tools", "What BNK built for a tenant, its usage, and how many requests it refuses."),
         (G, "Run:ai MCP server", "One write path", "manage_org_unit dry-runs first and refuses to apply without confirm=true."),
         (C, "Stateless", "No session id", "Every request carries its own protocol version. Any replica can answer it.")]),
    "notes-03": ("Challenge 3 · tenant-b gets throttled",
        'More traffic than its share.<br>BNK <r>refuses the extra</r>.',
        "tenant-b sends 35 requests a second on a 0.5 GPU quota. BNK lets 10 through and answers the rest with 429.",
        [(G, "Run:ai quota", "0.5 GPU", "tenant-b's share, set by the Run:ai admin."),
         (R, "BNK limit", "10 req/s", "20 × 0.5, rendered into tenant-b's iRule by the controller."),
         (B, "At the edge", "429 before a GPU", "The refused requests never reach the model server.")]),
    "notes-04": ("Challenge 4 · The agent team",
        'They find the problem.<br>You say <r>no</r>.',
        "The monitor reads BNK, the lead decides, the operator asks Run:ai for a dry run and then asks you. "
        "Decline, and nothing changes anywhere.",
        [(C, "Monitor", "Reads BNK", "Holds only the four read-only BNK tools."),
         (C, "Lead", "Decides", "Holds the other two agents as its tools, nothing else."),
         (P, "Operator", "Asks you", "Holds approved_quota_change, the only path to a Run:ai write.")]),
    "notes-05": ("Challenge 5 · Approve and watch",
        'You say <g>yes</g>.<br>The 429s <g>stop</g>.',
        "Run:ai applies the new quota. The tenancy controller sees the change and rewrites tenant-b's iRule. "
        "The agents never held a tool that could change BNK.",
        [(P, "You", "yes", "The only thing that lets the operator send confirm=true."),
         (G, "Run:ai", "0.5 → 2 GPU", "tenant-b's project quota changes through Run:ai's own API."),
         (R, "BNK", "10 → 40 req/s", "The controller follows Run:ai. Nobody configures BNK.")]),
    "notes-06": ("Challenge 6 · Give the GPUs back",
        'Quota follows demand <g>both ways</g>.',
        "The rush is over. tenant-b holds 2 GPUs for 4 requests a second, so the agents propose returning them.",
        [(B, "Monitor", "4 req/s, no 429s", "Real traffic far under the 40 req/s limit."),
         (C, "Lead", "Smallest that fits", "0.5 GPU covers it. The team never goes below 0.5."),
         (P, "You", "Still approve", "Scaling down goes past a person too.")]),
    "notes-07": ("Challenge 7 · Guardrails",
        'Rules in <r>code</r>, not in the prompt.',
        "A model can be talked into things. The limits that matter live in the one tool that can write.",
        [(R, "Allowed list", "tenant-a, tenant-b", "dynamo is refused before any dry run."),
         (R, "Bounds", "Above 0, at most 4 GPUs", "8 GPUs never reaches Run:ai."),
         (P, "Approval", "An exact yes", "No tool takes an approval flag, so 'pre-approved' still prompts.")]),
    "notes-08": ("Challenge 8 · A Dynamo tenant",
        'Different engine. <c>Same front door</c>.',
        "NVIDIA Dynamo serves the third tenant. BNK's Endpoint Picker reads Dynamo's KV-cache events and picks the worker.",
        [(P, "NVIDIA Dynamo", "Frontend + 2 workers", "Mocker workers with real KV-cache events, no model weights."),
         (R, "BNK picker", "Dynamo mode", "Chooses the worker and writes its ID into the request."),
         (C, "Agents", "Same tools", "dynamo is read like any tenant, and can't be changed by them.")]),
    "notes-09": ("Challenge 9 · Build an agent",
        'Add an agent with <c>YAML</c>, not code.',
        "Copy the team's config, add a cost reporter that sees only one BNK tool, and tighten the GPU cap.",
        [(C, "New MCP group", "One tool only", "include: [get_tenant_usage] limits what the agent can call."),
         (C, "New agent", "cost_reporter", "A react_agent the lead can use as a tool."),
         (R, "Tighter cap", "max_gpu: 2", "The guardrail changes in config, the code stays the same.")]),
    "notes-10": ("Challenge 10 · Debrief",
        'A person approves.<br>The factory <g>does the rest</g>.',
        "Run:ai owns the quota, BNK owns the edge, the controller keeps them in line, and the agents only propose.",
        [(G, "NVIDIA", "Run:ai, NeMo Agent Toolkit, Nemotron, Dynamo", "Quota, agents, model and inference engine."),
         (R, "F5", "BIG-IP Next for Kubernetes 2.4", "Per-tenant front door, limits, 429s and worker picking."),
         (P, "You", "Every change", "Nothing moved without your yes.")]),
}

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;width:1600px;height:900px;background:#0b0c0b;color:#f2f2ee;font-family:Inter,"Helvetica Neue",Arial,sans-serif;position:relative;overflow:hidden}}
.bar{{height:8px;background:linear-gradient(90deg,#76b900 50%,#e4002b 50%)}}
.glow{{position:absolute;inset:0;background:radial-gradient(600px 400px at 100% 0,rgba(118,185,0,.10),transparent),radial-gradient(500px 360px at 0 100%,rgba(228,0,43,.10),transparent)}}
.wrap{{position:relative;padding:76px 100px 0}}
.eb{{font-size:22px;letter-spacing:.16em;text-transform:uppercase;color:#a6a8a2;font-weight:600}}
h1{{font-size:64px;line-height:1.03;margin:22px 0 22px;letter-spacing:-.02em;font-weight:800}}
g{{color:#9fd14a}} r{{color:#ff4f6d}} c{{color:#4fd8e8}}
p.l{{font-size:26px;line-height:1.5;color:#d6d7d2;margin:0;max-width:1300px}}
.cards{{display:flex;gap:24px;margin-top:52px}}
.card{{flex:1;background:#161816;border:1px solid #2a2d29;border-radius:14px;padding:30px 26px;position:relative}}
.card:before{{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;border-radius:14px 0 0 14px;background:var(--a)}}
.k{{font-size:15px;letter-spacing:.12em;text-transform:uppercase;color:#a6a8a2;font-weight:600}}
.t{{font-size:28px;font-weight:700;margin:12px 0 10px}}
.x{{font-size:19px;line-height:1.5;color:#c8c9c4}}
.ft{{position:absolute;right:100px;bottom:36px;font-size:16px;color:#7d7f7a}}
</style></head><body><div class="bar"></div><div class="glow"></div><div class="wrap">
<div class="eb">{eb}</div><h1>{h1}</h1><p class="l">{lede}</p><div class="cards">{cards}</div></div>
<div class="ft">NVIDIA Run:ai · NeMo Agent Toolkit · F5 BIG-IP Next for Kubernetes 2.4</div></body></html>"""

here = os.path.dirname(os.path.abspath(__file__))
for name, (eb, h1, lede, cards) in SLIDES.items():
    cs = "".join(f'<div class="card" style="--a:{a}"><div class="k">{html.escape(k)}</div><div class="t">{html.escape(t)}</div>'
                 f'<div class="x">{html.escape(x)}</div></div>' for a, k, t, x in cards)
    with open(os.path.join(here, name + ".html"), "w") as f:
        f.write(PAGE.format(eb=html.escape(eb), h1=h1, lede=html.escape(lede), cards=cs))
print(len(SLIDES), "slides")
