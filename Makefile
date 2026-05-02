.PHONY: install run test lint format validate-env smoke-ado collect-raw normalize-raw

INCLUDE_TESTS ?= true
INCLUDE_PULL_REQUESTS ?= true
INCLUDE_ARTIFACTS ?= true

install:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

run:
	uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest

lint:
	ruff check .
	mypy --no-incremental --cache-dir .cache/mypy_backend backend scripts tests

format:
	ruff format .

validate-env:
	python scripts/validate_env.py

smoke-ado:
	python scripts/smoke_ado_auth.py --build-id $(BUILD_ID)

collect-raw:
	python scripts/collect_raw_metadata.py --build-id $(BUILD_ID) \
		--include-tests $(INCLUDE_TESTS) \
		--include-pull-requests $(INCLUDE_PULL_REQUESTS) \
		--include-artifacts $(INCLUDE_ARTIFACTS)

normalize-raw:
	python scripts/normalize_raw_metadata.py --build-id $(BUILD_ID)
