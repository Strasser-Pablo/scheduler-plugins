#!/usr/bin/env python3

import grpc
import hyperai_pb2
import hyperai_pb2_grpc

def test_client():
    # Connect to the server
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = hyperai_pb2_grpc.HyperAIStub(channel)
        
        # Create a test request
        request = hyperai_pb2.ScoreRequest(
            pod_name="test-pod",
            node_name="test-node"
        )
        
        # Call the GetScore method
        try:
            response = stub.GetScore(request)
            print(f"Received score: {response.score}")
            return response.score
        except grpc.RpcError as e:
            print(f"gRPC error: {e}")
            return None

if __name__ == '__main__':
    score = test_client()
    if score == 88:
        print("✅ Python gRPC server test PASSED - received expected gRPC score of 88")
    else:
        print(f"❌ Python gRPC server test FAILED - expected 88, got {score}")