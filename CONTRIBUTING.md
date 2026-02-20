# Contributing to GraphBus

Thanks for your interest in contributing! GraphBus is in alpha and we welcome all kinds of contributions — bug reports, feature ideas, documentation, and code.

## Getting Started

1. **Fork** the repo and clone your fork
2. **Install** in development mode:
   ```bash
   pip install -e ".[dev]"
   # or
   pip install -e . && pip install pytest pytest-cov
   ```
3. **Run the tests** to make sure everything passes:
   ```bash
   pytest
   ```
4. **Create a branch** for your work:
   ```bash
   git checkout -b feat/my-feature
   # or
   git checkout -b fix/bug-description
   ```

## Types of Contributions

### 🐛 Bug Reports

Please include:
- Python version and OS
- Minimal reproduction case
- Full error traceback
- What you expected vs. what happened

Use the [bug report issue template](.github/ISSUE_TEMPLATE/bug_report.md).

### 💡 Feature Requests

Before building something big, open an issue to discuss the idea. Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md).

Good places to look for ideas:
- The [Roadmap section in README.md](README.md#roadmap)
- Open issues labeled `help wanted` or `good first issue`

### 📖 Documentation

Documentation PRs are always welcome:
- Fix typos, clarify confusing sections
- Add examples to the `examples/` directory
- Improve docstrings in the source

### 🔧 Code Contributions

High-value areas right now:
- **LLM backends** — We're Claude-native. An OpenAI adapter in `graphbus_core/agents/` would unlock a huge audience.
- **More examples** — Real-world pipelines (data processing, API orchestration, etc.)
- **CLI commands** — There are stubs in `graphbus_cli/commands/` that need implementing
- **Test coverage** — Especially for the TUI and MCP server

## Code Style

- Follow PEP 8
- Use type hints for all public functions
- Write docstrings for public classes and methods (Google style)
- Keep functions focused and small

We use `pytest` for tests. Write tests for any new functionality.

## Pull Request Process

1. Make sure `pytest` passes with no failures
2. Add tests for new functionality
3. Update documentation if you've changed behavior
4. Keep PRs focused — one thing per PR
5. Write a clear PR description: what changed and why

PR titles should follow conventional commits:
```
feat: add OpenAI LLM backend
fix: handle empty agent directories in build
docs: improve negotiation protocol documentation
test: add coverage for RuntimeExecutor edge cases
```

## Development Tips

### Project Structure

```
graphbus_core/      ← Core library (the protocol implementation)
graphbus_cli/       ← CLI commands (click + rich)
graphbus_api/       ← REST API server
graphbus-mcp-server/ ← MCP protocol server
examples/           ← Working examples (keep these runnable)
tests/              ← Test suite (mirrors source structure)
docs/               ← Architecture documentation
```

### Running a Single Test

```bash
pytest tests/test_build/test_scanner.py -v
pytest tests/ -k "test_message_bus" -v
```

### Running the Hello World Example

```bash
cd examples/hello_graphbus
python build.py           # Static build (no LLM)
python run.py             # Run artifacts

export ANTHROPIC_API_KEY=sk-ant-...
python build.py           # Build with LLM agents negotiating
```

### Testing the CLI

```bash
graphbus --help
graphbus init test-project
graphbus build test-project/agents/ --dry-run
```

## Questions?

- Open a GitHub Discussion for general questions
- Email [hello@graphbus.com](mailto:hello@graphbus.com) for anything else

We try to respond within 48 hours.
