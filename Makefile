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
	@echo "ConstantScore Plugin Makefile"
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
	@echo "  clean               - Remove build artifacts"
	@echo "  unit-test           - Run unit tests"
	@echo "  integration-test    - Run integration tests"
	@echo "  verify              - Run verification checks"
	@echo ""
	@echo "Configuration variables:"
	@echo "  CONSTANTSCORE_IMAGE_NAME - Docker image name (default: constantscore-scheduler)"
	@echo "  CONSTANTSCORE_IMAGE_TAG  - Docker image tag (default: latest)"
	@echo "  KIND_CLUSTER_NAME       - Kind cluster name (default: sched)"
