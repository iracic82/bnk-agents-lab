---
slug: the-agent-team
id: ehv4bclucudd
type: challenge
title: The agent team
teaser: Three NeMo Agent Toolkit agents find the throttled tenant and propose a fix.
  You say no, and nothing changes.
notes:
- type: image
  url: ../assets/notes-04.png
tabs:
- id: yflrynip4533
  title: Terminal
  type: terminal
  hostname: control
- id: pkvvtzzkv1jw
  title: Terminal 2
  type: terminal
  hostname: control
- id: kgrvghbk5l1q
  title: Grafana
  type: service
  hostname: control
  path: /d/one-tenant-two-planes?orgId=1&kiosk&hideLogo&refresh=5s
  port: 3000
- id: qsnkofhipc6x
  title: Topology
  type: service
  hostname: control
  path: /topology.html
  port: 3002
difficulty: basic
timelimit: 1800
enhanced_loading: null
---
# The agent team

![The agent team and the one path to a change](../assets/04-team.png)

The team is three agents built with NVIDIA NeMo Agent Toolkit, running on NVIDIA Nemotron:

| Agent | Tools it holds | What it can do |
|---|---|---|
| **lead** | the other two agents | Ask the monitor, decide, hand the operator a proposal |
| **monitor** | the four BNK tools from challenge 2 | Read only |
| **operator** | `approved_quota_change` | Propose one Run:ai quota change, which you approve |

No agent holds `manage_org_unit` directly. `approved_quota_change` is the only thing that can call it, and
it runs Run:ai's dry run, shows you the diff and the BNK limit it implies, then sends `confirm=true` only if
you type exactly `yes`.

Have a look at the team's definition:

```bash,run
sed -n '/^functions:/,$p' /root/lab/agents/configs/factory-ops.yml
```

## Ask the team

tenant-b's load should still be running in **Terminal 2**. If it stopped, start it again and wait about a
minute before asking the agents, so the one-minute averages they read show the 429s:
`labctl load overload --tenant tenant-b --rps 35 --seconds 900`

## How to read what scrolls past

Each agent works in a loop. Three kinds of line matter:

| Line | Who wrote it | What it is |
|---|---|---|
| `Thought:` | Nemotron | The model's reasoning. It can be worded differently each run. |
| `Action:` and `Action Input:` | Nemotron | The tool the model chose and the arguments it picked. |
| `Tool's response:` | The MCP server | The real answer from BNK or Run:ai. This is data, not the model talking. |

So the numbers in `Tool's response:` come from BNK itself, and everything the agents conclude has to be
built on them.

## Ask the team

> **The model runs on NVIDIA's servers.** The agents call Nemotron on build.nvidia.com over the internet,
> so each step takes a few seconds, and the first one can take up to a minute while the model warms up.
> Please be patient. If the run stops with a timeout or a `500` error, NVIDIA's service had a hiccup, not
> the lab: run `labctl agents` again.

In **Terminal**:

```bash
labctl agents
```

Watch the agents work. You should see the lead hand a question to the monitor, the monitor call
`list_tenants` and `get_tenant_rejections`, and a `Tool's response:` for tenant-b with `"throttled":true`,
`"offeredRps"` near 35 and `"rateLimitRps":10`. Then the lead works out the quota. 20 req/s per GPU, so
35 req/s needs 1.75 GPU, which rounds up to 2 GPU (40 req/s) in steps of 0.5. The operator calls
`approved_quota_change`, and the run stops at a prompt like this:

```
Run:ai dry run for project tenant-b: GPU quota 0.5 -> 2 (BNK limit 10 -> 40 req/s). Approve this change? Type yes or no.
```

**Type `no`.**

You should see the tool answer `Declined by the operator. Project tenant-b stays at 0.5 GPU. Do not
retry.`, and the lead stop and report it without asking again.

The prompt isn't written by the model. `approved_quota_change` asked Run:ai's MCP server for a dry run, and
the `0.5 -> 2` in the prompt is Run:ai's own diff. The BNK limit next to it is that quota times 20.

## Proof from the systems, not from the agents

The agents say nothing changed. Check that with the systems themselves.

Run:ai's API, read through the same MCP tool the operator uses, with a dry run that changes nothing.
Then Run:ai's copy on the cluster, which is what the BNK controller watches. Then BNK:

```bash,run
labctl mcp runai call manage_org_unit '{"action":"update","orgType":"project","name":"tenant-b","spec":{"quota":[{"nodePoolName":"default","gpuDeserved":0.5}]},"dryRun":true}' 2>/dev/null \
  | jq -r '"Run:ai API      tenant-b quota: \(.before.quota[0].gpuDeserved) GPU"'
kubectl get projects.kai.resources tenant-b -o jsonpath='Run:ai cluster  tenant-b quota: {.spec.queues[0].resources.gpu.deserved} GPU{"\n"}'
labctl tenant show tenant-b | grep -i 'rate limit'
```

You should see 0.5 GPU in Run:ai's API, 0.5 GPU on the cluster, and 10 req/s at BNK. In **Grafana**,
tenant-b's 429s carry on.

## Replay the run

Open the **Topology** tab and scroll to **Last agent run**. It replays the run you just did from its log:
each tool call with its arguments, the question you were asked and your `no`. Every `labctl agents` run
replaces it.
