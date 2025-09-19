# LLM Development Guide for Kubernetes Scheduler Plugins

## Repository Overview

This repository (`scheduler-plugins`) contains out-of-tree scheduler plugins for Kubernetes based on the [scheduler framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/). It provides production-ready scheduler plugins that are exercised in large companies, available as Golang SDK libraries or pre-built container images.

**Key Facts:**
- **Language**: Go 1.24+ 
- **Kubernetes Version**: Compatible with v1.33.3
- **License**: Apache 2.0
- **R## Best Practices for Plugin Development

### General Guidelines

1. **Always check existing plugins** for similar functionality before creating new ones
2. **Follow naming conventions**: Use PascalCase for plugin names, match directory names
3. **Implement proper validation** in plugin args validation functions
4. **Add comprehensive tests** - both unit and integration
5. **Document plugin behavior** in README.md files
6. **Use structured logging** with appropriate log levels
7. **Handle edge cases** gracefully with proper error statuses
8. **Consider resource efficiency** - plugins run in scheduler hot path
9. **Test with real workloads** using the provided Makefile targets
10. **Follow Kubernetes API conventions** for configuration types

### gRPC Plugin Guidelines

11. **Implement fallback logic** for gRPC failures (like HyperAI)
12. **Use appropriate timeouts** for gRPC calls (5s recommended)
13. **Log success/failure clearly** with different log levels
14. **Choose architecture wisely**:
    - **Sidecar**: For high-throughput, low-latency requirements
    - **Service**: For shared gRPC servers across multiple schedulers
15. **Validate gRPC responses** before using scores
16. **Handle connection pooling** for performance in high-load scenarios
17. **Secure gRPC communication** in production (TLS, authentication)
18. **Monitor gRPC server health** with readiness/liveness probes
19. **Version your Protocol Buffers** for backward compatibility
20. **Test both success and failure scenarios** extensively

### Performance Considerations

- **Scoring latency**: Keep plugin execution under 1ms when possible
- **Memory usage**: Avoid large allocations in scoring path
- **gRPC overhead**: Sidecar communication has ~100x lower latency than service calls
- **Caching**: Cache expensive computations when appropriate
- **Batch operations**: Consider batching multiple scoring requests kubernetes-sigs/scheduler-plugins
- **Current Branch**: hyper-ai (default: master)

## Repository Structure

```
scheduler-plugins/
├── apis/                          # API definitions and configurations
│   ├── config/                    # Plugin configuration types
│   │   ├── types.go              # All plugin argument types
│   │   └── validation/           # Configuration validation
│   └── scheduling/               # Scheduling API definitions
├── cmd/                          # Main applications
│   ├── controller/               # Controller manager
│   └── scheduler/                # Main scheduler binary
├── pkg/                          # Core plugin implementations
│   ├── capacityscheduling/       # Capacity scheduling plugin
│   ├── constantscore/            # Constant score plugin (simple example)
│   ├── coscheduling/             # Gang scheduling plugin
│   ├── hyperai/                  # HyperAI gRPC-based scoring plugin
│   ├── noderesources/            # Node resource plugins
│   ├── noderesourcetopology/     # NUMA-aware scheduling
│   ├── networkaware/             # Network-aware scheduling
│   ├── preemptiontoleration/     # Preemption handling
│   ├── qos/                      # Quality of Service plugin
│   ├── sysched/                  # System call aware scheduling
│   └── trimaran/                 # Load-aware scheduling
├── manifests/                    # Kubernetes manifests
├── config/                       # Kustomize configurations
├── hack/                         # Build and test scripts
├── test/                         # Integration tests
└── site/                         # Documentation website
```

## Plugin Architecture

### Core Interfaces

Plugins implement one or more of these Kubernetes scheduler framework interfaces:

```go
// Extension points (from k8s.io/kubernetes/pkg/scheduler/framework)
framework.QueueSortPlugin       // Sort pods in scheduling queue
framework.PreFilterPlugin       // Preprocess pods before filtering
framework.FilterPlugin          // Filter nodes for pod placement
framework.PostFilterPlugin      // Handle filtering failures
framework.PreScorePlugin        // Preprocess before scoring
framework.ScorePlugin           // Score nodes for pod placement
framework.ReservePlugin         // Reserve resources
framework.PermitPlugin          // Approve/deny pod binding
framework.PreBindPlugin         // Actions before binding
framework.BindPlugin            // Bind pod to node
framework.PostBindPlugin        // Actions after binding
framework.UnreservePlugin       // Unreserve resources
```

### Plugin Configuration

Plugins are configured via `PluginConfig` in scheduler configuration:

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: my-scheduler
  plugins:
    score:
      enabled:
      - name: ConstantScore
        weight: 10
  pluginConfig:
  - name: ConstantScore
    args:
      score: 75
```

## Available Plugins

### Production Plugins

1. **CapacityScheduling** (`pkg/capacityscheduling/`)
   - Resource quota management with ElasticQuota
   - Implements PreFilter, PostFilter, Reserve

2. **Coscheduling** (`pkg/coscheduling/`)
   - Gang scheduling for grouped pods
   - Implements QueueSort, PreFilter, PostFilter, Permit, Unreserve

3. **NodeResources** (`pkg/noderesources/`)
   - Node resource allocation strategies
   - Scoring based on allocatable resources

4. **NodeResourceTopology** (`pkg/noderesourcetopology/`)
   - NUMA-aware scheduling
   - Implements Filter, Score, Reserve, PostBind

5. **NetworkAware** (`pkg/networkaware/`)
   - TopologicalSort: Queue sorting by network topology
   - NetworkOverhead: Network cost-aware placement

6. **Trimaran** (`pkg/trimaran/`)
   - Load-aware scheduling using real metrics
   - Multiple strategies: TargetLoadPacking, LoadVariationRiskBalancing

7. **PreemptionToleration** (`pkg/preemptiontoleration/`)
   - Enhanced preemption logic
   - Implements PostFilter

### Sample/Testing Plugins

1. **ConstantScore** (`pkg/constantscore/`)
   - Returns constant score for all nodes
   - Useful for testing and baselines

2. **HyperAI** (`pkg/hyperai/`)
  - **Advanced gRPC-based scoring plugin**
  - Connects to Python gRPC server for machine learning scoring
  - **Architecture**: Supports both sidecar and service deployment
  - **Protocol Buffers**: Type-safe gRPC communication
  - **Protocol Update**: Sends full Pod and Node specs as JSON in the gRPC request (see proto in `pkg/hyperai/README.md`)
  - **Fallback Logic**: Returns constant score if gRPC unavailable
  - **Configuration**: Configurable gRPC address and fallback score
  - **Use Cases**: ML-based node scoring, custom scoring algorithms

3. **PodState** (`pkg/podstate/`)
   - Basic scoring example
   - Educational/demonstration purposes

4. **QOS** (`pkg/qos/`)
   - Quality of Service aware scheduling

5. **SySched** (`pkg/sysched/`)
   - System call profile aware scheduling

## Development Workflow

### Building

```bash
# Build scheduler binary
make build

# Build with ConstantScore plugin focus
make build-scheduler

# Build Docker image for ConstantScore
make constantscore-image
```

### Testing

```bash
# Unit tests
make unit-test

# Integration tests  
make integration-test

# Verification (formatting, codegen, etc.)
make verify

# ConstantScore full test cycle (requires kind cluster)
make constantscore-full-test

# HyperAI full test cycle (requires kind cluster)
make hyperai-sidecar-full-test  # Recommended: sidecar architecture
make hyperai-full-test          # Alternative: separate service architecture
```

### ConstantScore Plugin Workflow

The repository includes specialized Makefile targets for the ConstantScore plugin:

```bash
# Complete test cycle for ConstantScore
make constantscore-full-test

# Individual steps
make constantscore-image        # Build Docker image
make constantscore-load-kind    # Load into kind cluster  
make constantscore-deploy       # Deploy to cluster
make constantscore-test         # Run test pod
make constantscore-logs         # View scheduler logs
make constantscore-cleanup      # Clean up resources
```

### HyperAI Plugin Workflow

The repository includes comprehensive Makefile targets for the HyperAI plugin with both sidecar and service architectures:

```bash
# Complete test cycle for HyperAI (sidecar - recommended)
make hyperai-sidecar-full-test

# Complete test cycle for HyperAI (separate service)
make hyperai-full-test

# Development workflow
make hyperai-proto              # Generate gRPC code
make hyperai-test-grpc          # Test local gRPC connectivity
make hyperai-sidecar-deploy     # Deploy sidecar architecture
make hyperai-deploy             # Deploy service architecture

# Individual steps
make hyperai-image              # Build scheduler Docker image
make hyperai-grpc-image         # Build gRPC server Docker image
make hyperai-load-kind          # Load images into kind cluster
make hyperai-sidecar-test       # Run test pod with sidecar
make hyperai-test               # Run test pod with service
make hyperai-sidecar-logs       # View sidecar scheduler logs
make hyperai-logs               # View service scheduler logs
make hyperai-cleanup            # Clean up resources
```

**Prerequisites**: Docker, kind cluster named 'sched', kubectl, Python 3.11+ with gRPC tools

## Creating New Plugins

### 1. Basic Plugin Structure

Create new plugin in `pkg/yourplugin/`:

```go
package yourplugin

import (
    "context"
    "k8s.io/kubernetes/pkg/scheduler/framework"
    "sigs.k8s.io/scheduler-plugins/apis/config"
)

const Name = "YourPlugin"

type YourPlugin struct {
    logger klog.Logger
    handle framework.Handle
    args   *config.YourPluginArgs
}

// Implement required interfaces
var _ framework.ScorePlugin = &YourPlugin{}

func (p *YourPlugin) Name() string {
    return Name
}

func (p *YourPlugin) Score(ctx context.Context, state *framework.CycleState, 
    pod *v1.Pod, nodeInfo *framework.NodeInfo) (int64, *framework.Status) {
    // Your scoring logic here
    return score, nil
}

func New(ctx context.Context, args runtime.Object, h framework.Handle) (framework.Plugin, error) {
    // Plugin initialization
    return &YourPlugin{
        logger: klog.FromContext(ctx),
        handle: h,
    }, nil
}
```

### 1a. Advanced gRPC Plugin Structure (HyperAI Pattern)

For plugins requiring external scoring services:

```go
package yourgrpcplugin

import (
    "context"
    "time"
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials/insecure"
    "k8s.io/kubernetes/pkg/scheduler/framework"
)

type YourGRPCPlugin struct {
    logger klog.Logger
    handle framework.Handle
    args   *config.YourGRPCPluginArgs
}

func (p *YourGRPCPlugin) Score(ctx context.Context, state *framework.CycleState, 
    pod *v1.Pod, nodeInfo *framework.NodeInfo) (int64, *framework.Status) {
    
    // Connect to gRPC server
    conn, err := grpc.Dial(p.args.GRPCAddress, 
        grpc.WithTransportCredentials(insecure.NewCredentials()), 
        grpc.WithTimeout(5*time.Second))
    if err != nil {
        p.logger.Error(err, "Failed to connect to gRPC server, using fallback", 
            "fallbackScore", p.args.FallbackScore)
        return p.args.FallbackScore, nil
    }
    defer conn.Close()

    // Create gRPC client and call service
    client := NewYourServiceClient(conn)
    response, err := client.GetScore(ctx, &ScoreRequest{
        PodName:  pod.Name,
        NodeName: nodeInfo.Node().Name,
    })
    
    if err != nil {
        p.logger.Error(err, "gRPC call failed, using fallback", 
            "fallbackScore", p.args.FallbackScore)
        return p.args.FallbackScore, nil
    }

    p.logger.Info("✅ gRPC SUCCESS: Received score", 
        "score", response.Score, "grpcAddress", p.args.GRPCAddress)
    return response.Score, nil
}
```

### 2. Configuration Types

Add plugin arguments to `apis/config/types.go` and `apis/config/v1/types.go`:

```go
// In apis/config/types.go
type YourPluginArgs struct {
    metav1.TypeMeta
    
    // Your configuration fields
    SomeParameter int64 `json:"someParameter,omitempty"`
}

// For gRPC plugins, include networking configuration
type YourGRPCPluginArgs struct {
    metav1.TypeMeta
    
    // gRPC server address (e.g., "localhost:50051" for sidecar)
    GRPCAddress string `json:"grpcAddress,omitempty"`
    
    // Fallback score when gRPC unavailable
    FallbackScore int64 `json:"fallbackScore,omitempty"`
    
    // Additional gRPC configuration
    Timeout string `json:"timeout,omitempty"`
}
```

**Important**: Also add the same types to `apis/config/v1/types.go` and register them in `apis/config/v1/register.go`, then run `hack/update-codegen.sh` to generate required methods.

### 3. Register Plugin

In `cmd/scheduler/main.go`, register your plugin:

```go
import "sigs.k8s.io/scheduler-plugins/pkg/yourplugin"

// Add to plugin registry
app.WithPlugin(yourplugin.Name, yourplugin.New)
```

### 4. Add Tests

Create test files following existing patterns:
- `pkg/yourplugin/yourplugin_test.go` - Unit tests
- `test/integration/yourplugin_test.go` - Integration tests

## Key Files for LLMs

### Essential Files to Understand
1. `cmd/scheduler/main.go` - Entry point and plugin registration
2. `apis/config/types.go` - All plugin configuration types
3. `pkg/*/README.md` - Plugin-specific documentation
4. `Makefile` - Build and test automation
5. `go.mod` - Dependencies and Go version

### Example Plugin: ConstantScore
- **Location**: `pkg/constantscore/`
- **Purpose**: Returns constant score for all nodes
- **Interfaces**: ScorePlugin
- **Configuration**: `ConstantScoreArgs.Score` (0-100, default 50)
- **Use Case**: Testing, baseline comparisons

### Example Plugin: HyperAI (Advanced)
- **Location**: `pkg/hyperai/`
- **Purpose**: Connects to Python gRPC server for ML-based node scoring
- **Interfaces**: ScorePlugin
- **Configuration**: `HyperAIArgs` with gRPC address and fallback score
- **Architecture Options**:
  - **Sidecar** (recommended): gRPC server runs in same pod as scheduler
  - **Service**: gRPC server runs as separate Kubernetes service
- **Protocol**: gRPC with Protocol Buffers (`hack/hyperai-grpc/hyperai.proto`)
- **Fallback**: Returns constant score if gRPC server unavailable
- **Python Server**: Located in `hack/hyperai-grpc/server.py`
- **Use Cases**: 
  - Machine learning-based node scoring
  - Custom scoring algorithms in Python
  - Integration with external scoring services
  - Real-time adaptive scheduling

#### HyperAI Architecture Comparison

| Aspect | Sidecar Architecture | Service Architecture |
|--------|---------------------|----------------------|
| **Latency** | ~0.1ms (localhost) | ~1-5ms (network) |
| **Reliability** | No network deps | Service discovery required |
| **Scaling** | Per scheduler pod | Independent scaling |
| **Deployment** | Atomic (scheduler + gRPC) | Separate lifecycles |
| **Resource Usage** | Higher per pod | Shared across schedulers |
| **Use Case** | High-throughput scheduling | Multi-scheduler environments |

#### HyperAI Configuration Example

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: hyperai-scheduler
  plugins:
    score:
      enabled:
      - name: HyperAI
  pluginConfig:
  - name: HyperAI
    args:
      grpcAddress: "localhost:50051"          # Sidecar
      # grpcAddress: "hyperai-grpc-service.scheduler-plugins.svc.cluster.local:50051"  # Service
      score: 42                               # Fallback score
```

#### HyperAI gRPC Protocol

```protobuf
syntax = "proto3";

package hyperai;
option go_package = "sigs.k8s.io/scheduler-plugins/pkg/hyperai";

service HyperAI {
  rpc GetScore(ScoreRequest) returns (ScoreReply) {}
}

message ScoreRequest {
  string pod_name = 1;
  string node_name = 2;
}

message ScoreReply {
  int64 score = 1;
}
```

### Common Patterns

1. **Logging**: Use `klog.FromContext(ctx)` for structured logging
2. **State Management**: Use `framework.CycleState` for sharing data between extension points
3. **Configuration**: Validate args in `New()` function
4. **Error Handling**: Return `framework.Status` with appropriate codes
5. **Testing**: Use `test/util` helpers for test setup

### Scoring Guidelines
- Return values between `framework.MinNodeScore` (0) and `framework.MaxNodeScore` (100)
- Higher scores indicate better nodes for pod placement
- Use `ScoreExtensions()` for score normalization if needed

### Extension Point Order
1. QueueSort → PreFilter → Filter → PostFilter → PreScore → Score → Reserve → Permit → PreBind → Bind → PostBind

## Build System

### Environment Variables
- `GO_VERSION`: Go version from go.mod
- `VERSION`: Scheduler version (default: v0.0.YYYYMMDD)
- `CONSTANTSCORE_IMAGE_NAME`: Docker image name (default: constantscore-scheduler)
- `CONSTANTSCORE_IMAGE_TAG`: Docker image tag (default: latest)
- `HYPERAI_IMAGE_NAME`: HyperAI Docker image name (default: hyperai-scheduler)
- `HYPERAI_IMAGE_TAG`: HyperAI Docker image tag (default: latest)
- `KIND_CLUSTER_NAME`: Kind cluster name (default: sched)

### Docker Images
- **Base**: gcr.io/distroless/static:nonroot
- **Binary**: Single statically linked `/kube-scheduler`
- **User**: 65532:65532 (nonroot)

### Kubernetes Compatibility
- This repository tracks latest Kubernetes releases
- Client-go version matches Kubernetes version
- Currently compatible with Kubernetes v1.33.3

### 5. gRPC Service Development (Optional)

For plugins requiring external services, create gRPC server:

1. **Define Protocol Buffers** (`hack/yourplugin-grpc/service.proto`):
```protobuf
syntax = "proto3";
package yourplugin;
option go_package = "sigs.k8s.io/scheduler-plugins/pkg/yourplugin";

service YourService {
  rpc GetScore(ScoreRequest) returns (ScoreReply) {}
}

message ScoreRequest {
  string pod_name = 1;
  string node_name = 2;
  // Add more context as needed
  map<string, string> pod_labels = 3;
  map<string, string> node_labels = 4;
}

message ScoreReply {
  int64 score = 1;
  string reason = 2;  // Optional: explain scoring decision
}
```

2. **Python gRPC Server** (`hack/yourplugin-grpc/server.py`):
```python
import grpc
from concurrent import futures
import yourplugin_pb2
import yourplugin_pb2_grpc

class YourServicer(yourplugin_pb2_grpc.YourServiceServicer):
    def GetScore(self, request, context):
        # Your ML/scoring logic here
        score = self.calculate_score(request.pod_name, request.node_name)
        return yourplugin_pb2.ScoreReply(score=score)
    
    def calculate_score(self, pod_name, node_name):
        # Implement your scoring algorithm
        return 88  # Example score

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    yourplugin_pb2_grpc.add_YourServiceServicer_to_server(YourServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC server started on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
```

3. **Generate gRPC Code**:
```bash
# Add to Makefile
.PHONY: yourplugin-proto
yourplugin-proto:
	cd hack/yourplugin-grpc && python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. service.proto
	cd pkg/yourplugin && protoc --go_out=. --go-grpc_out=. -I../../hack/yourplugin-grpc ../../hack/yourplugin-grpc/service.proto
```

4. **Deployment Options**:
   - **Sidecar**: Include gRPC server container in scheduler pod (recommended for low latency)
   - **Service**: Deploy gRPC server as separate Kubernetes service (better for scaling)

## Best Practices for Plugin Development

1. **Always check existing plugins** for similar functionality before creating new ones
2. **Follow naming conventions**: Use PascalCase for plugin names, match directory names
3. **Implement proper validation** in plugin args validation functions
4. **Add comprehensive tests** - both unit and integration
5. **Document plugin behavior** in README.md files
6. **Use structured logging** with appropriate log levels
7. **Handle edge cases** gracefully with proper error statuses
8. **Consider resource efficiency** - plugins run in scheduler hot path
9. **Test with real workloads** using the provided Makefile targets
10. **Follow Kubernetes API conventions** for configuration types

## Common Issues & Solutions

1. **Plugin not loading**: Check registration in `cmd/scheduler/main.go`
2. **Configuration errors**: Validate args structure matches `types.go` and `v1/types.go`
3. **Build failures**: Ensure Go version compatibility (1.24+)
4. **Test failures**: Check kind cluster setup and kubectl configuration
5. **Scoring issues**: Verify score values are within valid range (0-100)
6. **gRPC connection failures**: 
   - Check service discovery (for service architecture)
   - Verify localhost connectivity (for sidecar architecture)
   - Validate Protocol Buffers compilation
7. **Code generation errors**: Run `hack/update-codegen.sh` after adding new types
8. **Docker image issues**: Ensure images are loaded into kind cluster correctly
9. **Readiness probe failures**: Configure appropriate health checks for gRPC servers
10. **Type conversion errors**: Ensure plugin args types are registered in both `config` and `config/v1` packages

## Additional Resources

- [Kubernetes Scheduler Framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
- [Plugin Development Guide](doc/develop.md)
- [Installation Guide](doc/install.md)
- [KEP Documentation](kep/) - Design documents for major features
- [Integration Tests](test/integration/) - Real-world usage examples

For specific plugin documentation, see the README.md files in each `pkg/*/` directory.