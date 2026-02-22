.PHONY: help install test binary binary-x86_64 binary-arm64 clean

help:
	@echo "GraphBus — available targets:"
	@echo "  install        Install in editable mode + dev deps"
	@echo "  test           Run test suite (all directories)"
	@echo "  binary         Build CLI binary for current machine"
	@echo "  binary-x86_64  Build macOS x86_64 binary (run on macOS)"
	@echo "  binary-arm64   Build macOS arm64 binary (run on macOS)"
	@echo "  clean          Remove build artifacts"

install:
	pip install -e ".[dev]"

test:
	python -m pytest tests/cli/ tests/runtime/ tests/deployment/ tests/mcp/ tests/messaging/ tests/api/ \
		-q --no-header --override-ini="addopts=-q"

binary:
	bash scripts/build_binary.sh

binary-x86_64:
	bash scripts/build_binary.sh x86_64

binary-arm64:
	bash scripts/build_binary.sh arm64

clean:
	rm -rf dist/ build/_pyinstaller/ *.egg-info/ __pycache__/ .coverage htmlcov/
