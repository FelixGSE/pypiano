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

# Pull LFS objects (bundled sound font) if the clone only has pointers.
if git lfs ls-files --name-only 2>/dev/null | grep -q .; then
  echo "==> Fetching git-lfs objects"
  git lfs pull || echo "WARN: git lfs pull failed; sound font may be missing"
fi

if [[ -f pyproject.toml ]]; then
  # uv-based project layout (post migration)
  echo "==> uv sync"
  uv sync --all-extras
elif [[ -f requirements.txt ]]; then
  # Legacy setup.py / requirements.txt layout (pre migration).
  # The old pins (e.g. numpy==1.20.2) predate every maintained Python, so this
  # is best effort: warn instead of failing the container setup.
  echo "==> Legacy install via uv venv + uv pip"
  uv venv --clear --python 3.12 .venv
  # setuptools<81 still ships pkg_resources, which pypiano/piano.py imports
  if ! uv pip install -r requirements.txt "setuptools<81" -e .; then
    echo "WARN: legacy requirements do not install on Python 3.12; bump the pins or migrate to pyproject.toml"
  fi
  uv pip install black flake8 mypy pytest
else
  echo "==> No pyproject.toml or requirements.txt found; creating an empty venv"
  uv venv --clear --python 3.12 .venv
fi

echo "==> fluidsynth: $(fluidsynth --version 2>/dev/null | head -1 || echo 'not found')"
echo "==> python: $(.venv/bin/python --version 2>/dev/null || echo 'venv not created')"
echo "==> Done. Activate with: source .venv/bin/activate (or just use uv run ...)"
