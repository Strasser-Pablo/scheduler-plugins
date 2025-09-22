import grpc
from concurrent import futures
import time
import json
import logging
import socket

import hyperai_pb2
import hyperai_pb2_grpc

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
        Forwards to appropriate node agent for distributed processing
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

            # Try to forward to node agent
            node_score = self._call_node_agent(
                node_name, request.pod_json, request.node_json, pod_name, pod_namespace
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

    def _call_node_agent(self, node_name, pod_json, node_json, pod_name, pod_namespace):
        """
        Call the node agent on the specified node via gRPC
        Uses node IP since DaemonSet runs with hostNetwork: true
        """
        try:
            # Get node IP for direct connection (DaemonSet uses hostNetwork)
            node_ip = self._get_node_ip(node_name)
            if not node_ip:
                logger.warning(f"Could not resolve IP for node: {node_name}")
                return None

            # Connect directly to node IP (DaemonSet uses hostNetwork: true)
            node_agent_address = f"{node_ip}:50051"

            logger.info(
                f"Attempting to connect to node agent at: {node_agent_address} (node: {node_name})"
            )

            with grpc.insecure_channel(node_agent_address) as channel:
                stub = hyperai_pb2_grpc.NodeAgentStub(channel)

                request = hyperai_pb2.PodSpecRequest(
                    pod_json=pod_json,
                    node_json=node_json,
                    target_pod_name=pod_name,
                    target_pod_namespace=pod_namespace,
                )

                # Timeout for node agent communication
                response = stub.ProcessPodSpec(request, timeout=5.0)

                if response.success:
                    logger.info(
                        f"✅ Node agent responded successfully: {response.message}"
                    )
                    return response.score
                else:
                    logger.warning(f"⚠️  Node agent failed: {response.message}")
                    return None

        except grpc.RpcError as e:
            logger.debug(f"Node agent not available at {node_agent_address}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Error calling node agent: {e}")
            return None

    def _get_node_ip(self, node_name):
        """
        Get the IP address of a node using Kubernetes API or hostname resolution
        """
        try:
            # Method 1: Use Kubernetes API (preferred)
            if self.k8s_client:
                try:
                    node = self.k8s_client.read_node(name=node_name)
                    # Get internal IP address
                    for address in node.status.addresses:
                        if address.type == "InternalIP":
                            logger.info(
                                f"Found node {node_name} at IP: {address.address}"
                            )
                            return address.address
                    logger.warning(f"No InternalIP found for node: {node_name}")
                except client.exceptions.ApiException as e:
                    logger.warning(
                        f"Could not find node {node_name} in Kubernetes API: {e}"
                    )

            # Method 2: Hostname resolution fallback
            # For local kind testing
            if node_name == "kind-control-plane":
                return "127.0.0.1"  # localhost for kind

            # Try hostname resolution
            try:
                node_ip = socket.gethostbyname(node_name)
                logger.info(f"Resolved {node_name} to {node_ip} via hostname")
                return node_ip
            except socket.gaierror:
                logger.warning(f"Could not resolve hostname: {node_name}")
                return None

        except Exception as e:
            logger.error(f"Error resolving node IP for {node_name}: {e}")
            return None


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
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
