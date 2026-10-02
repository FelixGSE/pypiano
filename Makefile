.DEFAULT_GOAL := help

NOTE ?= C-4
INSTRUMENT ?= Acoustic Grand Piano
OUTPUT ?= demo.wav
RECORD_SECONDS ?= 2
PYTHONS ?= 3.11 3.12 3.13 3.14
# Minimum line and branch coverage in percent; make coverage fails below it
COVERAGE_MIN ?= 100

# On macOS, ctypes.util.find_library does not search Homebrew's lib dir, so
# mingus cannot locate libfluidsynth. SIP strips DYLD_* from /bin/sh's
# environment, so the hint must be set inline on the uv command, not exported.
BREW_PREFIX := $(shell brew --prefix 2>/dev/null)
ifneq ($(BREW_PREFIX),)
UV_RUN := DYLD_FALLBACK_LIBRARY_PATH=$(BREW_PREFIX)/lib uv run
else
UV_RUN := uv run
endif

.PHONY: help install lint test test-all coverage play record clean

help: ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-10s %s\n", $$1, $$2}'

install: ## Install the project and dev tools into .venv
	uv sync

lint: ## Run all pre-commit hooks on all files
	prek run --all-files

test: ## Run the tests
	$(UV_RUN) pytest

test-all: ## Run the tests on every supported Python version
	@set -e; for v in $(PYTHONS); do echo "==> Python $$v"; $(UV_RUN) --isolated --python $$v pytest -q; done

coverage: ## Run the tests with coverage; fails below COVERAGE_MIN percent
	$(UV_RUN) pytest --cov --cov-report=term-missing --cov-report=html --cov-fail-under=$(COVERAGE_MIN)

play: ## Play NOTE via audio output (needs a sound device)
	$(UV_RUN) scripts/demo.py play --note "$(NOTE)" --instrument "$(INSTRUMENT)"

record: ## Record NOTE to OUTPUT (wav)
	$(UV_RUN) scripts/demo.py record --note "$(NOTE)" --instrument "$(INSTRUMENT)" --output "$(OUTPUT)" --seconds $(RECORD_SECONDS)

clean: ## Remove caches and demo recordings
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist "$(OUTPUT)"
	find . -name __pycache__ -type d -not -path './.venv/*' -prune -exec rm -rf {} +
