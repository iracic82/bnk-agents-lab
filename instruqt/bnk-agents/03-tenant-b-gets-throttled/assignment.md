---
slug: tenant-b-gets-throttled
type: challenge
title: tenant-b gets throttled
teaser: tenant-b sends more than its GPU share allows. BNK refuses the extra at the edge,
  before it ever reaches a GPU.
tabs:
- title: Terminal
  type: terminal
  hostname: control
- title: Terminal 2
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
timelimit: 1200
---
# tenant-b gets throttled

tenant-b's team just launched something popular. Their traffic jumps to 35 requests per second. Their
Run:ai quota is 0.5 GPU, so BNK lets 10 per second through.

Start that traffic in **Terminal 2** and leave it running. The next challenges need it.

```bash
labctl load overload --tenant tenant-b --rps 35 --seconds 900
```

You should see one line per second with about 10 `200`s and about 25 `429`s. The 429s come from BNK, at
the edge. Those requests never reach tenant-b's model server, so they don't take GPU time from anyone.

In **Grafana**, tenant-b's 429 rate climbs to around 25 per second within a minute. tenant-a and
dynamo carry on unchanged.

## What an agent would see

Back in **Terminal**, ask the BNK MCP server the same question the monitor agent will ask:

```bash,run
labctl mcp bnk call get_tenant_rejections '{"project":"tenant-b"}'
```

You should see `"throttled": true`, `"rateLimitRps": 10` and an `"offeredRps"` near 35. The numbers are
averaged over the last minute, so give them a minute after the load starts.

Two ways to fix this. Someone could edit BNK's rate limit by hand, but then BNK and Run:ai disagree about
tenant-b's share, and the next quota change in Run:ai would overwrite the edit. Or tenant-b gets more
GPU quota in Run:ai, and BNK follows by itself. That second one is what the agents will propose.

Keep the load running in Terminal 2 and move on.
