.PHONY: setup test-contracts test lint backend frontend integration readiness containers
setup:
	python scripts/dev.py setup
test-contracts:
	uv run --locked python scripts/dev.py contracts
test:
	uv run --locked python scripts/dev.py test
lint:
	uv run --locked python scripts/dev.py lint
backend:
	uv run --locked python scripts/dev.py backend
frontend:
	uv run --locked python scripts/dev.py frontend
integration:
	uv run --locked python scripts/dev.py integration
readiness:
	uv run --locked python scripts/dev.py readiness
containers:
	uv run --locked python scripts/dev.py containers
