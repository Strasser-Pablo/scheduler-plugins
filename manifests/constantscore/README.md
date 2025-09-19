# ConstantScore Scheduler Plugin

This directory contains the configuration and deployment files for a scheduler that uses only the ConstantScore plugin, with all other plugins disabled (except essential ones for basic functionality).

## Files

- `scheduler-config.yaml` - ConfigMap containing the scheduler configuration
- `scheduler-config-standalone.yaml` - Standalone scheduler configuration file
- `scheduler-deployment.yaml` - Deployment manifest for the scheduler
- `README.md` - This file

## Configuration

The scheduler configuration does the following:

### Enabled Plugins

**Essential Filter Plugins** (minimal set needed for basic functionality):
- `NodeUnschedulable` - Filters out unschedulable nodes
- `NodeName` - Ensures pods are scheduled to the correct node when specified
- `TaintToleration` - Handles node taints and pod tolerations
- `NodeAffinity` - Handles node affinity rules

**Score Plugin**:
- `ConstantScore` - Our custom plugin that returns a constant score (configured to 75)

**Essential System Plugins**:
- `DefaultBinder` - Binds pods to nodes
- `PrioritySort` - Sorts pods by priority in the scheduling queue

### Disabled Plugins

All other plugins are explicitly disabled, including:
- All other score plugins (NodeResourcesFit, ImageLocality, etc.)
- PreFilter, PostFilter, Reserve, Permit, PreBind, PostBind plugins

## Quick Start with Makefile

The easiest way to test the ConstantScore plugin is using the provided Makefile targets:

```bash
# Complete test cycle (recommended)
make constantscore-full-test

# Or step by step:
make build                    # Build scheduler binary
make constantscore-image      # Build Docker image
make constantscore-deploy     # Deploy to kind cluster
make constantscore-test       # Run test pod
make constantscore-logs       # View scheduler logs
make constantscore-cleanup    # Clean up resources
```

### Requirements for Makefile approach:
- Docker
- kind cluster named `sched` (or customize with KIND_CLUSTER_NAME variable)
- kubectl configured to access the cluster

## Manual Usage

### Deploy the scheduler

1. Apply the ConfigMap:
   ```bash
   kubectl apply -f scheduler-config.yaml
   ```

2. Deploy the scheduler:
   ```bash
   kubectl apply -f scheduler-deployment.yaml
   ```

### Use the scheduler

To use this scheduler for your pods, specify the scheduler name in your pod spec:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  schedulerName: constantscore-scheduler
  containers:
  - name: test-container
    image: nginx
```

### Test the scheduler

1. Create a test pod:
   ```bash
   kubectl apply -f - <<EOF
   apiVersion: v1
   kind: Pod
   metadata:
     name: constantscore-test-pod
   spec:
     schedulerName: constantscore-scheduler
     containers:
     - name: nginx
       image: nginx:latest
   EOF
   ```

2. Check the scheduler logs to see the ConstantScore plugin in action:
   ```bash
   kubectl logs -n scheduler-plugins deployment/constantscore-scheduler
   ```

## Configuration Options

You can modify the constant score value by editing the `pluginConfig` section in the scheduler configuration:

```yaml
pluginConfig:
- name: ConstantScore
  args:
    score: 50  # Change this value (0-100)
```

## Notes

- This configuration ensures that all nodes receive the same score (75 by default) from the scoring phase
- The scheduler will still respect node filters (taints, affinity, etc.)
- Pods will be distributed based on the default tie-breaking mechanisms when all nodes have the same score
- This is useful for testing, debugging, or as a baseline for developing more complex scoring plugins