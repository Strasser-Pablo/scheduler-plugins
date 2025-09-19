# LLM Guide: Build and Automation (`hack/`)

This directory contains scripts for building, testing, code generation, and verification tasks.

## Directory Structure

```
hack/
├── build-images.sh              # Container image building
├── go-install.sh               # Go installation helper
├── install-envtest.sh          # Test environment setup
├── install-etcd.sh             # etcd installation for tests
├── integration-test.sh         # Integration test runner
├── net_tls_stat.go            # Network TLS statistics utility
├── tools.go                   # Go tool dependencies
├── unit-test.sh               # Unit test runner
├── update-codegen.sh          # Code generation (deepcopy, etc.)
├── update-gofmt.sh            # Go code formatting
├── update-gomod.sh            # Go module management
├── update-toc.sh              # Table of contents generation
├── upgrade-k8s.sh             # Kubernetes version upgrades
├── verify-crdgen.sh           # CRD generation verification
├── verify-gofmt.sh            # Go formatting verification
├── verify-gomod.sh            # Go module verification
├── verify-structured-logging.sh # Logging format verification
├── verify-toc.sh              # TOC verification
├── boilerplate/               # License header templates
└── lib/                       # Shared library functions
```

## Key Scripts for Development

### Building and Testing

#### `unit-test.sh`
```bash
#!/bin/bash
# Runs unit tests with proper setup
# Usage: hack/unit-test.sh [package_pattern]

# Set up test environment
source "$(dirname "${BASH_SOURCE[0]}")/lib/init.sh"

# Run tests with coverage
go test -race -cover ./pkg/... ./apis/...

# Optional: Run specific package
go test -race -cover ./pkg/constantscore/...
```

#### `integration-test.sh`  
```bash
#!/bin/bash
# Runs integration tests with real Kubernetes environment
# Usage: SCHED_PLUGINS_TEST_VERBOSE=1 hack/integration-test.sh

# Set up test cluster
hack/install-envtest.sh
hack/install-etcd.sh

# Run integration tests
go test -race ./test/integration/...
```

#### `build-images.sh`
```bash
#!/bin/bash
# Builds container images for scheduler and controller
# Usage: hack/build-images.sh

# Build scheduler image
docker build -f Dockerfile.constantscore -t scheduler-plugins/kube-scheduler .

# Build controller image  
docker build -f build/controller/Dockerfile -t scheduler-plugins/controller .
```

### Code Generation and Verification

#### `update-codegen.sh`
```bash
#!/bin/bash
# Generates deep copy methods and other boilerplate code
# Required after adding new types to apis/config/types.go

# Generate deepcopy methods
go run k8s.io/code-generator/cmd/deepcopy-gen \
  --input-dirs=sigs.k8s.io/scheduler-plugins/apis/config \
  --output-file-base=zz_generated.deepcopy

# Generate scheme registration  
go run k8s.io/code-generator/cmd/register-gen \
  --input-dirs=sigs.k8s.io/scheduler-plugins/apis/config
```

**When to run**: After modifying any types in `apis/config/types.go`

#### `verify-gofmt.sh`
```bash
#!/bin/bash
# Verifies Go code formatting
# Usage: hack/verify-gofmt.sh

# Check formatting
gofmt -l -s -d $(find . -name "*.go" | grep -v vendor | grep -v generated)

# Fix formatting automatically
hack/update-gofmt.sh
```

#### `verify-gomod.sh`
```bash
#!/bin/bash  
# Verifies Go module consistency
# Usage: hack/verify-gomod.sh

# Check for unused dependencies
go mod tidy

# Verify go.sum is up to date
go mod verify
```

### Kubernetes Integration

#### `upgrade-k8s.sh`
```bash
#!/bin/bash
# Updates Kubernetes dependencies to new version
# Usage: hack/upgrade-k8s.sh v1.33.3

K8S_VERSION=${1:-v1.33.3}

# Update go.mod dependencies
go mod edit -require=k8s.io/api@${K8S_VERSION}
go mod edit -require=k8s.io/apimachinery@${K8S_VERSION}
go mod edit -require=k8s.io/client-go@${K8S_VERSION}
# ... more dependencies

go mod tidy
```

#### `install-envtest.sh`
```bash
#!/bin/bash
# Installs controller-runtime test environment
# Provides fake Kubernetes API server for testing

ENVTEST_K8S_VERSION=${ENVTEST_K8S_VERSION:-1.33.x}

# Download and setup envtest binaries
go install sigs.k8s.io/controller-runtime/tools/setup-envtest@latest
setup-envtest use ${ENVTEST_K8S_VERSION} --bin-dir=./bin
```

## Development Workflow Scripts

### Pre-commit Verification

```bash
#!/bin/bash
# Run all verification checks before commit
# Create as: hack/verify-all.sh

set -e

echo "Running pre-commit verifications..."

# Code formatting
echo "Checking Go formatting..."
hack/verify-gofmt.sh

# Go modules
echo "Verifying Go modules..."  
hack/verify-gomod.sh

# Code generation
echo "Verifying code generation..."
hack/verify-crdgen.sh

# Structured logging
echo "Checking structured logging..."
hack/verify-structured-logging.sh

# Documentation TOC
echo "Verifying table of contents..."
hack/verify-toc.sh

echo "All verifications passed!"
```

### Continuous Integration

```bash
#!/bin/bash
# CI pipeline script
# Create as: hack/ci-test.sh

set -e

echo "Running CI tests..."

# Unit tests
echo "Running unit tests..."
hack/unit-test.sh

# Integration tests  
echo "Running integration tests..."
SCHED_PLUGINS_TEST_VERBOSE=1 hack/integration-test.sh

# Build verification
echo "Building scheduler..."
make build-scheduler

# Image build test
echo "Testing image build..."
hack/build-images.sh

echo "CI pipeline completed!"
```

## Environment Variables

### Test Configuration
```bash
# Integration test verbosity
export SCHED_PLUGINS_TEST_VERBOSE=1

# Kubernetes version for envtest
export ENVTEST_K8S_VERSION=1.33.x

# Test timeout
export TEST_TIMEOUT=300s
```

### Build Configuration
```bash
# Container registry
export REGISTRY=registry.k8s.io/scheduler-plugins

# Image tags
export VERSION=v0.33.3
export RELEASE_VERSION=v0.33.3

# Build flags
export CGO_ENABLED=0
export GOOS=linux
export GOARCH=amd64
```

## Tools and Dependencies

### `tools.go`
Manages build-time tool dependencies:

```go
//go:build tools
// +build tools

package tools

import (
    _ "k8s.io/code-generator/cmd/deepcopy-gen"
    _ "k8s.io/code-generator/cmd/register-gen"
    _ "sigs.k8s.io/controller-runtime/tools/setup-envtest"
    _ "github.com/golang/mock/mockgen"
)
```

### Installing Tools
```bash
# Install all build tools
go mod download
go install k8s.io/code-generator/cmd/deepcopy-gen
go install sigs.k8s.io/controller-runtime/tools/setup-envtest
```

## Common Development Tasks

### Adding New Plugin

1. **Create plugin files**:
   ```bash
   mkdir -p pkg/yourplugin
   # Create yourplugin.go, yourplugin_test.go, README.md
   ```

2. **Add configuration type** to `apis/config/types.go`:
   ```go
   type YourPluginArgs struct {
       metav1.TypeMeta
       // Configuration fields
   }
   ```

3. **Generate code**:
   ```bash
   hack/update-codegen.sh
   ```

4. **Run tests**:
   ```bash
   hack/unit-test.sh ./pkg/yourplugin/...
   ```

5. **Verify formatting and modules**:
   ```bash
   hack/verify-gofmt.sh
   hack/verify-gomod.sh
   ```

### Updating Dependencies

1. **Update Kubernetes version**:
   ```bash
   hack/upgrade-k8s.sh v1.34.0
   ```

2. **Update other dependencies**:
   ```bash
   go get github.com/some/dependency@v1.2.3
   go mod tidy
   ```

3. **Verify changes**:
   ```bash
   hack/verify-gomod.sh
   hack/unit-test.sh
   ```

### Release Preparation

1. **Run all verifications**:
   ```bash
   hack/verify-all.sh  # (create this script)
   ```

2. **Run full test suite**:
   ```bash
   hack/unit-test.sh
   hack/integration-test.sh
   ```

3. **Build images**:
   ```bash
   hack/build-images.sh
   ```

4. **Update documentation**:
   ```bash
   hack/update-toc.sh
   ```

## Troubleshooting

### Code Generation Issues
```bash
# If deepcopy generation fails
go mod download k8s.io/code-generator
hack/update-codegen.sh

# Check for missing build tags or incorrect types
grep -r "+k8s:deepcopy-gen" apis/
```

### Test Environment Issues
```bash
# Reset test environment
rm -rf ./bin/k8s/
hack/install-envtest.sh

# Check etcd
hack/install-etcd.sh
./bin/etcd --version
```

### Module Issues
```bash
# Clean and rebuild modules
go clean -modcache
go mod download
go mod tidy
hack/verify-gomod.sh
```

### Formatting Issues
```bash
# Fix all formatting
hack/update-gofmt.sh

# Check specific files
gofmt -l -s -d pkg/yourplugin/
```

## Integration with Make

The hack scripts integrate with the main `Makefile`:

```makefile
# Makefile targets use hack scripts
.PHONY: unit-test
unit-test: install-envtest
	hack/unit-test.sh $(ARGS)

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
```

These scripts provide the foundation for a robust development, testing, and release workflow for the scheduler plugins project.