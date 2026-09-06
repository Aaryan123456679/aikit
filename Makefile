.PHONY: install lint type test all
install: ; pip install -e ".[dev]"
lint:    ; ruff check .
type:    ; mypy src
test:    ; pytest -q
all: lint type test
