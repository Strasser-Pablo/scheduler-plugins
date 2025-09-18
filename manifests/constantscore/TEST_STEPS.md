# Test ConstantScore on kind

This script builds the scheduler with `ConstantScore`, builds the container image, loads it into an existing kind cluster named `sched`, deploys the scheduler and a sample pod, then tails logs.

Requirements:
- `kind` cluster named `sched` already exists
- `docker` and `kubectl` available

Usage:

```bash
set -euo pipefail

# 1) Build scheduler binary
make build-scheduler

# 2) Build local image
docker build -f Dockerfile.constantscore -t constantscore-scheduler:latest .

# 3) Load into kind
kind load docker-image constantscore-scheduler:latest --name sched

# 4) Ensure namespace and RBAC
kubectl get ns scheduler-plugins >/dev/null 2>&1 || kubectl create ns scheduler-plugins
kubectl apply -f manifests/install/scheduler-serviceaccount.yaml
kubectl apply -f manifests/install/scheduler-clusterrole.yaml
kubectl apply -f manifests/install/scheduler-clusterrolebinding.yaml

# 5) Apply scheduler config + deployment
kubectl apply -f manifests/constantscore/scheduler-config.yaml
kubectl apply -f manifests/constantscore/scheduler-deployment.yaml
kubectl -n scheduler-plugins rollout status deploy/constantscore-scheduler --timeout=120s

# 6) Run test pod
kubectl apply -f manifests/constantscore/test-pod.yaml
kubectl wait --for=condition=Ready pod/constantscore-test-pod --timeout=90s

# 7) Show results
kubectl get pod constantscore-test-pod -o wide
kubectl -n scheduler-plugins logs deploy/constantscore-scheduler --tail=200 | grep -i "Returning constant score" || true
```
