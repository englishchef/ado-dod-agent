.PHONY: install run test lint format validate-env smoke-ado smoke-llm generate-fields validate-output run-agent

install:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

run:
	uvicorn app.api.main:app --host 0.0.0.0 --port 8090 --reload

test:
	pytest

lint:
	ruff check .
	mypy --no-incremental --cache-dir .cache/mypy_run3 app scripts

format:
	ruff format .

validate-env:
	python scripts/validate_env.py

smoke-ado:
	python scripts/smoke_ado_auth.py --build-id $(BUILD_ID)

smoke-llm:
	python scripts/smoke_llm_access.py

generate-fields:
	python scripts/generate_service_now_fields.py --build-id $(BUILD_ID)

validate-output:
	python scripts/validate_service_now_payload.py --build-id $(BUILD_ID)

run-agent:
	python scripts/run_dod_agent.py --build-id $(BUILD_ID)
