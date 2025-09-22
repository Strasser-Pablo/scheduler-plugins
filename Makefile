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

# Build configurations
COMMONENVVAR=GOOS=$(shell uname -s | tr A-Z a-z) GOARCH=$(subst x86_64,amd64,$(patsubst i%86,386,$(shell uname -m)))
BUILDENVVAR=CGO_ENABLED=0 $(COMMONENVVAR)

# Go Build Environment
ARCHS=amd64 arm64
TAG=v$(shell date +%m%d%H%M)
REGISTRY?=localhost:5000
IMAGE_BUILD_EXTRA_OPTS?=

# Build versioning
VERSION?=v1.33.3
RELEASE_VERSION?=$(VERSION)
LOCALBIN ?= $(shell pwd)/bin
CONTROLLER_TOOLS_VERSION ?= v0.16.1
ENVTEST_K8S_VERSION = 1.32.x

# Image configurations
HYPERAI_IMAGE_NAME=hyperai-scheduler
HYPERAI_IMAGE_TAG=latest
KIND_CLUSTER_NAME=sched

GOPATH?=$(shell go env GOPATH)

# Core build targets
.PHONY: all
all: build

.PHONY: build
build: build-scheduler

.PHONY: build-scheduler
build-scheduler:
	$(BUILDENVVAR) go build -ldflags '-X k8s.io/component-base/version.gitVersion=$(VERSION) -w' -o bin/kube-scheduler cmd/scheduler/main.go

.PHONY: build-controller
build-controller:
	$(BUILDENVVAR) go build -ldflags '-X k8s.io/component-base/version.gitVersion=$(VERSION) -w' -o bin/controller cmd/controller/main.go

.PHONY: update-vendor
update-vendor:
	hack/update-vendor.sh

.PHONY: unit-test
unit-test:
	hack/unit-test.sh

.PHONY: install-etcd
install-etcd:
	hack/install-etcd.sh

.PHONY: install-envtest
install-envtest: $(LOCALBIN)
	test -s $(LOCALBIN)/setup-envtest || GOBIN=$(LOCALBIN) go install sigs.k8s.io/controller-runtime/tools/setup-envtest@latest

.PHONY: integration-test
integration-test: install-etcd install-envtest
	hack/integration-test.sh

.PHONY: verify
verify:
	hack/verify-gofmt.sh
	hack/verify-gomod.sh
	hack/verify-structured-logging.sh
	hack/verify-toc.sh

.PHONY: clean
clean:
	rm -rf ./bin

# Controller gen tool for manifests
.PHONY: controller-gen
controller-gen: $(LOCALBIN) ## Download controller-gen locally if necessary.
	test -s $(LOCALBIN)/controller-gen || GOBIN=$(LOCALBIN) go install sigs.k8s.io/controller-tools/cmd/controller-gen@$(CONTROLLER_TOOLS_VERSION)

$(LOCALBIN):
	mkdir -p $(LOCALBIN)


# HyperAI Production targets (Real NVIDIA Triton ML Inference)
.PHONY: hyperai-proto
hyperai-proto:
	@echo "Generating gRPC code for HyperAI..."
	cd hack/hyperai-grpc && python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. hyperai.proto
	cd pkg/hyperai && protoc --go_out=. --go-grpc_out=. -I../../hack/hyperai-grpc ../../hack/hyperai-grpc/hyperai.proto
	cd pkg/hyperai && mv sigs.k8s.io/scheduler-plugins/pkg/hyperai/*.go . && rm -rf sigs.k8s.io || true

.PHONY: hyperai-build-images
hyperai-build-images:
	@echo "Building all HyperAI images..."
	CGO_ENABLED=0 GOOS=linux $(BUILDENVVAR) go build -ldflags '-X k8s.io/component-base/version.gitVersion=$(VERSION) -w' -o bin/kube-scheduler cmd/scheduler/main.go
	docker build -f Dockerfile.constantscore -t $(HYPERAI_IMAGE_NAME):$(HYPERAI_IMAGE_TAG) .
	cd hack/hyperai-grpc && docker build -t hyperai-grpc-server:latest .
	cd hack/hyperai-grpc && docker build -f Dockerfile.triton-node-agent -t hyperai-triton-node-agent:latest .
	@echo "Pulling NVIDIA Triton server image..."
	docker pull nvcr.io/nvidia/tritonserver:24.12-py3

.PHONY: hyperai-load-kind
hyperai-load-kind: hyperai-build-images
	@echo "Loading HyperAI images into Kind cluster..."
	kind load docker-image $(HYPERAI_IMAGE_NAME):$(HYPERAI_IMAGE_TAG) --name $(KIND_CLUSTER_NAME)
	kind load docker-image hyperai-grpc-server:latest --name $(KIND_CLUSTER_NAME)
	kind load docker-image hyperai-triton-node-agent:latest --name $(KIND_CLUSTER_NAME)
	@echo "Loading NVIDIA Triton server image into Kind cluster..."
	kind load docker-image nvcr.io/nvidia/tritonserver:24.12-py3 --name $(KIND_CLUSTER_NAME)

.PHONY: hyperai-setup-rbac
hyperai-setup-rbac:
	@echo "Setting up namespace and RBAC for HyperAI..."
	kubectl get ns scheduler-plugins >/dev/null 2>&1 || kubectl create ns scheduler-plugins
	kubectl apply -f manifests/install/scheduler-serviceaccount.yaml
	kubectl apply -f manifests/install/scheduler-clusterrole.yaml
	kubectl apply -f manifests/install/scheduler-clusterrolebinding.yaml
	kubectl apply -f manifests/hyperai/node-agent-rbac.yaml

.PHONY: hyperai-deploy
hyperai-deploy: hyperai-load-kind hyperai-setup-rbac
	@echo "Deploying HyperAI with real NVIDIA Triton inference..."
	@echo "Setting up Triton node agents with DaemonSet..."
	kubectl apply -f manifests/hyperai/triton-node-agent-daemonset-real.yaml
	kubectl -n scheduler-plugins rollout status daemonset/hyperai-triton-node-agent --timeout=180s
	@echo "Deploying central gRPC server..."
	kubectl apply -f manifests/hyperai/grpc-server.yaml
	kubectl -n scheduler-plugins rollout status deploy/hyperai-grpc-server --timeout=120s
	@echo "Deploying HyperAI scheduler..."
	kubectl apply -f manifests/hyperai/scheduler-config.yaml
	kubectl apply -f manifests/hyperai/scheduler-deployment.yaml
	kubectl -n scheduler-plugins rollout status deploy/hyperai-scheduler --timeout=120s
	@echo "✅ HyperAI deployment completed successfully!"

.PHONY: hyperai-test
hyperai-test: hyperai-deploy
	@echo "Testing HyperAI with comprehensive pod specifications..."
	@echo "Waiting 5 seconds to allow agents to establish gRPC streams..."
	sleep 5
	kubectl apply -f hack/hyperai-grpc/test-triton-final-working.yaml
	kubectl wait --for=condition=Ready pod/test-triton-final-working --timeout=120s
	@echo "✅ Test pod deployed successfully!"
	kubectl get pod test-triton-final-working -o wide
	@echo "✅ HyperAI test completed!"

.PHONY: hyperai-logs
hyperai-logs:
	@echo "=== HyperAI Scheduler Logs ==="
	kubectl -n scheduler-plugins logs deploy/hyperai-scheduler --tail=20 | grep -E "(HyperAI|gRPC|score)" || true
	@echo ""
	@echo "=== Central gRPC Server Logs ==="
	kubectl -n scheduler-plugins logs deploy/hyperai-grpc-server --tail=50 | grep -E "(gRPC|AgentConnect|GetScore|score|Registered agent session|Streaming)" || true
	@echo ""
	@echo "=== Triton Node Agent Logs (sample) ==="
	kubectl -n scheduler-plugins logs -l app=hyperai-triton-node-agent -c triton-node-agent --tail=50 | head -25 || true
	@echo ""
	@echo "=== Triton Server Status ==="
	kubectl -n scheduler-plugins get pods -l app=hyperai-triton-node-agent

.PHONY: hyperai-status
hyperai-status:
	@echo "=== HyperAI Deployment Status ==="
	kubectl -n scheduler-plugins get deployments
	kubectl -n scheduler-plugins get daemonsets
	kubectl -n scheduler-plugins get pods | grep -E "(hyperai|triton)"

.PHONY: hyperai-cleanup
hyperai-cleanup:
	@echo "Cleaning up HyperAI resources..."
	kubectl delete pod test-triton-final-working --ignore-not-found=true
	kubectl delete -f manifests/hyperai/scheduler-deployment.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/scheduler-config.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/grpc-server.yaml --ignore-not-found=true
	kubectl delete -f manifests/hyperai/triton-node-agent-daemonset-real.yaml --ignore-not-found=true
	@echo "✅ HyperAI cleanup completed!"

.PHONY: hyperai-full-test
hyperai-full-test: hyperai-cleanup hyperai-test hyperai-logs

.PHONY: hyperai-rebuild-deploy
hyperai-rebuild-deploy: hyperai-cleanup hyperai-deploy

# Generate ONNX model for Triton
.PHONY: hyperai-generate-model
hyperai-generate-model:
	@echo "Generating ONNX model for Triton inference..."
	cd hack/hyperai-grpc && python3 generate_scheduler_model.py
	@echo "✅ ONNX model generated successfully!"

# Development and debugging targets
.PHONY: hyperai-debug-pods
hyperai-debug-pods:
	@echo "=== Pod Details ==="
	kubectl -n scheduler-plugins describe pods -l app=hyperai-triton-node-agent | grep -A5 -B5 "Status\|Ready\|Restart"

.PHONY: hyperai-debug-events
hyperai-debug-events:
	@echo "=== Recent Events ==="
	kubectl -n scheduler-plugins get events --sort-by='.lastTimestamp' | tail -10

.PHONY: hyperai-restart-agents
hyperai-restart-agents:
	@echo "Restarting Triton node agents..."
	kubectl -n scheduler-plugins delete pods -l app=hyperai-triton-node-agent
	kubectl -n scheduler-plugins rollout status daemonset/hyperai-triton-node-agent --timeout=180s
	@echo "✅ Node agents restarted!"

.PHONY: hyperai-test-connectivity
hyperai-test-connectivity:
	@echo "Testing gRPC connectivity..."
	cd hack/hyperai-grpc && python3 test_client.py

# Convenience targets
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  build               - Build scheduler binary"
	@echo "  unit-test           - Run unit tests"
	@echo "  integration-test    - Run integration tests"
	@echo "  verify              - Run all verification checks"
	@echo ""
	@echo "HyperAI Production (Real ML Inference):"
	@echo "  hyperai-deploy               - Deploy HyperAI with Triton inference"
	@echo "  hyperai-test                 - Test HyperAI with real ML scoring"
	@echo "  hyperai-logs                 - Show HyperAI component logs"
	@echo "  hyperai-status               - Show deployment status"
	@echo "  hyperai-cleanup              - Clean up HyperAI resources"
	@echo "  hyperai-full-test            - Full test cycle"
	@echo "  hyperai-generate-model       - Generate ONNX model for Triton"
	@echo ""
	@echo "Development and Debugging:"
	@echo "  hyperai-debug-pods           - Debug pod status"
	@echo "  hyperai-debug-events         - Show recent events"
	@echo "  hyperai-restart-agents       - Restart node agents"
	@echo "  hyperai-test-connectivity    - Test gRPC connectivity"