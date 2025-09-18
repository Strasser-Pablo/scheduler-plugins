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

## Makefile Usage and Automation

This repository provides a comprehensive `Makefile` to automate building, testing, and deploying scheduler-plugins, including local development and Kubernetes-in-Kind workflows.

### Key Targets

- **build**: Builds both the controller and scheduler binaries.
- **build-images**: Builds Docker images for the scheduler and controller.
- **local-image**: Builds images for the local architecture and loads them for local testing.
- **unit-test**: Runs unit tests.
- **integration-test**: Runs integration tests.
- **verify**: Runs all verification scripts (formatting, codegen, etc).
- **clean**: Cleans build artifacts.
- **kind-deploy-test**: Fully automates the build, image load, CRD install, deployment, and test pod scheduling in a local [kind](https://kind.sigs.k8s.io/) cluster.

### Automated Kind Deployment & Test

The `kind-deploy-test` target is the recommended way to build, deploy, and validate the scheduler-plugins in a local kind cluster. It performs the following steps:

1. Builds scheduler and controller images for your local architecture.
2. Loads these images into the kind cluster named `sched`.
3. Installs all required CRDs.
4. Deploys all scheduler-plugins manifests (RBAC, ConfigMap, Deployment, etc).
5. Deploys a test pod that uses the custom scheduler.
6. Waits for the test pod to become ready and prints its status.

#### Usage Example

```sh
make kind-deploy-test
```

**Requirements:**
- Docker (with buildx support)
- [kind](https://kind.sigs.k8s.io/) cluster named `sched` running
- kubectl configured to access the kind cluster

**What happens:**
- Images are built and loaded into kind
- All manifests and CRDs are applied
- A test pod is scheduled and its status is shown

If the test pod is `Running` and `Ready`, the deployment is successful.

#### Proxy Configuration

If you encounter Go module download issues, you can set a Go proxy before running the Makefile:

```sh
go env -w GOPROXY=https://proxy.golang.org,direct
# or for China: go env -w GOPROXY=https://goproxy.cn,direct
```

### For LLMs and Automation

- Always use the `kind-deploy-test` target for end-to-end local validation.
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

## Community, discussion, contribution, and support

Learn how to engage with the Kubernetes community on the [community page](http://kubernetes.io/community/).

You can reach the maintainers of this project at:

- [Slack](https://kubernetes.slack.com/messages/sig-scheduling)
- [Mailing List](https://groups.google.com/forum/#!forum/kubernetes-sig-scheduling)

You can find an [instruction how to build and run out-of-tree plugin here](doc/develop.md) .

### Code of conduct

Participation in the Kubernetes community is governed by the [Kubernetes Code of Conduct](code-of-conduct.md).
