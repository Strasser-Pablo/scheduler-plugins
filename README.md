[![Go Report Card](https://goreportcard.com/badge/kubernetes-sigs/scheduler-plugins)](https://goreportcard.com/report/kubernetes-sigs/scheduler-plugins) [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/kubernetes-sigs/scheduler-plugins/blob/master/LICENSE)

# Scheduler Plugins

Repository for out-of-tree scheduler plugins based on the [scheduler framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/).

This repo provides scheduler plugins that are exercised in large companies.
These plugins can be vendored as Golang SDK libraries or used out-of-box via the pre-built images or Helm charts.
Additionally, this repo incorporates best practices and utilities to compose a high-quality scheduler plugin.

## Install

Container images are available in the official scheduler-plugins k8s container registry. There are two images one
for the kube-scheduler and one for the controller. See the [Compatibility Matrix section](#compatibility-matrix)
for the complete list of images.

```shell
docker pull registry.k8s.io/scheduler-plugins/kube-scheduler:$TAG
docker pull registry.k8s.io/scheduler-plugins/controller:$TAG
```

## ConstantScore Plugin Makefile

This repository has been configured with a specialized `Makefile` focused on building, testing, and deploying the **ConstantScore** scheduler plugin, including automated workflows for local development with Kubernetes-in-Kind.

### Key Targets

- **build**: Builds the scheduler binary with ConstantScore plugin.
- **constantscore-image**: Builds the ConstantScore Docker image.
- **constantscore-load-kind**: Loads the image into a kind cluster.
- **constantscore-deploy**: Deploys ConstantScore scheduler to kind cluster.
- **constantscore-test**: Runs the ConstantScore test pod.
- **constantscore-full-test**: Complete test cycle (cleanup, deploy, test, logs).
- **unit-test**: Runs unit tests.
- **integration-test**: Runs integration tests.
- **verify**: Runs all verification scripts (formatting, codegen, etc).
- **clean**: Cleans build artifacts.
- **help**: Shows all available targets and configuration options.

## HyperAI Plugin Makefile


The repository also includes full support for the **HyperAI** plugin, which connects to a Python gRPC server for advanced node scoring. The plugin supports multiple deployment architectures including sidecar, service, and **DaemonSet** deployments.

**Protocol Note:**
The HyperAI plugin sends the full Pod and Node specs as JSON strings in the gRPC request, not just names. See `pkg/hyperai/README.md` for details and proto example.

### HyperAI Architecture Options

**DaemonSet Deployment (Recommended for Production)**: Node agents run on every node via DaemonSet for distributed, node-specific scoring
**Sidecar Deployment**: Scheduler and gRPC server run in the same pod for minimal latency
**Service Deployment**: gRPC server runs as separate service for independent scaling

### HyperAI Targets

- **hyperai-proto**: Generates gRPC code for both Go and Python.
- **hyperai-image**: Builds the HyperAI Docker image.
- **hyperai-load-kind**: Loads the image into a kind cluster.
- **hyperai-daemonset-deploy**: Deploys HyperAI scheduler with DaemonSet node agents (recommended for production).
- **hyperai-daemonset-test**: Runs test pod with DaemonSet architecture.
- **hyperai-daemonset-full-test**: Complete DaemonSet test cycle.
- **hyperai-sidecar-deploy**: Deploys HyperAI scheduler with sidecar gRPC server.
- **hyperai-sidecar-test**: Runs test pod with sidecar scheduler.
- **hyperai-sidecar-full-test**: Complete sidecar test cycle.
- **hyperai-deploy**: Deploys HyperAI scheduler with separate gRPC service.
- **hyperai-test**: Runs the HyperAI test pod.
- **hyperai-full-test**: Complete test cycle with separate gRPC service.
- **hyperai-start-grpc**: Starts the Python gRPC server locally.
- **hyperai-stop-grpc**: Stops the Python gRPC server.
- **hyperai-test-grpc**: Tests gRPC connectivity.

### HyperAI Image Optimization

The HyperAI targets include automatic optimization for the NVIDIA Triton server image (~9GB) used in production deployments. When using `hyperai-deploy` or related targets, the system:

1. **Single Download**: Pulls the Triton image once during the build phase
2. **Kind Integration**: Loads the image into the kind cluster's internal registry using `kind load docker-image`
3. **Cached Deployment**: DaemonSet pods use `imagePullPolicy: Never` to ensure they use the locally cached image
4. **Bandwidth Efficiency**: Eliminates redundant downloads across multiple nodes

This optimization significantly reduces deployment time and network usage, especially beneficial for development environments where deployments happen frequently.

### HyperAI Quick Start (DaemonSet - Production)

The `hyperai-daemonset-full-test` target is the recommended way to build, deploy, and validate the HyperAI plugin with DaemonSet architecture for production-like deployments:

```bash
make hyperai-daemonset-full-test
```

This performs:
1. Builds scheduler binary with HyperAI plugin
2. Builds and loads Docker images (scheduler + gRPC server + node agents) into kind cluster
3. Deploys HyperAI scheduler with sidecar gRPC server
4. Deploys node agent DaemonSet on all nodes
5. Runs test pod to validate distributed node-specific scoring
6. Shows logs confirming node-specific gRPC routing and scoring

### HyperAI Quick Start (Sidecar - Development)

The `hyperai-sidecar-full-test` target provides a simpler development setup:

```bash
make hyperai-sidecar-full-test
```

### HyperAI Development

**Prerequisites**: The devcontainer includes all required Python dependencies:
- **PyTorch 2.8.0+** - For ML model generation and training
- **gRPC 1.75.0+** - For scheduler-server communication
- **Kubernetes client** - For node discovery and API access
- **Triton client** - For NVIDIA Triton inference integration
- **NumPy, ONNX** - For numerical operations and model export

```bash
# Generate gRPC code
make hyperai-proto

# Test gRPC connectivity locally
make hyperai-start-grpc
make hyperai-test-grpc  # Should return score=88
make hyperai-stop-grpc

# Deploy and test DaemonSet (recommended for production)
make hyperai-daemonset-full-test

# Deploy and test sidecar (recommended for development)
make hyperai-sidecar-full-test

# Deploy and test separate service
make hyperai-full-test
```

### ConstantScore Quick Start

The `constantscore-full-test` target is the recommended way to build, deploy, and validate the ConstantScore plugin in a local kind cluster. It performs the following steps:

1. Cleans up any existing ConstantScore deployments.
2. Builds the scheduler binary with ConstantScore plugin.
3. Builds and loads the Docker image into the kind cluster.
4. Sets up necessary RBAC and namespace.
5. Deploys the ConstantScore scheduler.
6. Runs a test pod to validate scheduling.
7. Shows logs with constant score messages.

#### Usage Example

```sh
# Quick test - runs the complete cycle
make constantscore-full-test

# Or step by step
make build
make constantscore-image
make constantscore-deploy
make constantscore-test
make constantscore-logs
```

#### Configuration Variables

You can customize the behavior by setting these variables:

```sh
# Custom image name and tag
make constantscore-full-test CONSTANTSCORE_IMAGE_NAME=my-scheduler CONSTANTSCORE_IMAGE_TAG=v1.0.0

# Different kind cluster name
make constantscore-full-test KIND_CLUSTER_NAME=my-cluster
```

**Requirements:**
- Docker
- [kind](https://kind.sigs.k8s.io/) cluster named `sched` running (or customize with KIND_CLUSTER_NAME)
- kubectl configured to access the kind cluster

**What happens:**
- The scheduler binary is built with ConstantScore plugin
- Docker image is built using Dockerfile.constantscore
- Image is loaded into the kind cluster
- Namespace and RBAC are configured
- ConstantScore scheduler is deployed
- Test pod is scheduled using the ConstantScore scheduler
- Logs are displayed showing constant score scheduling decisions

If the test pod is `Running` and `Ready`, and you see "Returning constant score" messages in the logs, the deployment is successful.

#### Proxy Configuration

If you encounter Go module download issues, you can set a Go proxy before running the Makefile:

```sh
go env -w GOPROXY=https://proxy.golang.org,direct
# or for China: go env -w GOPROXY=https://goproxy.cn,direct
```

### For LLMs and Automation

- Always use the `constantscore-full-test` target for end-to-end local validation of the ConstantScore plugin.
- Use `make help` to see all available targets and configuration options.
- Ensure all prerequisites (Docker, kind, kubectl) are met.
- The Makefile is self-documenting; inspect it for more targets and details.

For more details on development workflows, see [doc/develop.md](doc/develop.md).

You can find [how to install release image](doc/install.md) here.

## Plugins

The kube-scheduler binary includes the below list of plugins. They can be configured by creating one or more
[scheduler profiles](https://kubernetes.io/docs/reference/scheduling/config/#multiple-profiles).

* [Capacity Scheduling](pkg/capacityscheduling/README.md)
* [Coscheduling](pkg/coscheduling/README.md)
* [Node Resources](pkg/noderesources/README.md)
* [Node Resource Topology](pkg/noderesourcetopology/README.md)
* [Preemption Toleration](pkg/preemptiontoleration/README.md)
* [Trimaran (Load-Aware Scheduling)](pkg/trimaran/README.md)
* [Network-Aware Scheduling](pkg/networkaware/README.md)

Additionally, the kube-scheduler binary includes the below list of sample plugins. These plugins are not intended for use in production
environments.

* [Cross Node Preemption](pkg/crossnodepreemption/README.md)
* [Pod State](pkg/podstate/README.md)
* [Quality of Service](pkg/qos/README.md)
* [HyperAI](pkg/hyperai/README.md)

## Compatibility Matrix

The below compatibility matrix shows the k8s client package (client-go, apimachinery, etc) versions
that the scheduler-plugins are compiled with.

The minor version of the scheduler-plugins matches the minor version of the k8s client packages that
it is compiled with. For example scheduler-plugins `v0.18.x` releases are built with k8s `v1.18.x`
dependencies.

The scheduler-plugins patch versions come in two different varieties (single digit or three digits).
The single digit patch versions (e.g., `v0.18.9`) exactly align with the k8s client package
versions that the scheduler plugins are built with. The three digit patch versions, which are built
on demand, (e.g., `v0.18.800`) are used to indicated that the k8s client package versions have not
changed since the previous release, and that only scheduler plugins code (features or bug fixes) was
changed.

| Scheduler Plugins | Compiled With k8s Version | Container Image                                           | Arch                                                       |
|-------------------|---------------------------|-----------------------------------------------------------|------------------------------------------------------------|
| v0.32.7           | v1.32.7                   | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.32.7  | linux/amd64<br>linux/arm64<br>linux/s390x<br>linux/ppc64le |
| v0.31.8           | v1.31.8                   | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.31.8  | linux/amd64<br>linux/arm64<br>linux/s390x<br>linux/ppc64le |
| v0.30.12          | v1.30.12                  | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.30.12 | linux/amd64<br>linux/arm64<br>linux/s390x<br>linux/ppc64le |

| Controller | Compiled With k8s Version | Container Image                                       | Arch                                                       |
|------------|---------------------------|-------------------------------------------------------|------------------------------------------------------------|
| v0.32.7    | v1.32.7                   | registry.k8s.io/scheduler-plugins/controller:v0.32.7  | linux/amd64<br>linux/arm64<br>linux/s390x<br>linux/ppc64le |
| v0.31.8    | v1.31.8                   | registry.k8s.io/scheduler-plugins/controller:v0.31.8  | linux/amd64<br>linux/arm64<br>linux/s390x<br>linux/ppc64le |
| v0.30.12   | v1.30.12                  | registry.k8s.io/scheduler-plugins/controller:v0.30.12 | linux/amd64<br>linux/arm64<br>linux/s390x<br>linux/ppc64le |

<details>
<summary>Older releases</summary>

| Scheduler Plugins | Compiled With k8s Version | Container Image                                           | Arch                                                       |
|-------------------|---------------------------|-----------------------------------------------------------|------------------------------------------------------------|
| v0.29.7           | v1.29.7                   | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.29.7  | linux/amd64<br>linux/arm64<br>linux/s390x<br>linux/ppc64le |
| v0.28.9           | v1.28.9                   | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.28.9  | linux/amd64<br>linux/arm64                                 |
| v0.27.8           | v1.27.8                   | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.27.8  | linux/amd64<br>linux/arm64                                 |
| v0.26.7           | v1.26.7                   | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.26.7  | linux/amd64<br>linux/arm64                                 |
| v0.25.12          | v1.25.12                  | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.25.12 | linux/amd64<br>linux/arm64                                 |
| v0.24.9           | v1.24.9                   | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.24.9  | linux/amd64<br>linux/arm64                                 |
| v0.23.10          | v1.23.10                  | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.23.10 | linux/amd64<br>linux/arm64                                 |
| v0.22.6           | v1.22.6                   | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.22.6  | linux/amd64<br>linux/arm64                                 |
| v0.21.6           | v1.21.6                   | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.21.6  | linux/amd64<br>linux/arm64                                 |
| v0.20.10          | v1.20.10                  | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.20.10 | linux/amd64<br>linux/arm64                                 |
| v0.19.9           | v1.19.9                   | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.19.9  | linux/amd64<br>linux/arm64                                 |
| v0.19.8           | v1.19.8                   | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.19.8  | linux/amd64<br>linux/arm64                                 |
| v0.18.9           | v1.18.9                   | registry.k8s.io/scheduler-plugins/kube-scheduler:v0.18.9  | linux/amd64                                                |

| Controller | Compiled With k8s Version | Container Image                                       | Arch                                                       |
|------------|---------------------------|-------------------------------------------------------|------------------------------------------------------------|
| v0.29.7    | v1.29.7                   | registry.k8s.io/scheduler-plugins/controller:v0.29.7  | linux/amd64<br>linux/arm64<br>linux/s390x<br>linux/ppc64le |
| v0.28.9    | v1.28.9                   | registry.k8s.io/scheduler-plugins/controller:v0.28.9  | linux/amd64<br>linux/arm64                                 |
| v0.27.8    | v1.27.8                   | registry.k8s.io/scheduler-plugins/controller:v0.27.8  | linux/amd64<br>linux/arm64                                 |
| v0.26.7    | v1.26.7                   | registry.k8s.io/scheduler-plugins/controller:v0.26.7  | linux/amd64<br>linux/arm64                                 |
| v0.25.12   | v1.25.12                  | registry.k8s.io/scheduler-plugins/controller:v0.25.12 | linux/amd64<br>linux/arm64                                 |
| v0.24.9    | v1.24.9                   | registry.k8s.io/scheduler-plugins/controller:v0.24.9  | linux/amd64<br>linux/arm64                                 |
| v0.23.10   | v1.23.10                  | registry.k8s.io/scheduler-plugins/controller:v0.23.10 | linux/amd64<br>linux/arm64                                 |
| v0.22.6    | v1.22.6                   | registry.k8s.io/scheduler-plugins/controller:v0.22.6  | linux/amd64<br>linux/arm64                                 |
| v0.21.6    | v1.21.6                   | registry.k8s.io/scheduler-plugins/controller:v0.21.6  | linux/amd64<br>linux/arm64                                 |
| v0.20.10   | v1.20.10                  | registry.k8s.io/scheduler-plugins/controller:v0.20.10 | linux/amd64<br>linux/arm64                                 |
| v0.19.9    | v1.19.9                   | registry.k8s.io/scheduler-plugins/controller:v0.19.9  | linux/amd64<br>linux/arm64                                 |
| v0.19.8    | v1.19.8                   | registry.k8s.io/scheduler-plugins/controller:v0.19.8  | linux/amd64<br>linux/arm64                                 |

</details>

## LLM Development Assistant

For AI/LLM assistance with this repository, see **[LLM.md](LLM.md)** - a comprehensive guide containing:

- **Repository architecture and structure**
- **Plugin development patterns and best practices** 
- **Build system and testing workflows**
- **Configuration examples and common patterns**
- **Troubleshooting guides and development tips**

Additional LLM guides are available in key directories:
- `pkg/LLM.md` - Plugin implementation details
- `apis/LLM.md` - Configuration and API types
- `cmd/LLM.md` - Main applications and entry points
- `hack/LLM.md` - Build scripts and automation
- `manifests/LLM.md` - Kubernetes deployment manifests

## Community, discussion, contribution, and support

Learn how to engage with the Kubernetes community on the [community page](http://kubernetes.io/community/).

You can reach the maintainers of this project at:

- [Slack](https://kubernetes.slack.com/messages/sig-scheduling)
- [Mailing List](https://groups.google.com/forum/#!forum/kubernetes-sig-scheduling)

You can find an [instruction how to build and run out-of-tree plugin here](doc/develop.md) .

### Code of conduct

Participation in the Kubernetes community is governed by the [Kubernetes Code of Conduct](code-of-conduct.md).
