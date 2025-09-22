# HyperAI Agent-Initiated Streaming Design

This document proposes and specifies an agent-initiated, bidirectional gRPC streaming design for the HyperAI node agent and central service. The new design removes the need for hostNetwork and node IP resolution by having node agents connect out to a central service and maintain a long-lived stream for registration, heartbeats, and scoring requests.

## Goals
- Agents initiate outbound connections to the central service (ClusterIP), no inbound ports on nodes.
- Remove hostNetwork and node IP/hostname tricks entirely.
- Keep scheduler-side RPC unchanged: `HyperAI.GetScore(ScoreRequest) -> ScoreReply` with full Pod/Node JSON.
- Provide robust correlation, timeouts, and fallback.
- Enable future auth (mTLS or SA token) and observability.

## Non-Goals
- Backward compatibility with the direct NodeAgent RPC (we will remove it).
- Multi-instance central coordination (initially single replica for simplicity).

## High-Level Architecture
- Central HyperAI service runs as a Deployment behind a ClusterIP Service (e.g., `hyperai-central.scheduler-plugins.svc:50051`).
- Scheduler plugin points to the central service DNS. `GetScore` continues to work unchanged.
- Node agents (DaemonSet) open a bidirectional stream to central using new `AgentConnect` RPC. Over the stream:
  - Agent sends `AgentHello` (registration) and periodic `AgentHeartbeat`.
  - Central sends `ServerScoreRequest` with `request_id`, `pod_json`, `node_json`.
  - Agent replies with `AgentScoreResponse` matching `request_id`.

## gRPC API
- Keep:
  - `service HyperAI { rpc GetScore(ScoreRequest) returns (ScoreReply); rpc AgentConnect(stream AgentMessage) returns (stream ServerMessage); }`
- Remove:
  - `service NodeAgent` and `ProcessPodSpec` RPC.

### Messages
- `ScoreRequest { string pod_json; string node_json; }`
- `ScoreReply { int64 score; }`
- `AgentMessage { oneof msg { AgentHello hello; AgentHeartbeat heartbeat; AgentScoreResponse score_response; } }`
- `ServerMessage { oneof msg { ServerScoreRequest score_request; ServerControl control; } }`
- `AgentHello { string node_name; string agent_version; repeated string capabilities; map<string,string> labels; string model; }`
- `AgentHeartbeat { int64 ts; }`
- `ServerScoreRequest { string request_id; string pod_json; string node_json; }`
- `AgentScoreResponse { string request_id; int64 score; bool success; string message; }`
- `ServerControl { string type; string payload; } // reserved for future controls`

## Central Server Behavior
- Maintain `map[nodeName]Session` where `Session` holds stream send/recv, lastHeartbeat, and a `map[requestID]chan AgentScoreResponse`.
- On `AgentConnect`: expect `AgentHello` first, then register session. Start a goroutine to read agent messages:
  - On `heartbeat`, update lastHeartbeat.
  - On `score_response`, find waiter by `request_id` and deliver result.
- On `GetScore`:
  - Extract `node_name` from `node_json`.
  - If session exists and healthy: create `request_id`, send `ServerScoreRequest`, wait for response with timeout (default 5s). Return `ScoreReply` with `score` on success or fallback (0) on timeout/missing session.

## Node Agent Behavior
- On start: dial `CENTRAL_ADDR` (e.g., `hyperai-central.scheduler-plugins.svc.cluster.local:50051`).
- Open `AgentConnect` stream. Send `AgentHello` with `NODE_NAME`, agent version, and optional metadata. Start periodic `AgentHeartbeat`.
- Read `ServerScoreRequest` messages, for each:
  - Run existing scoring logic (Triton inference via `localhost:8000` HTTP).
  - Send `AgentScoreResponse` with `request_id`, `score`, `success`, `message`.
- Reconnect with backoff on failure. No inbound server/ports required.

## Security
- Phase 1: plaintext for internal POC.
- Phase 2: mTLS or ServiceAccount token auth via TokenReview, plus NetworkPolicies.

## Availability & Scaling
- Phase 1: single central instance. Scheduler must target this instance’s Service.
- Later: leader election or routing layer to support multiple instances.

## Kubernetes Changes
- New Deployment + Service for central (if not already standalone).
- Update scheduler config to use central Service DNS.
- Update DaemonSet: remove `hostNetwork: true`, remove exposed gRPC port, add env `CENTRAL_ADDR` and `NODE_NAME`.

## Migration
- No backward compatibility required. Replace NodeAgent RPC with streaming entirely.
- Verify with local smoke test, then update manifests.

## Observability
- Central: metrics for `connected_agents`, `heartbeats_missed`, `score_latency_ms`, `timeouts`.
- Structured logs for request lifecycle and errors.

## Next Steps
1. Update `hack/hyperai-grpc/hyperai.proto` with streaming RPC + messages; remove `NodeAgent` service.
2. Regenerate Python and Go stubs.
3. Implement central streaming in `server.py` (session map, request routing, timeouts).
4. Implement agent streaming in `triton_node_agent.py` (client loop, heartbeat, inference handler).
5. Adjust Dockerfile/manifests to drop hostNetwork (follow-up PR can add manifests).
6. Local E2E smoke: run central and agent locally; run `test_client.py` and verify scoring path.
