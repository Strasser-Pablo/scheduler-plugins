#!/usr/bin/env bash
set -euo pipefail

# Optional: install handy Go tools (safe to skip)
# GOBIN=/usr/local/bin go install golang.org/x/tools/gopls@latest
# GOBIN=/usr/local/bin go install github.com/go-delve/delve/cmd/dlv@latest
# GOBIN=/usr/local/bin go install honnef.co/go/tools/cmd/staticcheck@latest

# Go cache tuning (optional)
go env -w GOMODCACHE=/go/pkg/mod