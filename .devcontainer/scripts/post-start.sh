#!/usr/bin/env bash
set -euo pipefail

# Docker socket access
if [ -S /var/run/docker.sock ]; then
  SOCK_GID="$(stat -c '%g' /var/run/docker.sock || echo 0)"
  if ! getent group docker >/dev/null 2>&1; then
    sudo groupadd -g "${SOCK_GID}" docker || true
  fi
  sudo usermod -aG docker vscode || true
  sudo chgrp docker /var/run/docker.sock || true
  sudo chmod g+rw /var/run/docker.sock || true
fi

mkdir -p /home/vscode/.kube
sudo chown -R vscode:vscode /home/vscode/.kube

_kind()   { sudo -u vscode -g docker -E kind "$@"; }

# Create cluster if missing (idempotent)
if ! _kind get clusters 2>/dev/null | grep -qx 'sched'; then
  echo "Creating kind cluster 'sched'..."
  cat <<'YAML' >/tmp/kind.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: sched
nodes:
  - role: control-plane
YAML
  _kind create cluster --config /tmp/kind.yaml
else
  echo "kind cluster 'sched' already exists."
fi

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
