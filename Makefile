UV ?= uv

.PHONY: install dev-install run format lint type-check test coverage pre-commit-install

install:
	$(UV) sync --no-dev

dev-install:
	$(UV) sync --all-groups

run:
	$(UV) run python run.py

format:
	$(UV) run ruff format .

lint:
	$(UV) run ruff check --fix .

type-check:
	$(UV) run mypy entzun

test:
	$(UV) run pytest

coverage:
	$(UV) run pytest --cov=entzun --cov-report=term-missing

pre-commit-install:
	$(UV) run pre-commit install
