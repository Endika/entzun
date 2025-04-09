.PHONY: lint format test install backend-install backend-lint backend-format backend-test frontend-install frontend-lint frontend-format docker-build docker-run docker-stop

PYTHON_PATH = python
POETRY_PATH = poetry
NPM_PATH = npm

backend-install:
	cd backend && $(POETRY_PATH) env remove --all
	cd backend && $(POETRY_PATH) config virtualenvs.in-project true
	cd backend && $(POETRY_PATH) install

backend-lint:
	cd backend && $(POETRY_PATH) run ruff check app

backend-format:
	cd backend && $(POETRY_PATH) run ruff format app

backend-test:
	cd backend && $(POETRY_PATH) run pytest

frontend-install:
	cd frontend && $(NPM_PATH) install

frontend-lint:
	cd frontend && $(NPM_PATH) run lint

frontend-format:
	cd frontend && $(NPM_PATH) run format

install: backend-install frontend-install

lint: backend-lint frontend-lint

format: backend-format frontend-format

test: backend-test

docker-build:
	docker-compose build

docker-run:
	docker-compose up

docker-stop:
	docker-compose down
