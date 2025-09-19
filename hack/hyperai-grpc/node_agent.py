#!/usr/bin/env python3
"""
HyperAI Node Agent - Runs as DaemonSet on each Kubernetes node
Receives gRPC requests from central HyperAI server and communicates with target pods
"""

import grpc
import json
import time
import logging
import socket
from concurrent import futures
from kubernetes import client, config
import hyperai_pb2
import hyperai_pb2_grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeAgentServicer(hyperai_pb2_grpc.NodeAgentServicer):
    def __init__(self):
        """Initialize the node agent with Kubernetes client"""
        try:
            # Try in-cluster config first (when running in pod)
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration")
        except Exception as e:
            try:
                # Fallback to local kubeconfig for development
                config.load_kube_config()
                logger.info("Loaded local Kubernetes configuration")
            except Exception as e2:
                logger.error(f"Failed to load Kubernetes config: {e2}")
                raise

        self.k8s_client = client.CoreV1Api()
        self.node_name = self._get_node_name()
        logger.info(f"Node Agent initialized for node: {self.node_name}")

    def _get_node_name(self):
        """Get the current node name from environment or hostname"""
        import os
        # In DaemonSet, node name is typically provided via environment variable
        node_name = os.environ.get('NODE_NAME')
        if not node_name:
            # Fallback to hostname
            node_name = socket.gethostname()
        return node_name

    def ProcessPodSpec(self, request, context):
        """
        Process pod specification request from central HyperAI server
        Returns constant score directly (placeholder for future Triton integration)
        """
        logger.info(f"📥 Received PodSpec request for pod: {request.target_pod_name}")
        
        try:
            # Parse the pod and node JSON
            pod_data = json.loads(request.pod_json) if request.pod_json else {}
            node_data = json.loads(request.node_json) if request.node_json else {}
            
            logger.info(f"Processing request for pod '{request.target_pod_name}' in namespace '{request.target_pod_namespace}'")
            logger.info(f"Pod metadata: {pod_data.get('metadata', {}).get('name', 'unknown')}")
            logger.info(f"Node name: {node_data.get('metadata', {}).get('name', 'unknown')}")

            # Check if pod exists and get basic info (optional validation)
            pod_info = self._get_pod_info(request.target_pod_name, request.target_pod_namespace)
            
            if not pod_info:
                logger.warning(f"Pod {request.target_pod_name} not found in namespace {request.target_pod_namespace}")
                constant_score = 30  # Lower score for non-existent pod
            elif pod_info.get('node_name') != self.node_name:
                logger.warning(f"Pod {request.target_pod_name} is not on this node ({self.node_name})")
                constant_score = 20  # Lower score for pod on different node
            else:
                # Pod exists and is on correct node - return constant placeholder score
                # This is where future Triton inference server integration will go
                constant_score = 85  # Constant placeholder score
                logger.info(f"✅ Pod validated on correct node, returning constant score: {constant_score}")

            logger.info(f"✅ Successfully processed PodSpec request, returning score: {constant_score}")
            
            return hyperai_pb2.PodSpecReply(
                score=constant_score,
                message=f"Processed by node agent on {self.node_name} (constant placeholder)",
                success=True
            )

        except Exception as e:
            logger.error(f"❌ Error processing PodSpec request: {e}")
            return hyperai_pb2.PodSpecReply(
                score=50,  # Fallback score
                message=f"Error: {str(e)}",
                success=False
            )

    def _get_pod_info(self, pod_name, pod_namespace):
        """Get pod information from Kubernetes API"""
        try:
            pod = self.k8s_client.read_namespaced_pod(name=pod_name, namespace=pod_namespace)
            return {
                'pod_ip': pod.status.pod_ip,
                'node_name': pod.spec.node_name,
                'phase': pod.status.phase
            }
        except client.exceptions.ApiException as e:
            if e.status == 404:
                logger.warning(f"Pod {pod_name} not found in namespace {pod_namespace}")
            else:
                logger.error(f"Kubernetes API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting pod info: {e}")
            return None

def serve():
    """Start the node agent gRPC server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    
    # Add the node agent servicer
    hyperai_pb2_grpc.add_NodeAgentServicer_to_server(NodeAgentServicer(), server)
    
    # Listen on all interfaces, port 50051
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    server.start()
    
    logger.info(f"🚀 HyperAI Node Agent started on {listen_addr}")
    
    try:
        while True:
            time.sleep(86400)  # Sleep for a day
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Node Agent")
        server.stop(0)

if __name__ == '__main__':
    serve()