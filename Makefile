# ConstantScore Plugin Makefile
# Focused build system for the ConstantScore scheduler plugin
#
# Copyright 2020 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

GO_VERSION := $(shell awk '/^go /{print $$2}' go.mod|head -n1)
INTEGTESTENVVAR=SCHED_PLUGINS_TEST_VERBOSE=1

# ConstantScore specific configuration
CONSTANTSCORE_IMAGE_NAME ?= constantscore-scheduler
CONSTANTSCORE_IMAGE_TAG ?= latest

# HyperAI specific configuration
HYPERAI_IMAGE_NAME ?= hyperai-scheduler
HYPERAI_IMAGE_TAG ?= latest

KIND_CLUSTER_NAME ?= sched

# VERSION is the scheduler's version
VERSION ?= v0.0.$(shell date +%Y%m%d)

.PHONY: all
all: build

.PHONY: build
build: build-scheduler

.PHONY: build-scheduler
build-scheduler:
	CGO_ENABLED=0 GOOS=linux $(GO_BUILD_ENV) go build -ldflags '-X k8s.io/component-base/version.gitVersion=$(VERSION) -w' -o bin/kube-scheduler cmd/scheduler/main.go

# ConstantScore specific targets
.PHONY: constantscore-image
constantscore-image: build-scheduler
	docker build -f Dockerfile.constantscore -t $(CONSTANTSCORE_IMAGE_NAME):$(CONSTANTSCORE_IMAGE_TAG) .

.PHONY: constantscore-load-kind
constantscore-load-kind: constantscore-image
	kind load docker-image $(CONSTANTSCORE_IMAGE_NAME):$(CONSTANTSCORE_IMAGE_TAG) --name $(KIND_CLUSTER_NAME)

.PHONY: constantscore-setup-rbac
constantscore-setup-rbac:
	@echo "Setting up namespace and RBAC for ConstantScore..."
	kubectl get ns scheduler-plugins >/dev/null 2>&1 || kubectl create ns scheduler-plugins
	kubectl apply -f manifests/install/scheduler-serviceaccount.yaml
	kubectl apply -f manifests/install/scheduler-clusterrole.yaml
	kubectl apply -f manifests/install/scheduler-clusterrolebinding.yaml

.PHONY: constantscore-deploy
constantscore-deploy: constantscore-load-kind constantscore-setup-rbac
	@echo "Deploying ConstantScore scheduler..."
	kubectl apply -f manifests/constantscore/scheduler-config.yaml
	kubectl apply -f manifests/constantscore/scheduler-deployment.yaml
	kubectl -n scheduler-plugins rollout status deploy/constantscore-scheduler --timeout=120s

.PHONY: constantscore-test
constantscore-test: constantscore-deploy
	@echo "Running ConstantScore test pod..."
	kubectl apply -f manifests/constantscore/test-pod.yaml
	kubectl wait --for=condition=Ready pod/constantscore-test-pod --timeout=90s
	@echo "Test pod deployed successfully!"
	kubectl get pod constantscore-test-pod -o wide

.PHONY: constantscore-logs
constantscore-logs:
	@echo "Fetching ConstantScore scheduler logs..."
	kubectl -n scheduler-plugins logs deploy/constantscore-scheduler --tail=200 | grep -i "Returning constant score" || true

.PHONY: constantscore-cleanup
constantscore-cleanup:
	@echo "Cleaning up ConstantScore resources..."
	kubectl delete -f manifests/constantscore/test-pod.yaml --ignore-not-found=true
	kubectl delete -f manifests/constantscore/scheduler-deployment.yaml --ignore-not-found=true
	kubectl delete -f manifests/constantscore/scheduler-config.yaml --ignore-not-found=true

.PHONY: constantscore-full-test
constantscore-full-test: constantscore-cleanup constantscore-test constantscore-logs

# HyperAI specific targets
.PHONY: hyperai-proto
hyperai-proto:
	@echo "Generating gRPC code for HyperAI..."
	cd hack/hyperai-grpc && python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. hyperai.proto
	cd pkg/hyperai && protoc --go_out=. --go-grpc_out=. -I../../hack/hyperai-grpc ../../hack/hyperai-grpc/hyperai.proto
	cd pkg/hyperai && mv sigs.k8s.io/scheduler-plugins/pkg/hyperai/*.go . && rm -rf sigs.k8s.io || true

.PHONY: hyperai-image
hyperai-image: build-scheduler
	docker build -f Dockerfile.constantscore -t $(HYPERAI_IMAGE_NAME):$(HYPERAI_IMAGE_TAG) .

.PHONY: hyperai-grpc-image
hyperai-grpc-image:
	@echo "Building HyperAI gRPC server image..."
	cd hack/hyperai-grpc && docker build -t hyperai-grpc-server:latest .

.PHONY: hyperai-load-kind
hyperai-load-kind: hyperai-image hyperai-grpc-image
	kind load docker-image $(HYPERAI_IMAGE_NAME):$(HYPERAI_IMAGE_TAG) --name $(KIND_CLUSTER_NAME)
	kind load docker-image hyperai-grpc-server:latest --name $(KIND_CLUSTER_NAME)

.PHONY: hyperai-setup-rbac
hyperai-setup-rbac:
	@echo "Setting up namespace and RBAC for HyperAI..."
	kubectl get ns scheduler-plugins >/dev/null 2>&1 || kubectl create ns scheduler-plugins
	kubectl apply -f manifests/install/scheduler-serviceaccount.yaml
	kubectl apply -f manifests/install/scheduler-clusterrole.yaml
	kubectl apply -f manifests/install/scheduler-clusterrolebinding.yaml

.PHONY: hyperai-start-grpc
hyperai-start-grpc:
	@echo "Starting HyperAI Python gRPC server..."
	cd hack/hyperai-grpc && python3 server.py &
	@echo "Waiting for gRPC server to start..."
	sleep 3

.PHONY: hyperai-stop-grpc
hyperai-stop-grpc:
	@echo "Stopping HyperAI Python gRPC server..."
	pkill -f "python3 server.py" || true

.PHONY: hyperai-test-grpc
hyperai-test-grpc:
	@echo "Testing HyperAI gRPC connection..."
	cd hack/hyperai-grpc && python3 test_client.py

.PHONY: hyperai-deploy
hyperai-deploy: hyperai-load-kind hyperai-setup-rbac
	@echo "Deploying HyperAI gRPC server..."
	kubectl apply -f manifests/hyperai/grpc-server.yaml
	kubectl -n scheduler-plugins rollout status deploy/hyperai-grpc-server --timeout=120s
	@echo "Deploying HyperAI scheduler..."
	kubectl apply -f manifests/hyperai/scheduler-config.yaml
	kubectl apply -f manifests/hyperai/scheduler-deployment.yaml
	kubectl -n scheduler-plugins rollout status deploy/hyperai-scheduler --timeout=120s

.PHONY: hyperai-test
hyperai-test: hyperai-deploy
	@echo "Running HyperAI test pod..."
	kubectl apply -f manifests/hyperai/test-pod.yaml
	kubectl wait --for=condition=Ready pod/hyperai-test-pod --timeout=90s
	@echo "Test pod deployed successfully!"
	kubectl get pod hyperai-test-pod -o wide

.PHONY: hyperai-logs
hyperai-logs:
	@echo "Fetching HyperAI scheduler logs..."
	kubectl -n scheduler-plugins logs deploy/hyperai-scheduler --tail=200 | grep -i "hyperai\|grpc\|score" || true

.PHONY: hyperai-cleanup
hyperai-cleanup:
	@echo "Cleaning up HyperAI resources..."
	kubectl delete -f manifests/hyperai/test-pod.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/scheduler-deployment.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/scheduler-config.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/grpc-server.yaml --ignore-not-found=true

.PHONY: hyperai-full-test
hyperai-full-test: hyperai-cleanup hyperai-start-grpc hyperai-test hyperai-logs hyperai-stop-grpc

# HyperAI Sidecar targets
.PHONY: hyperai-sidecar-deploy
hyperai-sidecar-deploy: hyperai-load-kind hyperai-setup-rbac
	@echo "Deploying HyperAI scheduler with sidecar gRPC server..."
	kubectl apply -f manifests/hyperai/scheduler-config-sidecar.yaml
	kubectl apply -f manifests/hyperai/scheduler-deployment-sidecar.yaml
	kubectl -n scheduler-plugins rollout status deploy/hyperai-scheduler-sidecar --timeout=120s

.PHONY: hyperai-sidecar-test
hyperai-sidecar-test: hyperai-sidecar-deploy
	@echo "Running HyperAI sidecar test pod..."
	kubectl apply -f manifests/hyperai/test-pod-sidecar.yaml
	kubectl wait --for=condition=Ready pod/hyperai-test-pod-sidecar --timeout=90s
	@echo "Sidecar test pod deployed successfully!"
	kubectl get pod hyperai-test-pod-sidecar -o wide

.PHONY: hyperai-sidecar-logs
hyperai-sidecar-logs:
	@echo "Fetching HyperAI sidecar scheduler logs..."
	kubectl -n scheduler-plugins logs deploy/hyperai-scheduler-sidecar -c kube-scheduler --tail=200 | grep -i "hyperai\|grpc\|score" || true

.PHONY: hyperai-sidecar-cleanup
hyperai-sidecar-cleanup:
	@echo "Cleaning up HyperAI sidecar resources..."
	kubectl delete -f manifests/hyperai/test-pod-sidecar.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/scheduler-deployment-sidecar.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/scheduler-config-sidecar.yaml --ignore-not-found=true

.PHONY: hyperai-sidecar-full-test
hyperai-sidecar-full-test: hyperai-sidecar-cleanup hyperai-sidecar-test hyperai-sidecar-logs

# HyperAI DaemonSet targets
.PHONY: hyperai-node-agent-image
hyperai-node-agent-image:
	@echo "Building HyperAI Node Agent image..."
	cd hack/hyperai-grpc && docker build -f Dockerfile.node-agent -t hyperai-node-agent:latest .

.PHONY: hyperai-daemonset-load-kind
hyperai-daemonset-load-kind: hyperai-image hyperai-grpc-image hyperai-node-agent-image
	kind load docker-image $(HYPERAI_IMAGE_NAME):$(HYPERAI_IMAGE_TAG) --name $(KIND_CLUSTER_NAME)
	kind load docker-image hyperai-grpc-server:latest --name $(KIND_CLUSTER_NAME)
	kind load docker-image hyperai-node-agent:latest --name $(KIND_CLUSTER_NAME)

.PHONY: hyperai-daemonset-setup-rbac
hyperai-daemonset-setup-rbac: hyperai-setup-rbac
	@echo "Setting up RBAC for HyperAI DaemonSet..."
	kubectl apply -f manifests/hyperai/node-agent-rbac.yaml

.PHONY: hyperai-daemonset-deploy
hyperai-daemonset-deploy: hyperai-daemonset-load-kind hyperai-daemonset-setup-rbac
	@echo "Deploying HyperAI DaemonSet architecture..."
	kubectl apply -f manifests/hyperai/scheduler-config-sidecar.yaml
	kubectl apply -f manifests/hyperai/scheduler-deployment-sidecar.yaml
	kubectl -n scheduler-plugins rollout status deploy/hyperai-scheduler-sidecar --timeout=120s
	@echo "Deploying Node Agent DaemonSet..."
	kubectl apply -f manifests/hyperai/node-agent-service.yaml
	kubectl apply -f manifests/hyperai/node-agent-daemonset.yaml
	kubectl -n scheduler-plugins rollout status daemonset/hyperai-node-agent --timeout=120s

.PHONY: hyperai-daemonset-test
hyperai-daemonset-test: hyperai-daemonset-deploy
	@echo "Running HyperAI DaemonSet test pod..."
	kubectl apply -f manifests/hyperai/test-pod-with-agent.yaml
	kubectl wait --for=condition=Ready pod/hyperai-test-pod-daemonset --timeout=120s
	@echo "DaemonSet test pod deployed successfully!"
	kubectl get pod hyperai-test-pod-daemonset -o wide

.PHONY: hyperai-daemonset-logs
hyperai-daemonset-logs:
	@echo "Fetching HyperAI DaemonSet logs..."
	kubectl -n scheduler-plugins logs deploy/hyperai-scheduler-sidecar -c kube-scheduler --tail=50 | grep -i "hyperai\|grpc\|score" || true
	@echo "\n--- Node Agent Logs ---"
	kubectl -n scheduler-plugins logs daemonset/hyperai-node-agent --tail=50 | grep -i "hyperai\|grpc\|score" || true

.PHONY: hyperai-daemonset-cleanup
hyperai-daemonset-cleanup:
	@echo "Cleaning up HyperAI DaemonSet resources..."
	kubectl delete -f manifests/hyperai/test-pod-with-agent.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/node-agent-daemonset.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/node-agent-service.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/node-agent-rbac.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/scheduler-deployment-sidecar.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/scheduler-config-sidecar.yaml --ignore-not-found=true

.PHONY: hyperai-daemonset-full-test
hyperai-daemonset-full-test: hyperai-daemonset-cleanup hyperai-daemonset-test hyperai-daemonset-logs

.PHONY: update-gomod
update-gomod:
	hack/update-gomod.sh

.PHONY: unit-test
unit-test: install-envtest
	hack/unit-test.sh $(ARGS)

.PHONY: install-envtest
install-envtest:
	hack/install-envtest.sh

.PHONY: integration-test
integration-test: install-envtest
	$(INTEGTESTENVVAR) hack/integration-test.sh $(ARGS)

.PHONY: verify
verify:
	hack/verify-gomod.sh
	hack/verify-gofmt.sh
	hack/verify-crdgen.sh
	hack/verify-structured-logging.sh
	hack/verify-toc.sh

.PHONY: clean
clean:
	rm -rf ./bin

.PHONY: help
help:
	@echo "Scheduler Plugins Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  build               - Build the scheduler binary"
	@echo "  constantscore-image - Build the ConstantScore Docker image"
	@echo "  constantscore-load-kind - Load the image into kind cluster"
	@echo "  constantscore-setup-rbac - Setup namespace and RBAC"
	@echo "  constantscore-deploy - Deploy ConstantScore to kind cluster"
	@echo "  constantscore-test  - Run the ConstantScore test pod"
	@echo "  constantscore-logs  - Show scheduler logs with constant score messages"
	@echo "  constantscore-cleanup - Clean up ConstantScore resources"
	@echo "  constantscore-full-test - Run complete test cycle (cleanup, deploy, test, logs)"
	@echo ""
	@echo "HyperAI targets:"
	@echo "  hyperai-proto       - Generate gRPC code for Go and Python"
	@echo "  hyperai-image       - Build the HyperAI Docker image"
	@echo "  hyperai-grpc-image  - Build the HyperAI gRPC server image"
	@echo "  hyperai-load-kind   - Load the image into kind cluster"
	@echo "  hyperai-start-grpc  - Start the Python gRPC server locally"
	@echo "  hyperai-stop-grpc   - Stop the Python gRPC server"
	@echo "  hyperai-test-grpc   - Test gRPC connectivity"
	@echo "  hyperai-sidecar-deploy - Deploy HyperAI with sidecar gRPC server (recommended)"
	@echo "  hyperai-sidecar-test - Run HyperAI test pod with sidecar"
	@echo "  hyperai-sidecar-logs - Show sidecar scheduler logs"
	@echo "  hyperai-sidecar-cleanup - Clean up sidecar resources"
	@echo "  hyperai-sidecar-full-test - Run complete sidecar test cycle"
	@echo "  hyperai-daemonset-deploy - Deploy HyperAI with DaemonSet architecture"
	@echo "  hyperai-daemonset-test - Run HyperAI test pod with DaemonSet agents"
	@echo "  hyperai-daemonset-logs - Show DaemonSet logs (scheduler, node agent)"
	@echo "  hyperai-daemonset-cleanup - Clean up DaemonSet resources"
	@echo "  hyperai-daemonset-full-test - Run complete DaemonSet test cycle"
	@echo "  hyperai-deploy      - Deploy HyperAI with separate gRPC service"
	@echo "  hyperai-test        - Run the HyperAI test pod"
	@echo "  hyperai-full-test   - Run complete test cycle with separate gRPC service"
	@echo ""
	@echo "General targets:"
	@echo "  clean               - Remove build artifacts"
	@echo "  unit-test           - Run unit tests"
	@echo "  integration-test    - Run integration tests"
	@echo "  verify              - Run verification checks"
	@echo ""
	@echo "Configuration variables:"
	@echo "  CONSTANTSCORE_IMAGE_NAME - Docker image name (default: constantscore-scheduler)"
	@echo "  CONSTANTSCORE_IMAGE_TAG  - Docker image tag (default: latest)"
	@echo "  HYPERAI_IMAGE_NAME       - HyperAI Docker image name (default: hyperai-scheduler)"
	@echo "  HYPERAI_IMAGE_TAG        - HyperAI Docker image tag (default: latest)"
	@echo "  KIND_CLUSTER_NAME        - Kind cluster name (default: sched)"
	@echo ""
	@echo "Quick Start:"
	@echo "  make constantscore-full-test     - Test ConstantScore plugin"
	@echo "  make hyperai-sidecar-full-test   - Test HyperAI plugin (sidecar, recommended)"
	@echo "  make hyperai-daemonset-full-test - Test HyperAI plugin (DaemonSet architecture)"
