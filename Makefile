.PHONY: all help fmt fmt-check lint type test test-ci check example clean install install-hooks

.DEFAULT_GOAL := all

all: fmt lint type

help:
	@echo "Available commands:"
	@echo "  make              - Run fmt, lint, and type (default)"
	@echo "  make install      - Install dependencies"
	@echo "  make install-hooks- Install and setup pre-commit hooks"
	@echo "  make fmt          - Format code with ruff"
	@echo "  make fmt-check    - Check code formatting (CI)"
	@echo "  make lint         - Lint code with ruff"
	@echo "  make type         - Type check with pyright and mypy"
	@echo "  make test         - Run tests with pytest"
	@echo "  make test-ci      - Run tests with coverage (for CI)"
	@echo "  make check        - Run lint, type, and test"
	@echo "  make example      - Run example Streamlit app"
	@echo "  make clean        - Clean build artifacts"

install:
	uv sync --dev
	@echo ""
	@echo "To enable pre-commit hooks, run: make install-hooks"

install-hooks:
	uv run pre-commit install
	@echo "Pre-commit hooks installed successfully!"

fmt:
	uv run ruff check --select I --fix .
	uv run ruff format .

fmt-check:
	uv run ruff format --check .

lint:
	uv run ruff check .
	uv run ruff format --check .

type:
	uv run pyright
	uv run mypy src tests examples

test:
	uv run pytest

test-ci:
	uv run pytest --cov=src/st_error_boundary --cov-report=xml --cov-report=term

check: lint type test

example: demo

demo:
	uv run streamlit run examples/demo.py

clean:
	rm -rf dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
