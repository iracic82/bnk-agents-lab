---
slug: meet-the-factory
type: challenge
title: Meet the AI factory
teaser: Three tenants share simulated GPUs. Run:ai decides who gets GPUs, BNK decides
  which requests reach them.
tabs:
- title: Terminal
  type: terminal
  hostname: control
- title: Topology
  type: service
  hostname: control
  path: /topology.html
  port: 3002
- title: Grafana
  type: service
  hostname: control
  path: /d/one-tenant-two-planes?orgId=1&kiosk&hideLogo&refresh=5s
  port: 3000
- title: Run:ai UI
  type: service
  hostname: control
  port: 3001
- title: Lab code
  type: code
  hostname: control
  path: /root/lab
difficulty: basic
timelimit: 1200
---
# Meet the AI factory

Before any agent touches this factory, have a look at what's running.

Three teams share the GPUs. Each one is a project in NVIDIA Run:ai, and each project's quota says how
much of the GPU estate it's owed. F5 BIG-IP Next for Kubernetes (BNK) 2.4 gives every project its own
front door and holds it to a request rate taken from that quota: 20 requests per second for each GPU.

| Tenant | Serves with | GPU quota | BNK limit |
|---|---|---|---|
| `tenant-a` | vLLM | 2 | 40 req/s |
| `tenant-b` | vLLM | 0.5 | 10 req/s |
| `dynamo` | NVIDIA Dynamo | 1 | 20 req/s |

Nobody configured BNK for any of them. A small controller watches Run:ai and writes the BNK side. Keep
that in mind, because the agents in this lab will only ever touch Run:ai.

## The tenants, from both sides

```bash,run
labctl status
```

You should see every check pass: BNK's data plane, the Run:ai cluster and API, the simulated GPUs, and the
controller that links Run:ai to BNK.

Now Run:ai's view next to BNK's:

```bash,run
kubectl get projects.kai.resources -o custom-columns='PROJECT:.metadata.name,NAMESPACE:.status.namespace,PHASE:.status.phase'
kubectl get gateway -n f5-bnk
```

Each Run:ai project has a Gateway of the same name in BNK, with its own address.

## Where the rate limit comes from

Look at tenant-b's front door:

```bash,run
labctl tenant show tenant-b
```

You should see `rate limit: 10 req/s`. That's 20 × 0.5 GPU. The number lives in an iRule the controller
wrote, and it changes when the Run:ai quota changes. Hold on to that number.

## Talk to a tenant

```bash,run
labctl chat tenant-b "What does a rate limit protect?"
```

The models here are simulators that return filler text, so don't read the answer for meaning. What's real
is the path: the request went through BNK, which tagged it for tenant-b and counted its tokens.

In **Grafana** you should see the three tenants in the table at the top, each with its GPU quota and
requests per second.

The **Topology** tab shows the same factory as a diagram, with every request path you'll use in this lab.

Next you'll look at the tools an agent gets to run this factory.
