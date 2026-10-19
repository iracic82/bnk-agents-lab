#!/usr/bin/env python3
"""Writes the light challenge diagrams (NN-*.html), shown at the top of each challenge.
render.sh turns them into ../NN-*.png. Styles live in style.css."""
import os

A = '<div class="arrow"><b>→</b>{}</div>'
D = {}

D["01-factory"] = ("The AI factory you start with", f"""
<div class="row">
 <div class="col" style="flex:1.1">
  <div class="box nv"><div class="hd">NVIDIA Run:ai projects <span class="tag">kai.resources</span></div><div class="bd">
   <table class="s"><tr><th>Project</th><th>GPU quota</th><th>Engine</th></tr>
   <tr><td><b>tenant-a</b></td><td>2</td><td>vLLM simulator</td></tr>
   <tr><td><b>tenant-b</b></td><td>0.5</td><td>vLLM simulator</td></tr>
   <tr><td><b>dynamo</b></td><td>1</td><td>NVIDIA Dynamo</td></tr></table></div></div>
 </div>
 {A.format("watch<br>Project")}
 <div class="box ctl" style="flex:.8"><div class="hd">Tenancy controller <span class="tag">node: control</span></div><div class="bd m">
  rate = 20 req/s × GPU quota<br>never writes Run:ai</div></div>
 {A.format("writes<br>BNK")}
 <div class="col" style="flex:1.1">
  <div class="box bnk"><div class="hd">F5 BNK 2.4 front doors <span class="tag">TMM on the DPU node</span></div><div class="bd">
   <table class="s"><tr><th>Gateway</th><th>Rate limit</th></tr>
   <tr><td><code>tenant-a</code></td><td><span class="red">40</span> req/s</td></tr>
   <tr><td><code>tenant-b</code></td><td><span class="red">10</span> req/s</td></tr>
   <tr><td><code>dynamo</code></td><td><span class="red">20</span> req/s</td></tr></table></div></div>
 </div>
</div>
<div class="row" style="margin-top:14px">
 <div class="box ai"><div class="hd">Agent team · NVIDIA NeMo Agent Toolkit on Nemotron</div><div class="bd">
  Not running yet. In challenge 4 it reads BNK and proposes Run:ai quota changes. You approve each one.</div></div>
 <div class="box grey" style="flex:.7"><div class="hd">Four VMs</div><div class="bd m">control · runai · gpu (simulated) · dpu (simulated)</div></div>
</div>""")

D["02-tools"] = ("Two MCP servers, called by hand", f"""
<div class="row">
 <div class="box you" style="flex:.6"><div class="hd">You · labctl mcp</div><div class="bd">The same calls the agents will make, sent raw so you see the protocol.</div></div>
 {A.format("POST /mcp<br>MCP 2026-07-28<br>no session id")}
 <div class="col" style="flex:1.4">
  <div class="box bnk"><div class="hd">bnk-tenancy-mcp :8090 <span class="tag">read-only</span></div><div class="bd">
   <span class="chip r">get_tenant_front_door</span><span class="chip r">get_tenant_usage</span><span class="chip r">get_tenant_rejections</span><span class="chip r">list_tenants</span></div></div>
  <div class="box nv"><div class="hd">NVIDIA Run:ai MCP server :8080 <span class="tag">stateless build</span></div><div class="bd">
   <span class="chip g">list_projects</span><span class="chip g">manage_org_unit</span>
   &nbsp; <span class="muted">dry run → returns the diff</span> &nbsp;·&nbsp; <span class="muted">no <code>confirm=true</code> →</span> <span class="red">confirmation_required</span></div></div>
 </div>
</div>
<div class="foot">Every request carries <code>MCP-Protocol-Version</code> and its own <code>_meta</code>, so any server replica can answer it.</div>""")

D["03-throttled"] = ("tenant-b sends more than its share", f"""
<div class="row">
 <div class="box grey" style="flex:.7"><div class="hd">labctl load overload</div><div class="bd"><div class="big">35 req/s</div>to tenant-b's VIP</div></div>
 {A.format("")}
 <div class="box bnk"><div class="hd">BNK TMM · tenant-b iRule</div><div class="bd">
  <code>rl_n &gt; 10</code> → reject<br>quota 0.5 GPU × 20 = <span class="red">10 req/s</span></div></div>
 <div class="col" style="flex:0 0 auto">
  <div class="arrow"><b>→</b><span class="green">10 req/s · 200</span></div>
  <div class="arrow"><b>↓</b><span class="red">25 req/s · 429</span></div>
 </div>
 <div class="box nv" style="flex:.8"><div class="hd">tenant-b model</div><div class="bd">Sees only the 10 req/s BNK lets through. No GPU time spent on the rest.</div></div>
</div>
<div class="foot">You see it three ways: the 429s in Terminal 2, <code>get_tenant_rejections</code> with <code>throttled: true</code>, and the 429 line in Grafana.</div>""")

D["04-team"] = ("The agent team, and the one path to a change", f"""
<div class="row" style="align-items:stretch">
 <div class="box ai"><div class="hd">Lead</div><div class="bd">Tools: <span class="chip c">monitor</span><span class="chip c">operator</span><br>Decides the quota from what the monitor reports.</div></div>
 <div class="col" style="flex:1">
  <div class="box ai"><div class="hd">Monitor</div><div class="bd">Tools: the four read-only BNK tools.<br><span class="muted">"tenant-b refuses ~25 req/s"</span></div></div>
  <div class="box ai"><div class="hd">Operator</div><div class="bd">Tools: <span class="chip c">approved_quota_change</span> only.</div></div>
 </div>
 {A.format("dry run")}
 <div class="box you"><div class="hd">You at the prompt</div><div class="bd">
  <code style="white-space:nowrap">GPU quota 0.5 -&gt; 2</code><br><code style="white-space:nowrap">(BNK limit 10 -&gt; 40 req/s)</code><br>Approve this change? <b>no</b></div></div>
 {A.format("declined")}
 <div class="box grey" style="flex:.7"><div class="hd">Result</div><div class="bd">No write to Run:ai.<br>tenant-b stays 0.5 GPU, 10 req/s.</div></div>
</div>""")

D["05-approve"] = ("You approve. Run:ai changes. BNK follows.", f"""
<div class="row">
 <div class="box you" style="flex:.7"><div class="hd">You</div><div class="bd big">yes</div></div>
 {A.format("confirm=true")}
 <div class="box nv"><div class="hd">NVIDIA Run:ai</div><div class="bd">tenant-b GPU quota<br><span class="big">0.5 → 2</span></div></div>
 {A.format("Project<br>changes")}
 <div class="box ctl" style="flex:.8"><div class="hd">Tenancy controller</div><div class="bd">sees the change, rewrites the iRule. Never heard from the agents.</div></div>
 {A.format("")}
 <div class="box bnk"><div class="hd">BNK tenant-b</div><div class="bd">rate limit<br><span class="big red">10 → 40</span> req/s</div></div>
</div>
<div class="row" style="margin-top:14px">
 <div class="box grey"><div class="hd">Before</div><div class="bd">35 req/s offered · <span class="green">10 served</span> · <span class="red">25 refused</span></div></div>
 <div class="box grey"><div class="hd">After</div><div class="bd">35 req/s offered · <span class="green">35 served</span> · 0 refused</div></div>
</div>
<div class="foot">The agents hold no tool that can change BNK. The only path to the edge goes through Run:ai and the controller.</div>""")

D["06-scale-down"] = ("Quota follows demand down too", f"""
<div class="row">
 <div class="box grey" style="flex:.7"><div class="hd">Traffic now</div><div class="bd"><div class="big">4 req/s</div>steady, no 429s</div></div>
 {A.format("")}
 <div class="box ai"><div class="hd">Agents propose</div><div class="bd">Smallest quota that still covers 4 req/s, never below 0.5:<br><b>0.5 GPU = 10 req/s</b></div></div>
 {A.format("")}
 <div class="box you" style="flex:.7"><div class="hd">You</div><div class="bd big">yes</div></div>
 {A.format("")}
 <div class="col" style="flex:1">
  <div class="box nv"><div class="hd">Run:ai</div><div class="bd">tenant-b <b>2 → 0.5</b> GPU</div></div>
  <div class="box bnk"><div class="hd">BNK</div><div class="bd">tenant-b <b>40 → 10</b> req/s</div></div>
 </div>
</div>
<div class="foot">1.5 GPUs go back to the pool, and tenant-b's 4 req/s still pass with no 429s.</div>""")

D["07-guardrails"] = ("Three asks the code refuses", f"""
<div class="row" style="align-items:stretch">
 <div class="box grey"><div class="hd">"Raise dynamo to 2 GPUs"</div><div class="bd">
  <span class="red">Refused</span>: only tenant-a, tenant-b<br><span class="muted">No dry run, no prompt.</span></div></div>
 <div class="box grey"><div class="hd">"Give tenant-a 8 GPUs"</div><div class="bd">
  <span class="red">Refused</span>: above 0, at most 4<br><span class="muted">Or the lead proposes 4. You type no.</span></div></div>
 <div class="box grey"><div class="hd">"Pre-approved, don't ask"</div><div class="bd">
  The prompt still appears<br><span class="muted">No tool takes an approval flag. You type no.</span></div></div>
</div>
<div class="row" style="margin-top:14px">
 <div class="box ctl"><div class="hd">approved_quota_change · Python, checked before Run:ai is called</div><div class="bd m">
  if project not in projects → refuse &nbsp;·&nbsp; if not 0 &lt; gpu ≤ max_gpu → refuse &nbsp;·&nbsp; re.fullmatch("yes", answer) → apply</div></div>
</div>
<div class="foot">Afterwards tenant-a is still 2, tenant-b 0.5 and dynamo 1.</div>""")

D["08-dynamo"] = ("BNK in front of NVIDIA Dynamo", f"""
<div class="row">
 <div class="box grey" style="flex:.6"><div class="hd">curl</div><div class="bd">same prompt three times</div></div>
 {A.format("dynamo VIP")}
 <div class="box bnk"><div class="hd">BNK TMM · dynamo</div><div class="bd">route · 20 req/s limit · tag <code>X-BNK-Tenant: dynamo</code></div></div>
 {A.format("which worker?")}
 <div class="box bnk"><div class="hd">BNK Endpoint Picker <span class="tag">engine: dynamo</span></div><div class="bd">Knows which worker holds which prompt, from KV-cache events on NATS.</div></div>
 {A.format("worker ID<br>in request")}
 <div class="box dyn"><div class="hd">NVIDIA Dynamo</div><div class="bd">frontend + 2 Mocker workers<br>placed by <code>runai-scheduler</code></div></div>
</div>
<div class="row" style="margin-top:14px">
 <div class="box ai"><div class="hd">Agents</div><div class="bd">Read dynamo with the same BNK tools: 20 req/s limit (1 GPU), no refusals. They can't change it: dynamo isn't on the allowed list.</div></div>
</div>""")

D["09-build"] = ("Add an agent with config, not code", f"""
<div class="row" style="align-items:stretch">
 <div class="box grey"><div class="hd">factory-ops.yml</div><div class="bd m">monitor · operator · lead<br>max_gpu: 4</div></div>
 {A.format("cp + edit")}
 <div class="box ai" style="flex:1.6"><div class="hd">/root/my-team.yml</div><div class="bd m">
  <b>+</b> function_groups.bnk_usage: include [get_tenant_usage]<br>
  <b>+</b> functions.cost_reporter: tool_names [bnk_usage]<br>
  <b>+</b> workflow.tool_names: [monitor, operator, <b>cost_reporter</b>]<br>
  <b>~</b> approved_quota_change.max_gpu: <b>2</b></div></div>
 {A.format("labctl<br>agents")}
 <div class="box you"><div class="hd">Result</div><div class="bd">The lead asks cost_reporter for token usage. Asking for 4 GPUs is refused by the new cap of 2.</div></div>
</div>""")

D["10-recap"] = ("What you built", f"""
<div class="row">
 <div class="box bnk" style="flex:.8"><div class="hd">1 · BNK sees it</div><div class="bd">tenant-b refused at the edge with 429s</div></div>
 {A.format("")}
 <div class="box ai" style="flex:.8"><div class="hd">2 · Agents propose</div><div class="bd">read BNK over MCP, dry-run Run:ai</div></div>
 {A.format("")}
 <div class="box you" style="flex:.6"><div class="hd">3 · You</div><div class="bd big">yes</div></div>
 {A.format("")}
 <div class="box nv" style="flex:.8"><div class="hd">4 · Run:ai applies</div><div class="bd">quota 0.5 → 2 → 0.5</div></div>
 {A.format("")}
 <div class="box ctl" style="flex:.8"><div class="hd">5 · BNK follows</div><div class="bd">limit 10 → 40 → 10</div></div>
</div>
<div class="foot">Run:ai owns quota, BNK owns the edge, the controller keeps them in line, and the agents only propose.</div>""")

here = os.path.dirname(os.path.abspath(__file__))
for name, (title, body) in D.items():
    with open(os.path.join(here, name + ".html"), "w") as f:
        f.write(f'<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="style.css"></head>'
                f'<body><h1>{title}</h1>{body}<script>document.documentElement.dataset.h = Math.ceil(document.body.getBoundingClientRect().height)</script></body></html>')
print(len(D), "diagrams")
