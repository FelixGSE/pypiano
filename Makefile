.DEFAULT_GOAL := help

NOTE ?= C-4
INSTRUMENT ?= Acoustic Grand Piano
OUTPUT ?= demo.wav
RECORD_SECONDS ?= 2
PYTHONS ?= 3.11 3.12 3.13 3.14
# Minimum line and branch coverage in percent; make coverage fails below it
COVERAGE_MIN ?= 100

.PHONY: help install soundfont soundfont-check lint test test-all coverage play record clean

help: ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-17s %s\n", $$1, $$2}'

install: ## Install the project and dev tools into .venv
	uv sync

soundfont: ## Build the bundled piano sound font from Debian's FluidR3_GM if it is missing; never overwrites a file
	uv run scripts/build_sound_font.py

soundfont-check: ## Rebuild the piano sound font and check it is byte-identical to the bundled file
	uv run scripts/build_sound_font.py --check

lint: ## Run all pre-commit hooks on all files
	prek run --all-files

test: ## Run the tests
	uv run pytest

test-all: ## Run the tests on every supported Python version
	@set -e; for v in $(PYTHONS); do echo "==> Python $$v"; uv run --isolated --python $$v pytest -q; done

coverage: ## Run the tests with coverage; fails below COVERAGE_MIN percent
	uv run pytest --cov --cov-report=term-missing --cov-report=html --cov-fail-under=$(COVERAGE_MIN)

play: ## Play NOTE via audio output (needs a sound device)
	uv run scripts/demo.py play --note "$(NOTE)" --instrument "$(INSTRUMENT)"

record: ## Record NOTE to OUTPUT (wav)
	uv run scripts/demo.py record --note "$(NOTE)" --instrument "$(INSTRUMENT)" --output "$(OUTPUT)" --seconds $(RECORD_SECONDS)

clean: ## Remove caches and demo recordings
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist "$(OUTPUT)"
	find . -name __pycache__ -type d -not -path './.venv/*' -prune -exec rm -rf {} +
