# syntax=docker/dockerfile:1.6
ARG GO_VERSION=1.25
ARG K8S_MINOR=1.30.0
ARG KIND_VERSION=0.23.0

FROM mcr.microsoft.com/devcontainers/go:${GO_VERSION}

USER root

# Base deps
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  sudo \ 
  ca-certificates curl git make bash-completion jq iptables iproute2 \
  gnupg lsb-release unzip tar build-essential \
  uidmap socat conntrack ebtables ethtool && \
  rm -rf /var/lib/apt/lists/*
RUN echo "vscode ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-vscode && \
  chmod 0440 /etc/sudoers.d/90-vscode

# kubectl pinned to cluster minor
ARG K8S_MINOR=1.30.0
RUN curl -fsSL -o /usr/local/bin/kubectl \
  https://dl.k8s.io/release/v${K8S_MINOR}/bin/linux/amd64/kubectl && \
  chmod +x /usr/local/bin/kubectl


ARG KIND_VERSION=0.23.0
ARG TARGETARCH=amd64
RUN set -eux; \
  ver="v${KIND_VERSION}"; \
  base="https://kind.sigs.k8s.io/dl"; \
  fn="kind-linux-${TARGETARCH}"; \
  # try exact version first
  if ! curl -fsSLo /usr/local/bin/kind "${base}/${ver}/${fn}"; then \
  echo "Requested KIND_VERSION ${ver} not found; falling back to latest"; \
  curl -fsSLo /usr/local/bin/kind "${base}/latest/${fn}"; \
  fi; \
  chmod +x /usr/local/bin/kind

# golangci-lint (optional but helpful)
ARG GOLANGCI_LINT_VERSION=v1.60.3
RUN curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/${GOLANGCI_LINT_VERSION}/install.sh | \
  sh -s -- -b /usr/local/bin ${GOLANGCI_LINT_VERSION}

# crane (updated to latest version compatible with Go 1.25)
RUN GOBIN=/usr/local/bin go install github.com/google/go-containerregistry/cmd/crane@v0.20.2

# ko (updated to latest version compatible with Go 1.25)
# Install ko
RUN GOBIN=/usr/local/bin go install github.com/google/ko@v0.17.0



# Docker CLI (to use host docker socket)
RUN curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-25.0.5.tgz | tar -xz -C /usr/local/bin --strip-components=1 docker/docker

# Docker Buildx (for multi-platform builds)
RUN mkdir -p /usr/local/lib/docker/cli-plugins \
  && curl -fsSL https://github.com/docker/buildx/releases/download/v0.28.0/buildx-v0.28.0.linux-amd64 -o /usr/local/lib/docker/cli-plugins/docker-buildx \
  && chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx

# Ensure docker group exists with host GID (997) and add vscode to it
RUN if getent group docker; then groupmod -g 997 docker; else groupadd -g 997 docker; fi \
  && usermod -aG docker vscode

# Nice shell + completions
RUN echo 'source /usr/share/bash-completion/bash_completion' >> /etc/bash.bashrc && \
  echo 'alias k=kubectl' >> /etc/bash.bashrc && \
  echo 'complete -F __start_kubectl k' >> /etc/bash.bashrc

# Create non-root user handled by devcontainer feature, ensure ownership
RUN mkdir -p /workspace && chown -R vscode:vscode /workspace

USER vscode
WORKDIR /workspace