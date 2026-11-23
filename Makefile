.PHONY: setup lint format typecheck sql-lint test test-unit test-integration test-dbt \
        dbt-deps dbt-parse dbt-build dbt-docs dagster-dev materialize-smoke materialize-full \
        delta-maintenance inspect-gold

DBT_DIR := dbt_project

setup:
	uv sync --dev
	uv run dbt deps --project-dir $(DBT_DIR) --profiles-dir $(DBT_DIR)

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

typecheck:
	uv run mypy src

sql-lint:
	uv run sqlfluff lint $(DBT_DIR)/models $(DBT_DIR)/macros $(DBT_DIR)/tests

test-unit:
	uv run pytest tests/unit -v --cov=ibge_market_intel

test-integration:
	uv run pytest tests/integration -v

test-dbt:
	uv run dbt parse --project-dir $(DBT_DIR) --profiles-dir $(DBT_DIR)
	uv run dbt test --select test_type:unit --project-dir $(DBT_DIR) --profiles-dir $(DBT_DIR)

test: lint typecheck test-unit test-integration test-dbt

dbt-deps:
	uv run dbt deps --project-dir $(DBT_DIR) --profiles-dir $(DBT_DIR)

dbt-parse:
	uv run dbt parse --project-dir $(DBT_DIR) --profiles-dir $(DBT_DIR)

dbt-build:
	uv run dbt build --project-dir $(DBT_DIR) --profiles-dir $(DBT_DIR)

dbt-docs:
	uv run dbt docs generate --project-dir $(DBT_DIR) --profiles-dir $(DBT_DIR)
	uv run dbt docs serve --project-dir $(DBT_DIR) --profiles-dir $(DBT_DIR) --port 8080

dagster-dev:
	DAGSTER_HOME="$(CURDIR)/.dagster" uv run dagster dev

materialize-smoke:
	uv run ibge-pipeline run --mode smoke

materialize-full:
	uv run ibge-pipeline run --mode full

delta-maintenance:
	uv run ibge-pipeline maintain

inspect-gold:
	uv run ibge-pipeline inspect
