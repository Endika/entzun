POETRY ?= poetry

.PHONY: install dev-install run format lint type-check test coverage pre-commit-install

install:
	$(POETRY) install

dev-install:
	$(POETRY) install --with dev

run:
	$(POETRY) run python run.py

format:
	$(POETRY) run ruff format .

lint:
	$(POETRY) run ruff check --fix .

type-check:
	$(POETRY) run mypy entzun

test:
	$(POETRY) run pytest

coverage:
	$(POETRY) run pytest --cov=entzun --cov-report=term-missing

pre-commit-install:
	$(POETRY) run pre-commit install

