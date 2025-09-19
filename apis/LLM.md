# LLM Guide: API Definitions (`apis/`)

This directory contains the API definitions, configuration types, and validation logic for all scheduler plugins.

## Directory Structure

```
apis/
├── config/                        # Plugin configuration APIs
│   ├── types.go                   # All plugin argument types
│   ├── doc.go                     # Package documentation
│   ├── register.go                # Scheme registration
│   ├── zz_generated.deepcopy.go   # Generated deep copy methods
│   ├── scheme/                    # Scheme registration helpers
│   ├── v1/                        # Versioned API (if needed)
│   └── validation/                # Configuration validation
│       ├── validation.go          # Validation functions
│       └── validation_test.go     # Validation tests
└── scheduling/                    # Scheduling-related APIs
    ├── doc.go
    ├── groupversion_info.go
    ├── scheme/
    └── v1alpha1/
```

## Plugin Configuration Types

All plugin configuration types are defined in `config/types.go`. Each plugin that accepts configuration must have a corresponding `Args` type.

### Configuration Type Pattern

```go
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object

// YourPluginArgs holds arguments used to configure YourPlugin.
type YourPluginArgs struct {
    metav1.TypeMeta `json:",inline"`

    // Your configuration fields with JSON tags and comments
    SomeParameter int64 `json:"someParameter,omitempty"`
    
    // Another field with validation constraints
    RequiredField string `json:"requiredField"`
    
    // Complex nested configuration
    NestedConfig *SomeNestedConfig `json:"nestedConfig,omitempty"`
}

// Supporting nested types
type SomeNestedConfig struct {
    Field1 string `json:"field1,omitempty"`
    Field2 int    `json:"field2,omitempty"`
}
```

### Key Requirements

1. **`+k8s:deepcopy-gen` comment**: Required for code generation
2. **`metav1.TypeMeta`**: Embed TypeMeta for Kubernetes object compliance  
3. **JSON tags**: Use `omitempty` for optional fields
4. **Documentation**: Add comments for all fields (used in generated docs)

## Current Plugin Configurations

### Core Production Plugins

#### CoschedulingArgs
```go
type CoschedulingArgs struct {
    metav1.TypeMeta
    
    // PermitWaitingTimeSeconds is the waiting timeout in seconds.
    PermitWaitingTimeSeconds int64
    // PodGroupBackoffSeconds is the backoff time in seconds before a pod group can be scheduled again.
    PodGroupBackoffSeconds int64
}
```

#### NodeResourcesAllocatableArgs
```go
type NodeResourcesAllocatableArgs struct {
    metav1.TypeMeta `json:",inline"`

    // Resources to be considered when scoring.
    Resources []schedconfig.ResourceSpec `json:"resources,omitempty"`

    // Whether to prioritize nodes with least or most allocatable resources.
    Mode ModeType `json:"mode,omitempty"`
}

// Supporting enums
type ModeType string

const (
    Least ModeType = "Least"
    Most  ModeType = "Most"
)
```

#### NodeResourceTopologyMatchArgs
```go
type NodeResourceTopologyMatchArgs struct {
    metav1.TypeMeta

    // ScoringStrategy determines how nodes are scored.
    ScoringStrategy ScoringStrategy
    // CacheResyncPeriodSeconds enables caching if > 0
    CacheResyncPeriodSeconds int64
    // DiscardReservedNodes excludes nodes with reserved pods
    DiscardReservedNodes bool
    // Cache fine-tunes caching behavior
    Cache *NodeResourceTopologyCache
}
```

#### ConstantScoreArgs (Example)
```go
type ConstantScoreArgs struct {
    metav1.TypeMeta

    // Score is the constant score value to return for all nodes.
    // Valid range is 0-100. Default is 50.
    Score int64 `json:"score,omitempty"`
}
```

### Network-Aware Plugins

#### NetworkOverheadArgs
```go
type NetworkOverheadArgs struct {
    metav1.TypeMeta

    // Namespaces to be considered by NetworkMinCost plugin
    Namespaces []string

    // Preferred weights (Default: UserDefined)
    WeightsName string

    // The NetworkTopology CRD name
    NetworkTopologyName string
}
```

#### TopologicalSortArgs
```go
type TopologicalSortArgs struct {
    metav1.TypeMeta

    // Namespaces to be considered by TopologySort plugin
    Namespaces []string
}
```

### Load-Aware Plugins (Trimaran)

#### TrimaranSpec (Common Base)
```go
type TrimaranSpec struct {
    // Metric Provider to use when using load watcher as a library
    MetricProvider MetricProviderSpec
    // Address of load watcher service
    WatcherAddress string
}

type MetricProviderSpec struct {
    Type               MetricProviderType
    Address            string
    Token              string
    InsecureSkipVerify bool
}
```

#### TargetLoadPackingArgs
```go
type TargetLoadPackingArgs struct {
    metav1.TypeMeta

    TrimaranSpec
    DefaultRequests           v1.ResourceList
    DefaultRequestsMultiplier string
    TargetUtilization        int64
}
```

## Configuration Validation

### Validation Pattern

Each plugin configuration should have validation functions in `validation/validation.go`:

```go
// ValidateYourPluginArgs validates YourPlugin configuration
func ValidateYourPluginArgs(args *config.YourPluginArgs, fldPath *field.Path) error {
    var allErrs field.ErrorList
    
    if args.SomeParameter < 0 || args.SomeParameter > 100 {
        allErrs = append(allErrs, field.Invalid(fldPath.Child("someParameter"), 
            args.SomeParameter, "must be between 0 and 100"))
    }
    
    if args.RequiredField == "" {
        allErrs = append(allErrs, field.Required(fldPath.Child("requiredField"), 
            "this field is required"))
    }
    
    return allErrs.ToAggregate()
}
```

### Validation Best Practices

1. **Range Validation**: Check numeric bounds
2. **Required Fields**: Validate required fields are present
3. **Format Validation**: Validate string formats (URLs, names, etc.)
4. **Cross-Field Validation**: Validate relationships between fields
5. **Resource Validation**: Validate Kubernetes resource specifications
6. **Enum Validation**: Validate enum values are in allowed set

### Example Validations

```go
// Range validation
if args.Score < 0 || args.Score > 100 {
    allErrs = append(allErrs, field.Invalid(fldPath.Child("score"), 
        args.Score, "must be between 0 and 100"))
}

// Required field validation
if args.WatcherAddress == "" {
    allErrs = append(allErrs, field.Required(fldPath.Child("watcherAddress"), 
        "watcher address is required"))
}

// URL validation
if _, err := url.Parse(args.WatcherAddress); err != nil {
    allErrs = append(allErrs, field.Invalid(fldPath.Child("watcherAddress"), 
        args.WatcherAddress, "must be a valid URL"))
}

// Enum validation
if args.Mode != Least && args.Mode != Most {
    allErrs = append(allErrs, field.NotSupported(fldPath.Child("mode"), 
        args.Mode, []string{string(Least), string(Most)}))
}
```

## Code Generation

### Deep Copy Generation

The `// +k8s:deepcopy-gen` comments trigger automatic generation of deep copy methods:

```bash
# Generate deep copy methods
hack/update-codegen.sh
```

Generated methods appear in `zz_generated.deepcopy.go`:

```go
// DeepCopy is an autogenerated deepcopy function
func (in *YourPluginArgs) DeepCopy() *YourPluginArgs {
    if in == nil {
        return nil
    }
    out := new(YourPluginArgs)
    in.DeepCopyInto(out)
    return out
}
```

### Scheme Registration

Register types in `register.go`:

```go
func init() {
    // SchemeBuilder is the scheme builder with scheme registration functions
    SchemeBuilder.Register(addKnownTypes)
}

func addKnownTypes(scheme *runtime.Scheme) error {
    scheme.AddKnownTypes(SchemeGroupVersion,
        &YourPluginArgs{},
    )
    return nil
}
```

## Usage in Scheduler Configuration

### YAML Configuration

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: my-scheduler
  plugins:
    score:
      enabled:
      - name: YourPlugin
        weight: 10
  pluginConfig:
  - name: YourPlugin
    args:
      someParameter: 75
      requiredField: "example"
      nestedConfig:
        field1: "value1"
        field2: 42
```

### Runtime Usage in Plugin

```go
func New(ctx context.Context, args runtime.Object, h framework.Handle) (framework.Plugin, error) {
    // Type assertion to get plugin-specific args
    pluginArgs, ok := args.(*config.YourPluginArgs)
    if !ok {
        return nil, fmt.Errorf("want args to be of type YourPluginArgs, got %T", args)
    }

    // Validate configuration
    if err := validation.ValidateYourPluginArgs(pluginArgs, nil); err != nil {
        return nil, err
    }

    // Use configuration
    return &YourPlugin{
        someParam: pluginArgs.SomeParameter,
        required:  pluginArgs.RequiredField,
    }, nil
}
```

## Common Patterns

### 1. Enum Types
```go
type ScoringStrategyType string

const (
    MostAllocated      ScoringStrategyType = "MostAllocated"
    BalancedAllocation ScoringStrategyType = "BalancedAllocation"  
    LeastAllocated     ScoringStrategyType = "LeastAllocated"
)
```

### 2. Resource Specifications
```go
// Reuse Kubernetes resource types
Resources []schedconfig.ResourceSpec `json:"resources,omitempty"`

// Or define custom resource configs
type ResourceConfig struct {
    Name   v1.ResourceName `json:"name"`
    Weight int64           `json:"weight"`
}
```

### 3. Time Durations
```go
// Use int64 for seconds (easier configuration)
PermitWaitingTimeSeconds int64 `json:"permitWaitingTimeSeconds,omitempty"`

// Or use metav1.Duration for richer time formats
Timeout metav1.Duration `json:"timeout,omitempty"`
```

### 4. Optional Complex Types
```go
// Use pointers for optional complex types
Cache *NodeResourceTopologyCache `json:"cache,omitempty"`

// Provide defaults in validation or New() function
if args.Cache == nil {
    args.Cache = &NodeResourceTopologyCache{
        ForeignPodsDetect: &defaultDetectMode,
    }
}
```

## Testing Configuration

### Validation Tests
```go
func TestValidateYourPluginArgs(t *testing.T) {
    tests := []struct {
        name    string
        args    *config.YourPluginArgs
        wantErr bool
    }{
        {
            name: "valid configuration",
            args: &config.YourPluginArgs{
                SomeParameter: 50,
                RequiredField: "test",
            },
            wantErr: false,
        },
        {
            name: "invalid range",
            args: &config.YourPluginArgs{
                SomeParameter: -1,
                RequiredField: "test",
            },
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := validation.ValidateYourPluginArgs(tt.args, field.NewPath("args"))
            if (err != nil) != tt.wantErr {
                t.Errorf("ValidateYourPluginArgs() error = %v, wantErr %v", err, tt.wantErr)
            }
        })
    }
}
```

## Development Workflow

### Adding New Plugin Configuration

1. **Define Args Type**: Add to `config/types.go`
2. **Add Validation**: Create validation function in `validation/validation.go`
3. **Register Type**: Update `register.go` if needed
4. **Generate Code**: Run `hack/update-codegen.sh`
5. **Test Validation**: Add tests to `validation/validation_test.go`
6. **Use in Plugin**: Reference in plugin's `New()` function

### Updating Existing Configuration

1. **Modify Type**: Update in `config/types.go`
2. **Update Validation**: Modify validation function
3. **Regenerate Code**: Run `hack/update-codegen.sh`
4. **Update Tests**: Add tests for new fields
5. **Update Documentation**: Update plugin README

This directory serves as the contract between the scheduler and plugins, defining exactly what configuration options are available and how they should be validated.