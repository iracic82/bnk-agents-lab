---
slug: debrief
type: challenge
title: What you built, and what's real
teaser: A recap of the loop, what in this lab is real and what is simulated, and where it goes
  next.
tabs:
- title: Terminal
  type: terminal
  hostname: control
- title: Grafana
  type: service
  hostname: control
  path: /d/one-tenant-two-planes?orgId=1&kiosk&hideLogo&refresh=5s
  port: 3000
- title: Topology
  type: service
  hostname: control
  path: /topology.html
  port: 3002
difficulty: basic
timelimit: 900
---
# What you built, and what's real

A tenant hit its limit. Agents noticed, worked out the fix and asked you. You said yes, and the fix
reached the edge without anyone configuring it. Then the traffic dropped and the GPUs went back to the pool
the same way.

Here's the state you left the factory in:

```bash,run
for t in tenant-a tenant-b dynamo; do
  printf '%-9s quota %-4s ' $t "$(kubectl get projects.kai.resources $t -o jsonpath='{.spec.queues[*].resources.gpu.deserved}')"
  labctl mcp bnk call get_tenant_rejections "{\"project\":\"$t\"}" 2>/dev/null | jq -r '"BNK limit \(.rateLimitRps) req/s, refused \(.rejectedRps) req/s"'
done
```

In **Grafana**, scroll back over the session: tenant-b's 429s rising, stopping when you approved, its quota
going 0.5 → 2 → 0.5.

## Who did what

| Part | Product | What it did here |
|---|---|---|
| GPU quota per tenant | NVIDIA Run:ai (open source) | Held each tenant's share, applied the change you approved |
| The agents | NVIDIA NeMo Agent Toolkit, NVIDIA Nemotron | Read BNK, reasoned about quota, proposed one change at a time |
| Agent tools | MCP 2026-07-28, stateless, on both servers | Run:ai's own MCP server and F5's BNK tenancy server |
| The edge | F5 BIG-IP Next for Kubernetes 2.4 | Front door per tenant, limits from quota, 429s before a GPU is touched, Dynamo worker picking |
| The glue | A small open-source controller | Watches Run:ai, writes BNK |
| The approval | You | Nothing changed without your `yes` |

## Real and simulated

Real: BNK 2.4, Run:ai's control plane and scheduler, Run:ai's MCP server (built from NVIDIA's source with
one change, so it runs without sessions), NeMo Agent Toolkit, Nemotron, NVIDIA Dynamo's operator and
routing, the controller and everything on the request path.

Simulated: the GPUs (NVIDIA's fake-gpu-operator), the model servers (vLLM simulators and Dynamo's Mocker,
which return filler text) and the BlueField DPU (a separate node with a tunnel standing in for the PCIe
link, so the request path is real but DPU offload isn't measured).

## Where this goes next

The approval is the right default while people learn to trust agents with capacity. A few directions
from here: per-agent token budgets enforced by BNK, NeMo Guardrails on the agents' own conversations, and
letting the agents raise quota by themselves within a budget, while anything outside it still needs a
person.
