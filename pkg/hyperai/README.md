# HyperAI Plugin

The HyperAI plugin is a Kubernetes scheduler ScorePlugin that connects to a Python gRPC server for node scoring. In the first version, it returns a constant score for all nodes via gRPC communication.

## Architecture

The plugin consists of:
- A Go scheduler plugin (`pkg/hyperai/hyperai.go`) that implements the ScorePlugin interface
- A Python gRPC server (`hack/hyperai-grpc/server.py`) that provides scoring services
- Protocol Buffers definition (`hack/hyperai-grpc/hyperai.proto`) for service communication

## Features
- **gRPC Connectivity**: Full integration with Python gRPC server for real-time scoring
- **Fallback Logic**: Returns constant score if gRPC server is unavailable  
- **Protocol Buffers**: Type-safe communication between Go and Python
- **Testing Suite**: Comprehensive testing including unit tests and integration tests
- **Build Automation**: Complete Makefile targets for development workflow

## Configuration

Register the plugin in the scheduler config:

```yaml
apiVersion: kubescheduler.config.k8s.io/v1beta3
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: hyperai-scheduler
  plugins:
    score:
      enabled:
      - name: HyperAI
        weight: 100
      disabled:
      - name: "*"
  pluginConfig:
  - name: HyperAI
    args:
      grpcAddress: "localhost:50051"
      score: 42
```

## Development Workflow

```bash
# Generate gRPC code
make hyperai-proto

# Build and deploy to kind cluster
make hyperai-full-test

# Test gRPC connectivity independently  
make hyperai-test-grpc
```

## Implementation Details
- The plugin is implemented in Go in `pkg/hyperai/hyperai.go`.
- The Python gRPC server is in `hack/hyperai-grpc/server.py`.
- gRPC code generation is automated via `make hyperai-proto`.
- The plugin gracefully handles gRPC connection failures by falling back to constant scoring.
- Currently returns a constant score of 42 but the gRPC infrastructure is in place for advanced scoring algorithms.
