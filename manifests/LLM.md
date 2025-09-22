# LLM Guide: Kubernetes Manifests (`manifests/`)

This directory contains Kubernetes manifest templates and examples for deploying the scheduler plugins and their associated resources.

## Directory Structure

```
manifests/
├── appgroup/                      # AppGroup CRD for network-aware scheduling
├── capacityscheduling/            # ElasticQuota and capacity scheduling resources
├── constantscore/                 # ConstantScore plugin deployment manifests
│   ├── scheduler-config.yaml      # Scheduler configuration
│   ├── scheduler-deployment.yaml  # Scheduler deployment
│   └── test-pod.yaml             # Test pod for validation
├── coscheduling/                  # PodGroup CRD and coscheduling resources
├── crds/                          # Custom Resource Definitions
├── install/                       # Base installation manifests
│   ├── scheduler-serviceaccount.yaml
│   ├── scheduler-clusterrole.yaml
│   └── scheduler-clusterrolebinding.yaml
├── networktopology/               # NetworkTopology CRD for network-aware scheduling
├── noderesources/                 # Node resource plugin examples
├── noderesourcetopology/          # NodeResourceTopology CRD and examples
├── podstate/                      # Pod state plugin examples
├── qos/                          # QoS plugin examples
├── sysched/                      # System call scheduling examples
└── trimaran/                     # Load-aware scheduling examples
```

## Installation Manifests (`install/`)

Base RBAC and service account configuration required by all scheduler plugins.

### Service Account (`scheduler-serviceaccount.yaml`)
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: scheduler-plugins-scheduler
  namespace: scheduler-plugins
---
apiVersion: v1
kind: ServiceAccount  
metadata:
  name: scheduler-plugins-controller
  namespace: scheduler-plugins
```

### Cluster Role (`scheduler-clusterrole.yaml`)
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: scheduler-plugins-scheduler
rules:
# Standard scheduler permissions
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch", "update", "patch"]
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["events"]
  verbs: ["create", "patch", "update"]

# Plugin-specific permissions
- apiGroups: ["scheduling.x-k8s.io"]
  resources: ["podgroups", "elasticquotas"]
  verbs: ["get", "list", "watch", "create", "delete", "update", "patch"]
- apiGroups: ["topology.node.k8s.io"]
  resources: ["noderesourcetopologies"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["appgroup.diktyo.io"]
  resources: ["appgroups"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["networktopology.diktyo.io"]
  resources: ["networktopologies"]
  verbs: ["get", "list", "watch"]
```

### Cluster Role Binding (`scheduler-clusterrolebinding.yaml`)
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: scheduler-plugins-scheduler
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: scheduler-plugins-scheduler
subjects:
- kind: ServiceAccount
  name: scheduler-plugins-scheduler
  namespace: scheduler-plugins
```

## Plugin-Specific Manifests

### ConstantScore Plugin (`constantscore/`)

#### Scheduler Configuration (`scheduler-config.yaml`)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: constantscore-scheduler-config
  namespace: scheduler-plugins
data:
  config.yaml: |
    apiVersion: kubescheduler.config.k8s.io/v1
    kind: KubeSchedulerConfiguration
    leaderElection:
      leaderElect: false
    profiles:
    - schedulerName: constantscore-scheduler
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
          score: 0   # Return constant score of 0 for all nodes
```

#### Scheduler Deployment (`scheduler-deployment.yaml`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: constantscore-scheduler
  namespace: scheduler-plugins
spec:
  replicas: 1
  selector:
    matchLabels:
      app: constantscore-scheduler
  template:
    metadata:
      labels:
        app: constantscore-scheduler
    spec:
      serviceAccountName: scheduler-plugins-scheduler
      containers:
      - name: kube-scheduler
        image: constantscore-scheduler:latest
        imagePullPolicy: Never  # For local kind testing
        command:
        - /kube-scheduler
        - --config=/etc/kubernetes/scheduler-config.yaml
        - --v=2
        volumeMounts:
        - name: config
          mountPath: /etc/kubernetes
          readOnly: true
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
      volumes:
      - name: config
        configMap:
          name: constantscore-scheduler-config
```

#### Test Pod (`test-pod.yaml`)
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: constantscore-test-pod
  labels:
    app: constantscore-test
spec:
  schedulerName: constantscore-scheduler
  containers:
  - name: test-container
    image: busybox:1.35
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
  restartPolicy: Never
```

### Coscheduling Plugin (`coscheduling/`)

#### PodGroup CRD
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: podgroups.scheduling.x-k8s.io
spec:
  group: scheduling.x-k8s.io
  versions:
  - name: v1alpha1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              scheduleTimeoutSeconds:
                type: integer
                format: int32
              minMember:
                type: integer
                format: int32
              priorityClassName:
                type: string
          status:
            type: object
            properties:
              phase:
                type: string
              scheduled:
                type: integer
                format: int32
              running:
                type: integer
                format: int32
  scope: Namespaced
  names:
    plural: podgroups
    singular: podgroup
    kind: PodGroup
```

#### Example PodGroup
```yaml
apiVersion: scheduling.x-k8s.io/v1alpha1
kind: PodGroup
metadata:
  name: web-service-group
  namespace: default
spec:
  scheduleTimeoutSeconds: 300
  minMember: 3
  priorityClassName: high-priority
```

#### Coscheduling Configuration
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: coscheduling-scheduler
  plugins:
    multiPoint:
      enabled:
      - name: Coscheduling
    queueSort:
      disabled:
      - name: "*"
  pluginConfig:
  - name: Coscheduling
    args:
      permitWaitingTimeSeconds: 300
      podGroupBackoffSeconds: 10
```

### Network-Aware Scheduling (`networkaware/`)

#### AppGroup CRD (`appgroup/`)
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: appgroups.appgroup.diktyo.io
spec:
  group: appgroup.diktyo.io
  versions:
  - name: v1alpha1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              numMembers:
                type: integer
                format: int32
              topologySpreadConstraints:
                type: array
                items:
                  type: object
              workloads:
                type: object
                additionalProperties:
                  type: object
  scope: Namespaced
  names:
    plural: appgroups
    singular: appgroup
    kind: AppGroup
```

#### NetworkTopology CRD (`networktopology/`)
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: networktopologies.networktopology.diktyo.io
spec:
  group: networktopology.diktyo.io
  versions:
  - name: v1alpha1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              nodeSelector:
                type: object
              costs:
                type: array
                items:
                  type: object
                  properties:
                    origin:
                      type: string
                    destination:
                      type: string
                    networkCost:
                      type: integer
                      format: int64
  scope: Namespaced
  names:
    plural: networktopologies
    singular: networktopology
    kind: NetworkTopology
```

## Deployment Patterns

### Single Plugin Deployment
```yaml
# Deploy only one plugin with specific configuration
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: single-plugin-scheduler
  plugins:
    score:
      enabled:
      - name: ConstantScore
      disabled:
      - name: "*"  # Disable all other scoring plugins
  pluginConfig:
  - name: ConstantScore
    args:
      score: 75
```

### Multi-Plugin Deployment
```yaml
# Deploy multiple plugins with different weights
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
        weight: 10  # Higher weight for network awareness
      - name: ConstantScore
        weight: 1   # Lower weight for baseline
  pluginConfig:
  - name: NetworkOverhead
    args:
      namespaces: ["production", "staging"]
  - name: ConstantScore
    args:
      score: 50
```

### Secondary Scheduler Deployment
```yaml
# Deploy as secondary scheduler alongside default
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secondary-scheduler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: secondary-scheduler
  template:
    spec:
      containers:
      - name: kube-scheduler
        image: registry.k8s.io/scheduler-plugins/kube-scheduler:v0.33.3
        command:
        - /kube-scheduler
        - --config=/etc/kubernetes/scheduler-config.yaml
        - --leader-elect=true
        - --leader-elect-resource-name=secondary-scheduler
        - --leader-elect-resource-namespace=kube-system
```

## Testing and Validation

### Pod with Specific Scheduler
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  schedulerName: constantscore-scheduler  # Use custom scheduler
  containers:
  - name: test-container
    image: nginx:1.20
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
```

### Pod with Plugin-Specific Annotations
```yaml
# For coscheduling
apiVersion: v1
kind: Pod
metadata:
  name: gang-member-pod
  annotations:
    scheduling.x-k8s.io/pod-group: "web-service-group"
spec:
  schedulerName: coscheduling-scheduler
  containers:
  - name: web-server
    image: nginx:1.20
```

### Load Testing Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scheduler-load-test
spec:
  replicas: 50
  selector:
    matchLabels:
      app: load-test
  template:
    metadata:
      labels:
        app: load-test
    spec:
      schedulerName: constantscore-scheduler
      containers:
      - name: test-workload
        image: busybox:1.35
        command: ["sleep", "600"]
        resources:
          requests:
            cpu: 10m
            memory: 16Mi
```

## Usage with Makefile

The ConstantScore manifests integrate with the specialized Makefile:

```bash
# Deploy ConstantScore scheduler
make constantscore-deploy

# Run test pod
make constantscore-test

# View logs
make constantscore-logs

# Clean up
make constantscore-cleanup
```

## Common Configuration Patterns

### Development Environment
- Use `imagePullPolicy: Never` for local images
- Set low resource requests/limits
- Enable verbose logging (`--v=4`)
- Disable leader election for single-node testing

### Production Environment
- Use versioned container images from registry
- Set appropriate resource limits
- Enable leader election
- Configure monitoring and alerting
- Use multiple replicas for high availability

### Multi-Tenant Environment
- Use different scheduler names per tenant
- Configure namespace-specific plugin behavior
- Set up proper RBAC isolation
- Monitor resource usage per scheduler

These manifests provide a complete foundation for deploying and testing scheduler plugins in various Kubernetes environments.