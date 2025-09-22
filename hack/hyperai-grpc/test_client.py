#!/usr/bin/env python3

import grpc
import hyperai_pb2
import hyperai_pb2_grpc


def test_client():
    # Connect to the server
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = hyperai_pb2_grpc.HyperAIStub(channel)

        # Create a test request with full pod and node JSON
        import json

        pod_obj = {
            "metadata": {"name": "test-pod", "namespace": "default"},
            "spec": {"containers": [{"name": "c", "image": "busybox"}]},
        }
        node_obj = {
            "metadata": {"name": "test-node"},
            "status": {"capacity": {"cpu": "4", "memory": "8Gi"}},
        }
        request = hyperai_pb2.ScoreRequest(
            pod_json=json.dumps(pod_obj), node_json=json.dumps(node_obj)
        )

        # Call the GetScore method
        try:
            response = stub.GetScore(request)
            print(f"Received score: {response.score}")
            return response.score
        except grpc.RpcError as e:
            print(f"gRPC error: {e}")
            return None


if __name__ == "__main__":
    score = test_client()
    if score == 0:
        print(
            "✅ Python gRPC server test PASSED - received expected fallback gRPC score of 0"
        )
    else:
        print(f"❌ Python gRPC server test FAILED - expected 0, got {score}")
