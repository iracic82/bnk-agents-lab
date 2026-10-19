---
slug: dynamo-tenant
type: challenge
title: A Dynamo tenant, to BNK and the agents alike
teaser: NVIDIA Dynamo serves one tenant. BNK picks its worker from Dynamo's own KV-cache events,
  and the agents watch it like any other tenant.
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
difficulty: intermediate
timelimit: 1800
---
# A Dynamo tenant, to BNK and the agents alike

The third tenant, `dynamo`, doesn't use vLLM. It runs NVIDIA Dynamo: a frontend and two workers, each
keeping a KV cache of the prompts it has seen. The workers here are Dynamo's **Mocker**, which registers
like a real worker, keeps a simulated KV cache and publishes real KV events, but loads no model weights.

For this tenant BNK's Endpoint Picker runs in Dynamo mode. It listens to the workers' KV-cache events on
NATS and sends each request to the worker that already holds its prompt.

## The Dynamo side

```bash,run
NS=$(kubectl get projects.kai.resources dynamo -o jsonpath='{.status.namespace}')
kubectl -n $NS get pods -o custom-columns='POD:.metadata.name,NODE:.spec.nodeName,SCHEDULER:.spec.schedulerName'
kubectl -n $NS get f5-epps model-pool-epp -o jsonpath='{.spec.engine}{"\n"}'
```

You should see the Dynamo pods scheduled by `runai-scheduler`, so Run:ai placed them, and `dynamo` as the
Endpoint Picker's engine.

## BNK picks the worker

```bash,run
VIP=$(kubectl get gateway -n f5-bnk dynamo -o jsonpath='{.status.addresses[0].value}')
MODEL=$(curl -s http://$VIP:8000/v1/models | jq -r '.data[0].id')
for i in 1 2 3; do
  curl -si http://$VIP:8000/v1/chat/completions -H 'Content-Type: application/json' -d "{
    \"model\": \"$MODEL\", \"max_tokens\": 8, \"nvext\": {\"extra_fields\": [\"worker_id\"]},
    \"messages\": [{\"role\": \"user\", \"content\": \"Same prompt every time, so the same KV cache.\"}]}" \
  | grep -iE '^HTTP|x-bnk-tenant|decode_worker_id' | sed -E 's/.*("decode_worker_id":[0-9]+).*/\1/'
done
```

You should see `HTTP/1.1 200`, `X-BNK-Tenant: dynamo` and a `decode_worker_id` on each request. That ID
came from BNK: the picker chose the worker and wrote its ID into the request, and Dynamo's frontend served
exactly that worker.

## The agents see a tenant like any other

```bash
labctl agents "How is the dynamo tenant doing? Report its limit, traffic and any refusals."
```

You should see the monitor call the same BNK tools it used for tenant-b, with `dynamo` as the project, and
report a 20 req/s limit (1 GPU) and no refusals. The agents never need to know which engine serves a
tenant. BNK gives every tenant the same front door and the same tools. The agents can read dynamo but not
change it: it isn't on `approved_quota_change`'s allowed list.
