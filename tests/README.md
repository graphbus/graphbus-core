# GraphBus Core Tests

This directory contains the test suite for GraphBus Core.

## Test Structure

```
tests/
├── build/                  # Build Mode tests
│   ├── unit/              # Unit tests for build components
│   ├── functional/        # Build workflow tests
│   └── integration/       # Build integration tests
└── runtime/               # Runtime Mode tests
    ├── unit/              # Unit tests for runtime components
    ├── functional/        # Runtime workflow tests
    └── integration/       # Runtime integration tests
```

## Test Categories

### Build Mode Tests (`tests/build/`)

Tests for Build Mode functionality (agent extraction, graph building, artifact generation).

#### Unit Tests (`tests/build/unit/`)
Tests for individual Build Mode components:
- `test_config.py` - Configuration classes (SafetyConfig, BuildConfig, etc.)
- `test_negotiation.py` - NegotiationEngine functionality
- `test_agent_def.py` - AgentDefinition and NodeMemory

#### Functional Tests (`tests/build/functional/`)
Tests for Build Mode workflows:
- `test_build_workflow.py` - Build Mode pipeline (scan, extract, build graph)

#### Integration Tests (`tests/build/integration/`)
End-to-end Build Mode tests:
- `test_hello_world.py` - Complete Hello World example build integration

### Runtime Mode Tests (`tests/runtime/`)

Tests for Runtime Mode functionality (artifact loading, message bus, event routing, execution).

#### Unit Tests (`tests/runtime/unit/`)
Tests for individual Runtime Mode components:
- `test_loader.py` - ArtifactLoader functionality
- `test_message_bus.py` - MessageBus pub/sub functionality
- `test_event_router.py` - EventRouter dispatching
- `test_executor.py` - RuntimeExecutor orchestration

#### Functional Tests (`tests/runtime/functional/`)
Tests for Runtime Mode workflows:
- `test_artifact_loading.py` - Complete artifact loading workflows
- `test_message_flow.py` - Message flow and event routing patterns

#### Integration Tests (`tests/runtime/integration/`)
End-to-end Runtime Mode tests:
- `test_hello_world_runtime.py` - Hello World runtime execution
- `test_end_to_end.py` - Complete system lifecycle tests

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test categories
```bash
# All Build Mode tests
pytest tests/build/

# All Runtime Mode tests
pytest tests/runtime/

# Build Mode unit tests only
pytest tests/build/unit/

# Runtime Mode unit tests only
pytest tests/runtime/unit/

# Functional tests only (both modes)
pytest tests/build/functional/ tests/runtime/functional/

# Integration tests only (both modes)
pytest tests/build/integration/ tests/runtime/integration/
```

### Run with coverage
```bash
pytest --cov=graphbus_core --cov-report=html
```

### Run tests by marker
```bash
# Run only fast tests (exclude slow/llm tests)
pytest -m "not slow and not llm"

# Run only unit tests
pytest -m unit

# Run only LLM tests (requires ANTHROPIC_API_KEY)
pytest -m llm
```

## Test Markers

Tests are marked with the following markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.functional` - Functional tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Tests that take a long time to run
- `@pytest.mark.llm` - Tests that require LLM API access

## Environment Variables

Some tests require environment variables:

- `ANTHROPIC_API_KEY` - Required for LLM-powered agent tests (marked with `@pytest.mark.llm`)

Tests requiring environment variables will be automatically skipped if the variable is not set.

## Writing New Tests

### Unit Test Template
```python
"""
Unit tests for MyModule
"""
import pytest
from graphbus_core.module import MyClass

class TestMyClass:
    """Tests for MyClass"""

    def test_initialization(self):
        """Test MyClass initialization"""
        obj = MyClass()
        assert obj is not None
```

### Functional Test Template
```python
"""
Functional tests for MyWorkflow
"""
import pytest

@pytest.mark.functional
class TestMyWorkflow:
    """Tests for MyWorkflow"""

    @pytest.fixture
    def setup_workflow(self):
        """Setup fixture for workflow tests"""
        # Setup code
        yield data
        # Teardown code

    def test_workflow(self, setup_workflow):
        """Test complete workflow"""
        # Test implementation
```

### Integration Test Template
```python
"""
Integration tests for MyFeature
"""
import pytest

@pytest.mark.integration
class TestMyFeatureIntegration:
    """Integration tests for MyFeature"""

    def test_end_to_end(self):
        """Test end-to-end feature"""
        # Test implementation
```

## Coverage Reports

After running tests with coverage, view the HTML report:

```bash
open htmlcov/index.html
```

## Continuous Integration

Tests are designed to run in CI environments. To simulate CI locally:

```bash
# Run all tests except slow/llm tests
pytest -m "not slow and not llm" --tb=short

# Generate coverage report
pytest --cov=graphbus_core --cov-report=term-missing --cov-report=xml
```

## Troubleshooting

### Import Errors
If you encounter import errors, ensure you're running pytest from the project root:
```bash
cd /path/to/graphbus
pytest
```

### Skipped Tests
Some tests may be skipped if:
- `ANTHROPIC_API_KEY` is not set (LLM tests)
- Test is marked as `slow` and you're running with `-m "not slow"`

To see why tests are skipped:
```bash
pytest -v -rs
```
