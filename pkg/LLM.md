# LLM Guide: Plugin Implementation (`pkg/`)

This directory contains the core scheduler plugin implementations. Each subdirectory represents a distinct plugin with its own functionality and extension points.

## Plugin Categories

### Production-Ready Plugins
- **capacityscheduling/**: Resource quota management with ElasticQuota
- **coscheduling/**: Gang scheduling for grouped pods  
- **noderesources/**: Node resource allocation strategies
- **noderesourcetopology/**: NUMA-aware scheduling
- **networkaware/**: Network topology-aware scheduling
- **trimaran/**: Load-aware scheduling using real metrics
- **preemptiontoleration/**: Enhanced preemption logic

### Sample/Educational Plugins  
- **constantscore/**: Returns constant score (testing/baseline)
- **podstate/**: Basic scoring example
- **qos/**: Quality of Service aware scheduling
- **sysched/**: System call profile aware scheduling
- **crossnodepreemption/**: Cross-node preemption example

## Plugin Development Pattern

### Standard Plugin Structure
```
pkg/yourplugin/
├── yourplugin.go              # Main plugin implementation
├── yourplugin_test.go         # Unit tests
├── README.md                  # Plugin documentation
└── types.go                   # Plugin-specific types (if needed)
```

### Plugin Implementation Template
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

// Implement required framework interfaces
var _ framework.ScorePlugin = &YourPlugin{}

func (p *YourPlugin) Name() string {
    return Name
}

func (p *YourPlugin) Score(ctx context.Context, state *framework.CycleState, 
    pod *v1.Pod, nodeInfo *framework.NodeInfo) (int64, *framework.Status) {
    // Implementation here
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

## Extension Points by Plugin

| Plugin | QueueSort | PreFilter | Filter | PostFilter | PreScore | Score | Reserve | Permit | PreBind | Bind | PostBind | Unreserve |
|--------|-----------|-----------|--------|------------|----------|-------|---------|--------|---------|------|----------|-----------|
| CapacityScheduling | | ✓ | | ✓ | | | ✓ | | | | | ✓ |
| Coscheduling | ✓ | ✓ | | ✓ | | | | ✓ | | | | ✓ |
| NodeResources | | | | | | ✓ | | | | | | |
| NodeResourceTopology | | ✓ | ✓ | | | ✓ | ✓ | | | | ✓ | |
| NetworkOverhead | | ✓ | ✓ | | | ✓ | | | | | | |
| TopologicalSort | ✓ | | | | | | | | | | | |
| Trimaran | | ✓ | | | | ✓ | | | | | | |
| PreemptionToleration | | | | ✓ | | | | | | | | |
| ConstantScore | | | | | | ✓ | | | | | | |

## Common Patterns

### 1. State Management
```go
// Store state in PreFilter, use in Filter/Score
type PreFilterState struct {
    someData map[string]interface{}
}

func (p *Plugin) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) (*framework.PreFilterResult, *framework.Status) {
    state.Write(stateKey, &PreFilterState{someData: data})
    return nil, nil
}

func (p *Plugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) (int64, *framework.Status) {
    s, err := getPreFilterState(state)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, err.Error())
    }
    // Use s.someData
}
```

### 2. Logging
```go
func (p *Plugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) (int64, *framework.Status) {
    logger := klog.FromContext(klog.NewContext(ctx, p.logger)).WithValues("ExtensionPoint", "Score")
    logger.V(10).Info("Scoring node", "pod", pod.Name, "node", nodeInfo.Node().Name)
    return score, nil
}
```

### 3. Configuration Validation
```go
func New(ctx context.Context, args runtime.Object, h framework.Handle) (framework.Plugin, error) {
    pluginArgs, ok := args.(*config.YourPluginArgs)
    if !ok {
        return nil, fmt.Errorf("want args to be of type YourPluginArgs, got %T", args)
    }
    
    if err := validation.ValidateYourPluginArgs(pluginArgs, nil); err != nil {
        return nil, err
    }
    
    return &YourPlugin{args: pluginArgs}, nil
}
```

### 4. Error Handling
```go
// Return appropriate status codes
if node == nil {
    return 0, framework.NewStatus(framework.Error, "node not found")
}

// Success with message
return score, framework.NewStatus(framework.Success, "scored successfully")

// Skip scoring for this node
return 0, framework.NewStatus(framework.Skip, "node not suitable")
```

### 5. Resource Calculations
```go
// Access node resources
allocatable := nodeInfo.Node().Status.Allocatable
capacity := nodeInfo.Node().Status.Capacity

// Calculate used resources
used := util.GetNodeUsage(nodeInfo)

// Score based on utilization
utilization := float64(used[v1.ResourceCPU]) / float64(allocatable[v1.ResourceCPU])
score := int64(utilization * framework.MaxNodeScore)
```

## Testing Patterns

### Unit Test Structure
```go
func TestPluginScore(t *testing.T) {
    tests := []struct {
        name          string
        pod           *v1.Pod
        nodes         []*v1.Node
        expectedScore int64
        expectedStatus *framework.Status
    }{
        {
            name: "basic scoring test",
            pod: &v1.Pod{},
            nodes: []*v1.Node{{}},
            expectedScore: 50,
            expectedStatus: nil,
        },
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            plugin := &YourPlugin{}
            score, status := plugin.Score(context.Background(), framework.NewCycleState(), tt.pod, framework.NewNodeInfo())
            
            if score != tt.expectedScore {
                t.Errorf("expected score %d, got %d", tt.expectedScore, score)
            }
            
            if !reflect.DeepEqual(status, tt.expectedStatus) {
                t.Errorf("expected status %v, got %v", tt.expectedStatus, status)
            }
        })
    }
}
```

## Plugin-Specific Notes

### ConstantScore (`constantscore/`)
- **Purpose**: Returns constant score for all nodes
- **Use Case**: Testing, baseline comparisons, educational
- **Configuration**: `ConstantScoreArgs.Score` (0-100, default 50)
- **Extension Points**: Score only
- **Example Usage**: Useful when you want equal scoring for all nodes

### Coscheduling (`coscheduling/`)
- **Purpose**: Gang scheduling - schedule pods in groups
- **Use Case**: ML workloads, distributed applications
- **Configuration**: `CoschedulingArgs` with wait times and backoff
- **Extension Points**: QueueSort, PreFilter, PostFilter, Permit, Unreserve
- **Key Concept**: PodGroup CRD defines groups of pods

### NodeResourceTopology (`noderesourcetopology/`)
- **Purpose**: NUMA-aware scheduling
- **Use Case**: High-performance computing, latency-sensitive workloads
- **Configuration**: Scoring strategy (LeastAllocated, MostAllocated, BalancedAllocation)
- **Extension Points**: PreFilter, Filter, Score, Reserve, PostBind
- **Requirements**: NodeResourceTopology CRD

### NetworkAware (`networkaware/`)
- **Purpose**: Network topology and latency-aware scheduling
- **Plugins**: TopologicalSort (QueueSort) + NetworkOverhead (Filter + Score)
- **Use Case**: Multi-zone deployments, latency-sensitive applications
- **Configuration**: Network topology definitions
- **Requirements**: AppGroup and NetworkTopology CRDs

## Development Environment

### Python Dependencies (for gRPC/ML plugins)

The devcontainer includes comprehensive Python support for advanced plugins:

- **PyTorch 2.8.0+**: ML model development and training
- **gRPC 1.75.0+**: High-performance RPC communication
- **Kubernetes client**: Cluster API integration and node discovery
- **Triton client**: NVIDIA Triton inference server integration
- **NumPy 2.3.3+**: Numerical computing and array operations
- **ONNX 1.19.0+**: Model serialization and cross-platform deployment
- **Protocol Buffers**: Type-safe message serialization

These are pre-installed and tested in the devcontainer environment.

## Development Checklist

When creating a new plugin:

1. **[ ]** Define plugin structure and interfaces
2. **[ ]** Add configuration types to `apis/config/types.go`
3. **[ ]** Implement validation in `apis/config/validation/`
4. **[ ]** Create comprehensive unit tests
5. **[ ]** Add integration tests in `test/integration/`
6. **[ ]** Write detailed README.md with examples
7. **[ ]** Register plugin in `cmd/scheduler/main.go`
8. **[ ]** Add to main repository README.md
9. **[ ]** Create example manifests
10. **[ ]** Update documentation website if needed
11. **[ ]** For gRPC plugins: Test Python dependencies and gRPC connectivity
12. **[ ]** For ML plugins: Verify PyTorch, ONNX, and Triton integration

## Common Anti-Patterns to Avoid

1. **Don't block in extension points** - Use efficient algorithms
2. **Don't ignore error handling** - Always return appropriate Status
3. **Don't hardcode values** - Use configuration parameters
4. **Don't skip logging** - Use structured logging for debugging
5. **Don't forget validation** - Validate configuration args
6. **Don't assume node state** - Check for nil values
7. **Don't ignore test coverage** - Test edge cases and failures
8. **Don't break compatibility** - Consider API versioning for changes

## Useful Utilities

### From `pkg/util/`
- Node resource calculations
- Common validation helpers
- Test utilities

### From Kubernetes Framework
- `framework.NodeInfo` - Node information wrapper
- `framework.CycleState` - Per-scheduling-cycle state
- `framework.Status` - Return status with codes and messages
- Helper functions for common operations

## Performance Considerations

1. **Caching**: Use local caches for frequently accessed data
2. **Lazy Loading**: Load expensive data only when needed
3. **Efficient Data Structures**: Use appropriate data structures
4. **Memory Management**: Avoid memory leaks in long-running scheduler
5. **Concurrency**: Be aware that multiple plugins run concurrently
6. **Resource Limits**: Consider impact on scheduler performance

This directory contains the heart of the scheduler plugins system. Each plugin implements specific scheduling logic while following common patterns and interfaces.