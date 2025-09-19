# LLM Development Guide for Kubernetes Scheduler Plugins

## Repository Overview

This repository (`scheduler-plugins`) contains out-of-tree scheduler plugins for Kubernetes based on the [scheduler framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/). It provides production-ready scheduler plugins that are exercised in large companies, available as Golang SDK libraries or pre-built container images.

**Key Facts:**
- **Language**: Go 1.24+ 
- **Kubernetes Version**: Compatible with v1.33.3
- **License**: Apache 2.0
- **Repository**: kubernetes-sigs/scheduler-plugins
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

2. **PodState** (`pkg/podstate/`)
   - Basic scoring example
   - Educational/demonstration purposes

3. **QOS** (`pkg/qos/`)
   - Quality of Service aware scheduling

4. **SySched** (`pkg/sysched/`)
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

**Prerequisites**: Docker, kind cluster named 'sched', kubectl

## Creating New Plugins

### 1. Plugin Structure

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

### 2. Configuration Types

Add plugin arguments to `apis/config/types.go`:

```go
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
type YourPluginArgs struct {
    metav1.TypeMeta
    
    // Your configuration fields
    SomeParameter int64 `json:"someParameter,omitempty"`
}
```

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
- `KIND_CLUSTER_NAME`: Kind cluster name (default: sched)

### Docker Images
- **Base**: gcr.io/distroless/static:nonroot
- **Binary**: Single statically linked `/kube-scheduler`
- **User**: 65532:65532 (nonroot)

### Kubernetes Compatibility
- This repository tracks latest Kubernetes releases
- Client-go version matches Kubernetes version
- Currently compatible with Kubernetes v1.33.3

## Best Practices for LLMs

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
2. **Configuration errors**: Validate args structure matches `types.go`
3. **Build failures**: Ensure Go version compatibility (1.24+)
4. **Test failures**: Check kind cluster setup and kubectl configuration
5. **Scoring issues**: Verify score values are within valid range (0-100)

## Additional Resources

- [Kubernetes Scheduler Framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
- [Plugin Development Guide](doc/develop.md)
- [Installation Guide](doc/install.md)
- [KEP Documentation](kep/) - Design documents for major features
- [Integration Tests](test/integration/) - Real-world usage examples

For specific plugin documentation, see the README.md files in each `pkg/*/` directory.