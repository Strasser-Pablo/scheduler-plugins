import grpc
from concurrent import futures
import time
import json
import logging
import socket

import hyperai_pb2
import hyperai_pb2_grpc
import threading
import uuid
import queue

# Kubernetes client for node discovery (optional)
try:
    from kubernetes import client, config

    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    logging.warning(
        "Kubernetes client not available - using simple hostname resolution"
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HyperAIServicer(hyperai_pb2_grpc.HyperAIServicer):
    def __init__(self):
        """Initialize the central HyperAI server with optional Kubernetes client"""
        self.k8s_client = None
        # Session management: node_name -> AgentSession
        self._sessions = {}
        self._sessions_lock = threading.Lock()
        if KUBERNETES_AVAILABLE:
            try:
                # Try in-cluster config first
                config.load_incluster_config()
                self.k8s_client = client.CoreV1Api()
                logger.info(
                    "Loaded in-cluster Kubernetes configuration for node discovery"
                )
            except Exception:
                try:
                    # Fallback to local kubeconfig
                    config.load_kube_config()
                    self.k8s_client = client.CoreV1Api()
                    logger.info(
                        "Loaded local Kubernetes configuration for node discovery"
                    )
                except Exception as e:
                    logger.warning(f"Could not load Kubernetes config: {e}")

    def GetScore(self, request, context):
        """
        Central HyperAI server - receives requests from scheduler
        Forwards to appropriate node agent via streaming session
        """
        logger.info(f"📡 gRPC request received from scheduler")
        logger.info(
            f"  pod_json: {request.pod_json[:200]}{'...' if len(request.pod_json) > 200 else ''}"
        )
        logger.info(
            f"  node_json: {request.node_json[:200]}{'...' if len(request.node_json) > 200 else ''}"
        )

        try:
            # Parse pod and node information
            pod_data = json.loads(request.pod_json) if request.pod_json else {}
            node_data = json.loads(request.node_json) if request.node_json else {}

            pod_name = pod_data.get("metadata", {}).get("name", "unknown-pod")
            pod_namespace = pod_data.get("metadata", {}).get("namespace", "default")
            node_name = node_data.get("metadata", {}).get("name", "unknown-node")

            logger.info(f"Processing request for pod: {pod_name} on node: {node_name}")

            # Try to forward to node agent via streaming session
            node_score = self._forward_over_stream(
                node_name, request.pod_json, request.node_json
            )

            if node_score is not None:
                final_score = node_score
                logger.info(f"✅ Received score from node agent: {final_score}")
            else:
                # Fallback when node agent is unavailable
                final_score = 0
                logger.info(
                    f"⚠️  Using fallback score (node agent unavailable): {final_score}"
                )

            logger.info(f"📡 gRPC response: score={final_score}")
            return hyperai_pb2.ScoreReply(score=final_score)

        except Exception as e:
            logger.error(f"❌ Error processing score request: {e}")
            # Return fallback score on error
            fallback_score = 0
            logger.info(f"📡 gRPC response (error fallback): score={fallback_score}")
            return hyperai_pb2.ScoreReply(score=fallback_score)

    def _forward_over_stream(self, node_name: str, pod_json: str, node_json: str):
        """Send a score request over the agent's streaming session and await response."""
        session = self._get_session(node_name)
        if not session:
            logger.warning(f"No active session for node {node_name}")
            return None

        request_id = str(uuid.uuid4())
        resp_q = session.register_waiter(request_id)
        try:
            msg = hyperai_pb2.ServerMessage(
                score_request=hyperai_pb2.ServerScoreRequest(
                    request_id=request_id, pod_json=pod_json, node_json=node_json
                )
            )
            session.send(msg)
        except Exception as e:
            logger.warning(f"Failed sending request to node {node_name}: {e}")
            session.unregister_waiter(request_id)
            return None

        try:
            # Wait up to 5 seconds for agent response
            response = resp_q.get(timeout=5.0)
            if response.success:
                return response.score
            logger.warning(f"Agent reported failure: {response.message}")
            return None
        except Exception:
            logger.warning(f"Timeout waiting for response from node {node_name}")
            return None
        finally:
            session.unregister_waiter(request_id)

    # ===== Streaming session management =====
    def AgentConnect(self, request_iterator, context):
        """Bidirectional streaming RPC for agents to connect/register and handle work."""
        logger.info("🔌 Agent connected (awaiting hello)")

        # We can't push directly; implement this RPC as a generator that
        # yields messages from a queue populated by session.send().
        out_queue = queue.Queue()

        class Session:
            def __init__(self, node_name: str):
                self.node_name = node_name
                self.waiters = {}
                self.waiters_lock = threading.Lock()
                self.last_heartbeat = time.time()

            def send(self, msg: hyperai_pb2.ServerMessage):
                out_queue.put(msg)

            def register_waiter(self, request_id: str):
                q = queue.Queue(maxsize=1)
                with self.waiters_lock:
                    self.waiters[request_id] = q
                return q

            def unregister_waiter(self, request_id: str):
                with self.waiters_lock:
                    self.waiters.pop(request_id, None)

            def deliver(self, resp: hyperai_pb2.AgentScoreResponse):
                with self.waiters_lock:
                    q = self.waiters.get(resp.request_id)
                if q:
                    try:
                        q.put_nowait(resp)
                    except Exception:
                        pass

        session = None

        def reader_loop():
            nonlocal session
            try:
                for msg in request_iterator:
                    if msg.WhichOneof("msg") == "hello":
                        node_name = msg.hello.node_name or "unknown-node"
                        session = Session(node_name)
                        with self._sessions_lock:
                            self._sessions[node_name] = session
                        logger.info(f"🤝 Registered agent session for node {node_name}")
                    elif msg.WhichOneof("msg") == "heartbeat":
                        if session:
                            session.last_heartbeat = time.time()
                    elif msg.WhichOneof("msg") == "score_response":
                        if session:
                            session.deliver(msg.score_response)
            except Exception as e:
                # Log RPC details if available
                code = getattr(context, "code", lambda: None)()
                details = getattr(context, "details", lambda: None)()
                logger.info(f"Agent stream ended: {e} code={code} details={details}")
            finally:
                if session:
                    with self._sessions_lock:
                        self._sessions.pop(session.node_name, None)
                    logger.info(f"🛑 Agent session closed for node {session.node_name}")

        reader_thread = threading.Thread(target=reader_loop, daemon=True)
        reader_thread.start()

        # Writer loop: yield messages from out_queue to the agent until stream ends.
        # Also periodically send a lightweight keepalive control message so the stream
        # carries server->client traffic and avoids idle timeouts in intermediaries.
        try:
            last_keepalive = time.time()
            while True:
                try:
                    # Wait up to 10s for a real message to send
                    msg = out_queue.get(timeout=10.0)
                    yield msg
                except queue.Empty:
                    # Periodic keepalive message
                    ka = hyperai_pb2.ServerMessage(
                        control=hyperai_pb2.ServerControl(
                            type="keepalive", payload="ping"
                        )
                    )
                    yield ka
                    now = time.time()
                    logger.debug(
                        f"Sent server keepalive after {int(now - last_keepalive)}s"
                    )
                    last_keepalive = now
        except Exception as e:
            logger.info(f"Agent writer loop ending: {e}")

    def _get_session(self, node_name: str):
        with self._sessions_lock:
            return self._sessions.get(node_name)


def serve():
    # Configure server-side keepalive and HTTP/2 ping policy to avoid disconnects
    server_opts = [
        ("grpc.keepalive_time_ms", 20000),  # send server keepalive every 20s
        ("grpc.keepalive_timeout_ms", 5000),  # wait 5s for ack
        ("grpc.http2.max_pings_without_data", 0),  # allow pings without data
        (
            "grpc.keepalive_permit_without_calls",
            1,
        ),  # allow server pings with no active calls
        (
            "grpc.http2.min_time_between_pings_ms",
            10000,
        ),  # min time between server pings
        ("grpc.http2.min_ping_interval_without_data_ms", 10000),
    ]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4), options=server_opts)
    hyperai_pb2_grpc.add_HyperAIServicer_to_server(HyperAIServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    logger.info("🚀 HyperAI Central gRPC server started on port 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Central gRPC server")
        server.stop(0)


if __name__ == "__main__":
    serve()
