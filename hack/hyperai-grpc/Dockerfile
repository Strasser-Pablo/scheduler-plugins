FROM python:3.11-slim

WORKDIR /app

# Install grpcio and grpcio-tools
RUN pip install grpcio==1.75.0 grpcio-tools==1.75.0

# Copy the gRPC files
COPY hyperai.proto .
COPY hyperai_pb2.py .
COPY hyperai_pb2_grpc.py .
COPY server.py .

# Generate the gRPC code if not already present
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. hyperai.proto || true

EXPOSE 50051

CMD ["python", "server.py"]