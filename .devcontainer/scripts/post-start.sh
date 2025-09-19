#!/usr/bin/env bash
set -euo pipefail

# Docker socket access

# Always ensure docker group is GID 997 and socket is correct
if [ -S /var/run/docker.sock ]; then
  if getent group docker >/dev/null 2>&1; then
    sudo groupmod -g 997 docker || true
  else
    sudo groupadd -g 997 docker || true
  fi
  sudo usermod -aG docker vscode || true
  sudo chgrp docker /var/run/docker.sock || true
  sudo chmod g+rw /var/run/docker.sock || true
fi

mkdir -p /home/vscode/.kube
sudo chown -R vscode:vscode /home/vscode/.kube

_kind()   { sudo -u vscode -g docker -E kind "$@"; }

# Recreate cluster 'sched': delete if exists, then create 3-node cluster
if _kind get clusters 2>/dev/null | grep -qx 'sched'; then
  echo "Deleting existing kind cluster 'sched'..."
  _kind delete cluster --name sched || true
fi

echo "Creating kind cluster 'sched' with 1 control-plane and 2 workers..."
cat <<'YAML' >/tmp/kind.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: sched
nodes:
  - role: control-plane
    image: kindest/node:v1.33.4@sha256:25a6018e48dfcaee478f4a59af81157a437f15e6e140bf103f85a2e7cd0cbbf2
  - role: worker
    image: kindest/node:v1.33.4@sha256:25a6018e48dfcaee478f4a59af81157a437f15e6e140bf103f85a2e7cd0cbbf2
  - role: worker
    image: kindest/node:v1.33.4@sha256:25a6018e48dfcaee478f4a59af81157a437f15e6e140bf103f85a2e7cd0cbbf2
YAML
_kind create cluster --config /tmp/kind.yaml

# Export INTERNAL kubeconfig and point directly at control-plane IP
_kind export kubeconfig --name sched --kubeconfig /home/vscode/.kube/config --internal
sudo chown vscode:vscode /home/vscode/.kube/config
chmod 600 /home/vscode/.kube/config || true

# Resolve control-plane IP on 'kind' network and set server to IP (bypasses DNS)
CP_IP=$(sudo -u vscode -g docker docker inspect -f '{{ .NetworkSettings.Networks.kind.IPAddress }}' sched-control-plane || true)
if [ -n "$CP_IP" ]; then
  kubectl config set-cluster kind-sched --server="https://$CP_IP:6443" >/dev/null
fi
kubectl config use-context kind-sched >/dev/null 2>&1 || true

# Wait (bounded) for API
for i in {1..20}; do
  if [ -n "$CP_IP" ] && curl -sk --connect-timeout 1 "https://$CP_IP:6443/readyz" >/dev/null; then
    break
  fi
  sleep 1
done

echo "post-start complete."
