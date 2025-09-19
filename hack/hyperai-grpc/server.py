import grpc
from concurrent import futures
import time

import hyperai_pb2
import hyperai_pb2_grpc

class HyperAIServicer(hyperai_pb2_grpc.HyperAIServicer):
    def GetScore(self, request, context):
        # Return a different score to distinguish from fallback
        print(f"📡 gRPC request received: pod={request.pod_name}, node={request.node_name}")
        grpc_score = 88  # Different from fallback score (42) to prove gRPC is working
        print(f"📡 gRPC response: score={grpc_score}")
        return hyperai_pb2.ScoreReply(score=grpc_score)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    hyperai_pb2_grpc.add_HyperAIServicer_to_server(HyperAIServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("HyperAI gRPC server started on port 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
