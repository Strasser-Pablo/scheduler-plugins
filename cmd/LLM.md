# LLM Guide: Main Applications (`cmd/`)

This directory contains the main entry points for the scheduler applications.

## Directory Structure

```
cmd/
├── controller/                    # Controller manager application
│   ├── controller.go             # Main controller entry point
│   └── app/                      # Controller application logic
│       └── controller.go         # Controller implementation
└── scheduler/                    # Scheduler application  
    ├── main.go                   # Main scheduler entry point
    └── main_test.go             # Scheduler setup tests
```

## Main Scheduler (`scheduler/main.go`)

This is the primary entry point for the enhanced Kubernetes scheduler with plugin support.

### Key Components

#### Plugin Registration
```go
func main() {
    // Create scheduler command with plugin registry
    command := app.NewSchedulerCommand(
        app.WithPlugin(capacityscheduling.Name, capacityscheduling.New),
        app.WithPlugin(coscheduling.Name, coscheduling.New),
        app.WithPlugin(constantscore.Name, constantscore.New),
        app.WithPlugin(noderesources.Name, noderesources.New),
        app.WithPlugin(noderesourcetopology.Name, noderesourcetopology.New),
        app.WithPlugin(networkoverhead.Name, networkoverhead.New),
        app.WithPlugin(topologicalsort.Name, topologicalsort.New),
        app.WithPlugin(trimaran.Name, trimaran.New),
        app.WithPlugin(preemptiontoleration.Name, preemptiontoleration.New),
        app.WithPlugin(podstate.Name, podstate.New),
        app.WithPlugin(qos.Name, qos.New),
        app.WithPlugin(sysched.Name, sysched.New),
        // Add more plugins here
    )

    // Execute the command
    if err := command.Execute(); err != nil {
        os.Exit(1)
    }
}
```

#### Plugin Registry Pattern
Each plugin is registered using `app.WithPlugin()`:
- **Name**: Plugin identifier (must match plugin's `Name` constant)
- **Constructor**: Plugin factory function with signature `func(context.Context, runtime.Object, framework.Handle) (framework.Plugin, error)`

### Adding New Plugins

To register a new plugin:

1. **Import the plugin package**:
```go
import "sigs.k8s.io/scheduler-plugins/pkg/yourplugin"
```

2. **Add to registration**:
```go
app.WithPlugin(yourplugin.Name, yourplugin.New),
```

3. **Ensure plugin implements required interfaces**:
```go
// In your plugin package
const Name = "YourPlugin"

func New(ctx context.Context, args runtime.Object, h framework.Handle) (framework.Plugin, error) {
    // Plugin initialization
}
```

### Command Line Options

The scheduler inherits all standard kube-scheduler options plus plugin-specific configurations:

```bash
# Standard scheduler options
/kube-scheduler \
  --config=/path/to/scheduler-config.yaml \
  --v=2 \
  --leader-elect=false

# Configuration via KubeSchedulerConfiguration
```

## Controller Manager (`controller/`)

The controller manager handles Custom Resource Definitions (CRDs) and related controllers for plugins that require additional cluster-wide logic.

### Controller Structure
```go
// cmd/controller/app/controller.go
func NewControllerManagerCommand() *cobra.Command {
    // Set up controller manager with:
    // - CRD controllers for plugin-specific resources
    // - Webhooks for validation/mutation
    // - Metrics and health endpoints
}
```

### Common Controllers

#### For Coscheduling Plugin
- **PodGroup Controller**: Manages pod group lifecycle
- **Queue Controller**: Handles pod group queuing logic

#### For Capacity Scheduling Plugin  
- **ElasticQuota Controller**: Manages quota allocation and borrowing

#### For Network-Aware Plugins
- **AppGroup Controller**: Manages application group definitions
- **NetworkTopology Controller**: Handles network topology resources

### Controller Development Pattern

```go
// Example controller structure
type YourController struct {
    client.Client
    Scheme *runtime.Scheme
    Log    logr.Logger
}

func (r *YourController) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    // Reconciliation logic for your CRD
    return ctrl.Result{}, nil
}

func (r *YourController) SetupWithManager(mgr ctrl.Manager) error {
    return ctrl.NewControllerManagedBy(mgr).
        For(&yourv1alpha1.YourCRD{}).
        Complete(r)
}
```

## Testing (`scheduler/main_test.go`)

Contains comprehensive tests for scheduler setup and plugin registration.

### Test Structure
```go
func TestSetup(t *testing.T) {
    tests := []struct {
        name            string
        configFile      string
        registryOptions []app.Option
        wantPlugins     map[string]*config.Plugins
    }{
        {
            name: "plugin registration test",
            registryOptions: []app.Option{
                app.WithPlugin(constantscore.Name, constantscore.New),
            },
            wantPlugins: map[string]*config.Plugins{
                "default-scheduler": {
                    Score: config.PluginSet{
                        Enabled: []config.Plugin{{Name: constantscore.Name}},
                    },
                },
            },
        },
    }
}
```

### Configuration Testing

Tests various scheduler configurations:

#### Basic Plugin Configuration
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- plugins:
    score:
      enabled:
      - name: ConstantScore
      disabled:
      - name: "*"
```

#### Multiple Extension Points
```yaml
profiles:
- plugins:
    preFilter:
      enabled:
      - name: Coscheduling
    postFilter:
      enabled:
      - name: Coscheduling  
    permit:
      enabled:
      - name: Coscheduling
  pluginConfig:
  - name: Coscheduling
    args:
      permitWaitingTimeSeconds: 300
```

## Build Configuration

### Binary Output
- **Target**: `bin/kube-scheduler`
- **Build Command**: `make build-scheduler`
- **CGO**: Disabled for static linking
- **OS**: Linux (for container deployment)

### Linker Flags
```bash
CGO_ENABLED=0 GOOS=linux go build \
  -ldflags '-X k8s.io/component-base/version.gitVersion=$(VERSION) -w' \
  -o bin/kube-scheduler cmd/scheduler/main.go
```

### Version Information
- Version injected via `-ldflags` during build
- Uses `k8s.io/component-base/version` for consistency
- Default version format: `v0.0.YYYYMMDD`

## Development Workflow

### Adding a New Plugin

1. **Create Plugin Implementation**:
   ```bash
   mkdir pkg/yourplugin
   # Implement plugin following framework interfaces
   ```

2. **Register in Main**:
   ```go
   // cmd/scheduler/main.go
   import "sigs.k8s.io/scheduler-plugins/pkg/yourplugin"
   
   // Add to registration
   app.WithPlugin(yourplugin.Name, yourplugin.New),
   ```

3. **Add Configuration** (if needed):
   ```go
   // apis/config/types.go
   type YourPluginArgs struct {
       metav1.TypeMeta
       // Configuration fields
   }
   ```

4. **Add Tests**:
   ```go
   // cmd/scheduler/main_test.go
   // Add test case for your plugin
   ```

5. **Build and Test**:
   ```bash
   make build-scheduler
   make unit-test
   ```

### Testing Plugin Registration

```go
// Test that plugin is properly registered
func TestYourPluginRegistration(t *testing.T) {
    registry := app.NewInTreeRegistry()
    registry.Register(yourplugin.Name, yourplugin.New)
    
    factory := registry[yourplugin.Name]
    if factory == nil {
        t.Errorf("Plugin %s not registered", yourplugin.Name)
    }
    
    // Test plugin creation
    plugin, err := factory(context.Background(), nil, nil)
    if err != nil {
        t.Errorf("Failed to create plugin: %v", err)
    }
    
    if plugin.Name() != yourplugin.Name {
        t.Errorf("Expected plugin name %s, got %s", yourplugin.Name, plugin.Name())
    }
}
```

## Configuration Examples

### Single Plugin
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: constant-scheduler
  plugins:
    score:
      enabled:
      - name: ConstantScore
        weight: 100
      disabled:
      - name: "*"
  pluginConfig:
  - name: ConstantScore
    args:
      score: 75
```

### Multiple Plugins
```yaml
profiles:
- schedulerName: multi-plugin-scheduler
  plugins:
    queueSort:
      enabled:
      - name: TopologicalSort
    preFilter:
      enabled:
      - name: NetworkOverhead
      - name: Coscheduling
    filter:
      enabled:
      - name: NetworkOverhead
    score:
      enabled:
      - name: NetworkOverhead
        weight: 5
      - name: ConstantScore
        weight: 1
  pluginConfig:
  - name: NetworkOverhead
    args:
      namespaces: ["default"]
      weightsName: "UserDefined"
  - name: ConstantScore
    args:
      score: 50
```

## Common Issues and Solutions

### Plugin Not Loading
```
Error: plugin "YourPlugin" not found
```
**Solution**: Ensure plugin is imported and registered in `main.go`

### Configuration Parse Error
```
Error: cannot unmarshal plugin args
```
**Solution**: Check that plugin args type is registered in scheme and matches YAML structure

### Plugin Initialization Error
```
Error: failed to initialize plugin
```
**Solution**: Check plugin's `New()` function for proper error handling and validation

### Multiple Scheduler Profiles
```yaml
profiles:
- schedulerName: scheduler-1
  plugins:
    score:
      enabled: [...]
- schedulerName: scheduler-2  
  plugins:
    filter:
      enabled: [...]
```

This directory provides the main entry points and orchestration logic for the enhanced scheduler, bringing together all the plugin implementations into a cohesive scheduling system.