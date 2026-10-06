.DEFAULT_GOAL := help

NOTE ?= C-4
INSTRUMENT ?= Acoustic Grand Piano
OUTPUT ?= demo.wav
RECORD_SECONDS ?= 2
PYTHONS ?= 3.11 3.12 3.13 3.14
# Minimum line and branch coverage in percent; make coverage fails below it
COVERAGE_MIN ?= 100
# Minimum mutation score in percent; make mutation fails below it
MUTATION_MIN ?= 100

.PHONY: help install soundfont soundfont-check lint test test-all test-lowest test-package test-integration coverage mutation play record clean

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

test-lowest: ## Run all tests with the oldest dependency versions pyproject.toml allows, on the oldest Python
	@# A throwaway venv, so uv.lock and the project's venv stay untouched
	rm -rf .venv-lowest
	uv venv --quiet --python $(firstword $(PYTHONS)) .venv-lowest
	uv pip install --quiet --python .venv-lowest --resolution lowest-direct --editable . --group dev
	.venv-lowest/bin/python -m pytest -q -m "integration or not integration"

test-package: ## Build the sdist and wheel, install the wheel into a fresh venv and check it outside the repository
	@# The script runs with the venv's Python and imports pypiano from the installed wheel, not from the source tree
	rm -rf dist .venv-package
	uv build --quiet
	uv venv --quiet --python $(lastword $(PYTHONS)) .venv-package
	uv pip install --quiet --python .venv-package dist/*.whl
	.venv-package/bin/python scripts/check_package.py

test-integration: ## Run the tests that play real audio
	uv run pytest -m integration

coverage: ## Run the tests with coverage; fails below COVERAGE_MIN percent
	uv run pytest --cov --cov-report=term-missing --cov-report=html --cov-fail-under=$(COVERAGE_MIN)

mutation: ## Run mutation testing; fails below MUTATION_MIN percent and lists the mutants the tests missed
	@# Always from scratch: mutmut's incremental cache can keep results of mutants whose code changed
	rm -rf mutants
	uv run mutmut run
	uv run mutmut export-cicd-stats
	uv run scripts/mutation_score.py --min $(MUTATION_MIN)

play: ## Play NOTE via audio output (needs a sound device)
	uv run scripts/demo.py play --note "$(NOTE)" --instrument "$(INSTRUMENT)"

record: ## Record NOTE to OUTPUT (wav)
	uv run scripts/demo.py record --note "$(NOTE)" --instrument "$(INSTRUMENT)" --output "$(OUTPUT)" --seconds $(RECORD_SECONDS)

clean: ## Remove caches and demo recordings
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist mutants .venv-lowest .venv-package "$(OUTPUT)"
	find . -name __pycache__ -type d -not -path './.venv/*' -prune -exec rm -rf {} +
