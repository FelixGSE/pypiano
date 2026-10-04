#!/usr/bin/env bash
# Runs once after the container is created (as the unprivileged "dev" user).
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> uv $(uv --version)"

# The bind-mounted repo may be owned by a different uid than the container user.
git config --global --add safe.directory "$(pwd)"

# Let git use gh's credentials (GH_TOKEN or `gh auth login`) for HTTPS remotes.
if [[ -n "${GH_TOKEN:-}" ]] || gh auth status >/dev/null 2>&1; then
  gh auth setup-git
  echo "==> gh: $(gh auth status 2>&1 | grep -m1 'Logged in' || echo 'authenticated via GH_TOKEN')"
else
  echo "==> gh: not authenticated (set GH_TOKEN on the host or run 'gh auth login')"
fi

echo "==> uv sync"
uv sync --all-extras

# Install the git pre-commit hook (prek reads .pre-commit-config.yaml).
if [[ -f .pre-commit-config.yaml ]]; then
  echo "==> prek install"
  prek install
fi

echo "==> fluidsynth: $(fluidsynth --version 2>/dev/null | head -1 || echo 'not found')"
echo "==> python: $("$UV_PROJECT_ENVIRONMENT/bin/python" --version 2>/dev/null || echo 'venv not created')"
echo "==> Done. Activate with: source $UV_PROJECT_ENVIRONMENT/bin/activate (or just use uv run ...)"
