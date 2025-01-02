include vars.mk

.DEFAULT_GOAL := all

.PHONY: clean default dev ensure-uv fmt lint test help

all: dev lint

client: dev
	$(UV) run python app.py
server: dev
	$(UV) run python -m mcp_servers.connect_api

clean:
	rm -rf .pytest_cache .ruff_cache *.egg-info
	find . -name "*.egg-info" -exec rm -rf {} +
	find . -name "*.pyc" -exec rm -f {} +
	find . -name "__pycache__" -exec rm -rf {} +
	find . -type d -empty -delete

dev: ensure-uv
	$(UV) pip install -e .

$(VIRTUAL_ENV):
	$(UV) venv $(VIRTUAL_ENV)
ensure-uv:
	@if ! command -v $(UV) >/dev/null; then \
		$(PYTHON) -m ensurepip && $(PYTHON) -m pip install "uv >= 0.4.27"; \
	fi
	@# Install virtual environment (before calling `uv pip install ...`)
	@$(MAKE) $(VIRTUAL_ENV) 1>/dev/null
	@# Be sure recent uv is installed
	@$(UV) pip install "uv >= 0.4.27" --quiet

fmt: dev
	$(UV) run ruff check --fix
	$(UV) run ruff format

$(UV_LOCK): dev
	$(UV) lock
lint: dev
	$(UV) run ruff check
	$(UV) run pyright

test: dev
	echo "Not implemented yet"
	exit 1
	$(UV) run --source=src -m pytest tests

ex-api: dev
	$(UV) run --group ex-fastapi uvicorn ex_api.main:app --reload
shiny: dev
	$(UV) run --group ex-fastapi python -m shiny run --port 56025 --reload --autoreload-port 56026 shiny/app.py

help:
	@echo "Makefile Targets"
	@echo "  all            Run dev and lint"
	@echo "  clean          Clean up project artifacts"
	@echo "  dev            Install the project in editable mode"
	@echo "  ensure-uv      Ensure 'uv' is installed"
	@echo "  fmt            Format the code"
	@echo "  lint           Lint the code"
	@echo "  test           Run unit tests"
