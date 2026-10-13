.PHONY: help test-unit test-integration test-e2e test-all coverage check lint-imports contracts-check

VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
PYTEST ?= $(VENV)/bin/pytest
LINT_IMPORTS ?= $(VENV)/bin/lint-imports

help:
	@echo "PromiseCheck Test & Verification Suite"
	@echo ""
	@echo "Available targets:"
	@echo "  make test-unit         Run pure unit tests (isolated, no DB, no network)"
	@echo "  make test-integration  Run integration tests against PostgreSQL & Redis"
	@echo "  make test-e2e          Run end-to-end full stack user journeys"
	@echo "  make test-all          Run the entire test suite (unit + integration + e2e)"
	@echo "  make coverage          Run full test suite with line & branch coverage report"
	@echo "  make check             Run architecture contracts, snapshot freeze & full tests"
	@echo "  make lint-imports      Verify modular-monolith boundary contracts"
	@echo "  make contracts-check   Verify contract snapshot freeze against baseline"

test-unit:
	$(PYTEST) backend/tests/unit -m unit -v

test-integration:
	$(PYTEST) backend/tests/integration -m integration -v

test-e2e:
	$(PYTEST) backend/tests/e2e -m e2e -v

test-all:
	$(PYTEST) backend/tests -v

coverage:
	$(PYTEST) -c backend/pyproject.toml backend/tests --cov=core --cov=modules --cov=jobs --cov=connectors --cov=ai --cov=api --cov-report=term-missing --cov-fail-under=65

lint-imports:
	cd backend && ../$(LINT_IMPORTS)

contracts-check:
	PYTHONPATH=backend/src:backend $(PYTHON) backend/tools/snapshot_contracts.py --check

check: lint-imports contracts-check test-all
