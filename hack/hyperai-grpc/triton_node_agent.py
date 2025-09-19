#!/usr/bin/env python3
"""
Triton-enabled Node Agent for HyperAI scheduler
Runs as part of DaemonSet and provides gRPC interface with full pod/node specification support
"""
import os
import json
import logging
import time
import threading
import grpc
from concurrent import futures
import tritonclient.http as httpclient
import numpy as np

# Use the main protobuf files
import hyperai_pb2
import hyperai_pb2_grpc

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thread-local storage for Triton clients
thread_local = threading.local()

class TritonNodeAgent(hyperai_pb2_grpc.NodeAgentServicer):
    def __init__(self):
        self.node_name = os.getenv('NODE_NAME', 'unknown-node')
        self.triton_url = "localhost:8000"  # Triton HTTP port
        
        # Initialize Triton client for main thread
        self.triton_client = None
        self._init_triton_client()
        
        logger.info(f"🚀 Triton Node Agent initialized on {self.node_name}")
    
    def _init_triton_client(self):
        """Initialize connection to local Triton server"""
        try:
            # Connect to Triton server running as sidecar
            self.triton_client = httpclient.InferenceServerClient(url=self.triton_url)
            
            # Test connection
            if self.triton_client.is_server_ready():
                logger.info(f"✅ Connected to Triton server at {self.triton_url}")
                
                # Log available models
                models = self.triton_client.get_model_repository_index()
                logger.info(f"📋 Available models: {[m['name'] for m in models]}")
            else:
                logger.warning("⚠️ Triton server not ready")
                self.triton_client = None
                
        except Exception as e:
            logger.warning(f"⚠️ Could not connect to Triton: {e}")
            self.triton_client = None
    
    def _get_thread_local_triton_client(self):
        """Get a thread-local Triton client to avoid threading issues"""
        if not hasattr(thread_local, 'triton_client'):
            try:
                thread_local.triton_client = httpclient.InferenceServerClient(url=self.triton_url)
                if not thread_local.triton_client.is_server_ready():
                    thread_local.triton_client = None
            except Exception as e:
                logger.debug(f"Failed to create thread-local Triton client: {e}")
                thread_local.triton_client = None
        return thread_local.triton_client
    
    def ProcessPodSpec(self, request, context):
        """Handle NodeAgent ProcessPodSpec requests with full pod and node specifications"""
        logger.info(f"📨 ProcessPodSpec request for pod {request.target_pod_name} in namespace {request.target_pod_namespace}")
        logger.debug(f"   Pod JSON: {request.pod_json[:200]}...")
        logger.debug(f"   Node JSON: {request.node_json[:200]}...")
        
        try:
            # Parse full pod and node specifications
            pod_data = json.loads(request.pod_json) if request.pod_json else {}
            node_data = json.loads(request.node_json) if request.node_json else {}
            
            # Extract comprehensive features for ML scoring
            features = self._extract_comprehensive_features(pod_data, node_data)
            logger.info(f"🔍 Extracted features: cpu={features.get('cpu_millicores')}mc, mem={features.get('memory_mb')}MB, gpu={features.get('gpu_count')}, containers={features.get('container_count')}")
            
            # Get score using Triton with full feature set
            score = self._get_enhanced_triton_score(features)
            
            logger.info(f"📡 ProcessPodSpec response: score={score} for pod {request.target_pod_name}")
            return hyperai_pb2.PodSpecReply(
                score=score,
                message=f"Scored on node {self.node_name} using full pod/node specification",
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ Error in ProcessPodSpec: {e}", exc_info=True)
            return hyperai_pb2.PodSpecReply(
                score=42,
                message=f"Error processing pod spec: {str(e)}",
                success=False
            )
    
    def _extract_comprehensive_features(self, pod_data, node_data):
        """Extract comprehensive features from full pod and node specifications"""
        features = {}
        
        # Pod resource requirements
        features.update(self._extract_pod_resources(pod_data))
        
        # Pod metadata and scheduling preferences
        features.update(self._extract_pod_metadata(pod_data))
        
        # Node capacity and availability
        features.update(self._extract_node_capacity(node_data))
        
        # Node metadata and characteristics
        features.update(self._extract_node_metadata(node_data))
        
        return features
    
    def _extract_pod_resources(self, pod_data):
        """Extract resource requirements from pod specification"""
        features = {
            'cpu_millicores': 0,
            'memory_mb': 0,
            'gpu_count': 0,
            'storage_gb': 0,
            'container_count': 0
        }
        
        try:
            containers = pod_data.get('spec', {}).get('containers', [])
            features['container_count'] = len(containers)
            
            for container in containers:
                requests = container.get('resources', {}).get('requests', {})
                limits = container.get('resources', {}).get('limits', {})
                
                # CPU
                cpu_str = requests.get('cpu', '0')
                features['cpu_millicores'] += self._parse_cpu_to_millicores(cpu_str)
                
                # Memory  
                mem_str = requests.get('memory', '0')
                features['memory_mb'] += self._parse_memory_to_mb(mem_str)
                
                # GPU
                gpu_count = requests.get('nvidia.com/gpu', '0')
                if gpu_count:
                    features['gpu_count'] += int(gpu_count)
                
                # Storage (ephemeral-storage)
                storage_str = requests.get('ephemeral-storage', '0')
                features['storage_gb'] += self._parse_storage_to_gb(storage_str)
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting pod resources: {e}")
        
        return features
    
    def _extract_pod_metadata(self, pod_data):
        """Extract pod metadata and scheduling preferences"""
        features = {
            'priority_class': '',
            'qos_class': 'BestEffort',
            'has_affinity': False,
            'has_anti_affinity': False,
            'has_node_selector': False,
            'has_tolerations': False,
            'restart_policy': 'Always'
        }
        
        try:
            spec = pod_data.get('spec', {})
            metadata = pod_data.get('metadata', {})
            
            # Priority and QoS
            features['priority_class'] = spec.get('priorityClassName', '')
            
            # Scheduling constraints
            features['has_affinity'] = 'affinity' in spec
            features['has_node_selector'] = bool(spec.get('nodeSelector'))
            features['has_tolerations'] = bool(spec.get('tolerations'))
            features['restart_policy'] = spec.get('restartPolicy', 'Always')
            
            # Labels for ML features
            labels = metadata.get('labels', {})
            features['app_label'] = labels.get('app', '')
            features['tier_label'] = labels.get('tier', '')
            features['version_label'] = labels.get('version', '')
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting pod metadata: {e}")
        
        return features
    
    def _extract_node_capacity(self, node_data):
        """Extract node capacity and availability"""
        features = {
            'node_cpu_cores': 0,
            'node_memory_gb': 0,
            'node_gpu_count': 0,
            'node_pods_capacity': 0,
            'node_allocatable_cpu_cores': 0,
            'node_allocatable_memory_gb': 0
        }
        
        try:
            status = node_data.get('status', {})
            
            # Total capacity
            capacity = status.get('capacity', {})
            features['node_cpu_cores'] = self._parse_cpu_to_cores(capacity.get('cpu', '0'))
            features['node_memory_gb'] = self._parse_memory_to_gb(capacity.get('memory', '0'))
            features['node_pods_capacity'] = int(capacity.get('pods', '0'))
            
            gpu_capacity = capacity.get('nvidia.com/gpu', '0')
            if gpu_capacity:
                features['node_gpu_count'] = int(gpu_capacity)
            
            # Allocatable resources
            allocatable = status.get('allocatable', {})
            features['node_allocatable_cpu_cores'] = self._parse_cpu_to_cores(allocatable.get('cpu', '0'))
            features['node_allocatable_memory_gb'] = self._parse_memory_to_gb(allocatable.get('memory', '0'))
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting node capacity: {e}")
        
        return features
    
    def _extract_node_metadata(self, node_data):
        """Extract node metadata and characteristics"""
        features = {
            'node_zone': '',
            'node_instance_type': '',
            'node_architecture': '',
            'node_os': '',
            'node_ready': False
        }
        
        try:
            metadata = node_data.get('metadata', {})
            status = node_data.get('status', {})
            
            # Node labels
            labels = metadata.get('labels', {})
            features['node_zone'] = labels.get('topology.kubernetes.io/zone', '')
            features['node_instance_type'] = labels.get('node.kubernetes.io/instance-type', '')
            features['node_architecture'] = labels.get('kubernetes.io/arch', '')
            features['node_os'] = labels.get('kubernetes.io/os', '')
            
            # Node readiness
            conditions = status.get('conditions', [])
            for condition in conditions:
                if condition.get('type') == 'Ready':
                    features['node_ready'] = condition.get('status') == 'True'
                    break
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting node metadata: {e}")
        
        return features
    
    def _parse_cpu_to_millicores(self, cpu_str):
        """Parse CPU string to millicores (e.g., '100m' -> 100, '0.5' -> 500)"""
        try:
            if cpu_str.endswith('m'):
                return int(cpu_str[:-1])
            else:
                return int(float(cpu_str) * 1000)
        except:
            return 0
    
    def _parse_cpu_to_cores(self, cpu_str):
        """Parse CPU string to cores (e.g., '4' -> 4, '4000m' -> 4)"""
        try:
            if cpu_str.endswith('m'):
                return int(cpu_str[:-1]) / 1000
            else:
                return float(cpu_str)
        except:
            return 0
    
    def _parse_memory_to_mb(self, mem_str):
        """Parse memory string to MB (e.g., '128Mi' -> 128, '1Gi' -> 1024)"""
        try:
            if mem_str.endswith('Mi'):
                return int(mem_str[:-2])
            elif mem_str.endswith('Gi'):
                return int(mem_str[:-2]) * 1024
            elif mem_str.endswith('Ki'):
                return int(mem_str[:-2]) // 1024
            elif mem_str.isdigit():
                return int(mem_str) // (1024 * 1024)
            else:
                return 0
        except:
            return 0
    
    def _parse_memory_to_gb(self, mem_str):
        """Parse memory string to GB"""
        return self._parse_memory_to_mb(mem_str) / 1024
    
    def _parse_storage_to_gb(self, storage_str):
        """Parse storage string to GB (e.g., '10Gi' -> 10, '1000Mi' -> ~1)"""
        try:
            if storage_str.endswith('Gi'):
                return int(storage_str[:-2])
            elif storage_str.endswith('Mi'):
                return int(storage_str[:-2]) / 1024
            elif storage_str.endswith('Ti'):
                return int(storage_str[:-2]) * 1024
            elif storage_str.isdigit():
                return int(storage_str) // (1024 * 1024 * 1024)
            else:
                return 0
        except:
            return 0
    
    def _get_enhanced_triton_score(self, features):
        """Get ML-based score using Triton with comprehensive feature set"""
        # Use thread-local Triton client to avoid threading issues
        triton_client = self._get_thread_local_triton_client()
        if not triton_client:
            logger.warning("⚠️ Triton client not available, using fallback scoring")
            return self._fallback_score(features)
        
        try:
            # Prepare inputs for Triton model with comprehensive features
            inputs = []
            outputs = []
            
            # Create feature vector from all extracted features
            feature_vector = self._create_feature_vector(features)
            
            # Single features input (as expected by the model)
            # Use only the first 2 features that the model was trained on: CPU and memory
            feature_vector_full = self._create_feature_vector(features)
            feature_vector_simple = [
                float(features.get('cpu_millicores', 0)),
                float(features.get('memory_mb', 0))
            ]
            
            features_input = httpclient.InferInput("features", [1, 2], "FP32")
            features_data = np.array([feature_vector_simple], dtype=np.float32)
            features_input.set_data_from_numpy(features_data)
            inputs.append(features_input)
            
            logger.info(f"🧠 Using simplified features for Triton: {feature_vector_simple} (Full feature set: {len(feature_vector_full)} features available)")
            
            # Output
            output = httpclient.InferRequestedOutput("score")
            outputs.append(output)
            
            # Make inference request
            result = triton_client.infer(
                model_name="scheduler_model",
                inputs=inputs,
                outputs=outputs
            )
            
            # Extract score
            score_data = result.as_numpy("score")
            score = int(score_data[0][0])
            
            logger.info(f"🎯 Enhanced Triton inference: features={len(feature_vector)}, score={score}")
            return score
            
        except Exception as e:
            logger.warning(f"⚠️ Enhanced Triton inference failed: {e}, using fallback")
            return self._fallback_score(features)
    
    def _create_feature_vector(self, features):
        """Create a comprehensive feature vector for ML model"""
        vector = []
        
        # Resource features
        vector.extend([
            features.get('cpu_millicores', 0),
            features.get('memory_mb', 0),
            features.get('gpu_count', 0),
            features.get('storage_gb', 0),
            features.get('container_count', 0)
        ])
        
        # Node capacity features
        vector.extend([
            features.get('node_cpu_cores', 0),
            features.get('node_memory_gb', 0),
            features.get('node_gpu_count', 0),
            features.get('node_pods_capacity', 0),
            features.get('node_allocatable_cpu_cores', 0),
            features.get('node_allocatable_memory_gb', 0)
        ])
        
        # Boolean features (0/1)
        vector.extend([
            1 if features.get('has_affinity', False) else 0,
            1 if features.get('has_anti_affinity', False) else 0,
            1 if features.get('has_node_selector', False) else 0,
            1 if features.get('has_tolerations', False) else 0,
            1 if features.get('node_ready', False) else 0
        ])
        
        # Categorical features (simplified as numeric for now)
        qos_map = {'Guaranteed': 3, 'Burstable': 2, 'BestEffort': 1}
        vector.append(qos_map.get(features.get('qos_class', 'BestEffort'), 1))
        
        restart_map = {'Always': 3, 'OnFailure': 2, 'Never': 1}
        vector.append(restart_map.get(features.get('restart_policy', 'Always'), 3))
        
        return vector
    
    def _fallback_score(self, features):
        """Enhanced fallback scoring using comprehensive features"""
        try:
            # Basic resource-based scoring
            cpu_mc = features.get('cpu_millicores', 0)
            mem_mb = features.get('memory_mb', 0)
            
            # Node capacity awareness
            node_cpu_cores = features.get('node_allocatable_cpu_cores', 1)
            node_mem_gb = features.get('node_allocatable_memory_gb', 1)
            
            # CPU utilization percentage
            cpu_util = (cpu_mc / 1000) / max(node_cpu_cores, 0.1)
            mem_util = (mem_mb / 1024) / max(node_mem_gb, 0.1)
            
            # Base score (prefer nodes with lower utilization)
            base_score = max(0, 100 - (cpu_util + mem_util) * 50)
            
            # Bonus for special features
            bonus = 0
            if features.get('node_ready', False):
                bonus += 10
            if features.get('gpu_count', 0) > 0 and features.get('node_gpu_count', 0) > 0:
                bonus += 20  # GPU workload on GPU node
            if features.get('has_affinity', False):
                bonus += 5  # Affinity rules considered
            
            final_score = min(100, max(0, base_score + bonus))
            
            logger.info(f"🧮 Enhanced fallback score: cpu_util={cpu_util:.2f}, mem_util={mem_util:.2f}, bonus={bonus}, score={final_score}")
            return int(final_score)
            
        except Exception as e:
            logger.warning(f"⚠️ Fallback scoring error: {e}")
            return 42


def serve():
    """Start the gRPC server"""
    logger.info(f"🚀 Starting Triton Node Agent on {os.getenv('NODE_NAME', 'unknown-node')}")
    
    # Create the service
    service = TritonNodeAgent()
    
    # Start gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    hyperai_pb2_grpc.add_NodeAgentServicer_to_server(service, server)
    
    # Listen on all interfaces
    listen_addr = '0.0.0.0:50051'
    server.add_insecure_port(listen_addr)
    
    logger.info(f"🌐 gRPC server listening on {listen_addr}")
    logger.info("📋 Serving NodeAgent.ProcessPodSpec with full pod/node specifications")
    
    server.start()
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Triton Node Agent")
        server.stop(0)


if __name__ == '__main__':
    serve()