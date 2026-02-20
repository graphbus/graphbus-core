# Changelog

All notable changes to GraphBus are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Version scheme: `MAJOR.MINOR.PATCH-stage` (currently pre-1.0 alpha).

---

## [Unreleased]

### Planned
- PyPI release (`pip install graphbus`)
- OpenAI and Ollama LLM backends
- Visual graph editor (browser-based)
- Cloud-hosted build service
- Protocol specification for non-Python implementations
- `graphbus_cli.tui` — full Textual TUI (in progress)

---

## [0.1.0-alpha] — 2026-02-01

Initial alpha release. Core protocol implemented and tested.

### Added

#### Core Framework (`graphbus_core`)
- **`GraphBusNode`** base class — subclass to define an agent
- **`@schema_method`** decorator — declare typed input/output contracts per method
- **`@subscribe`** decorator — register pub/sub handlers on the message bus
- **`@depends_on`** decorator — declare dependency edges between agents in the DAG
- **`BuildConfig`** and **`RuntimeConfig`** — typed configuration objects
- **`build_project()`** — entry point for the build pipeline

#### Build Pipeline
- **Scanner** — discovers all `GraphBusNode` subclasses in a target path
- **Extractor** — parses methods, schemas, subscriptions, system prompts per class
- **Graph Builder** — constructs `networkx` DAG from `@depends_on` edges, topological sort
- **Code Writer** — applies accepted proposal diffs to source files
- **Artifact Writer** — serializes `graph.json`, `agents.json`, `topics.json`, `build_summary.json`

#### LLM Negotiation Engine
- **Proposal protocol** — structured diffs with rationale and affected-agent lists
- **Evaluation protocol** — accept/reject decisions with reasoning and optional counter-proposals
- **Arbiter protocol** — `IS_ARBITER = True` designates a conflict-resolution agent
- **Multi-round negotiation** — configurable rounds via `--rounds` flag
- **Negotiation history** — persisted to `.graphbus/negotiation_log.json`

#### Runtime Engine
- **Artifact Loader** — loads and validates `.graphbus/` JSON artifacts
- **Message Bus** — in-process pub/sub routing, topic registry
- **Event Router** — dispatches published events to all registered `@subscribe` handlers
- **Runtime Executor** — initializes agents, runs the event loop, exposes REPL
- **State Manager** — optional agent state persistence across invocations
- **Health Monitor** — runtime health checks and status reporting
- **Hot Reload** — watches `.graphbus/` for artifact changes and reloads without restart
- **Profiler** — latency/throughput metrics per agent and topic
- **Debugger** — interactive breakpoints and step-through in REPL mode
- **Contract Validator** — runtime schema contract enforcement
- **Coherence Tracker** — detects inter-agent schema drift at runtime
- **Migration Engine** — handles artifact version upgrades

#### CLI (`graphbus` command, 18 commands)
- `graphbus build` — scan agents, build graph, emit artifacts
- `graphbus run` — load artifacts, start runtime (with optional REPL)
- `graphbus inspect` — rich display of artifact contents
- `graphbus validate` — validate schemas without building
- `graphbus init` — scaffold new project from template
- `graphbus generate agent` — generate `GraphBusNode` boilerplate
- `graphbus negotiate` — standalone negotiation round
- `graphbus inspect-negotiation` — browse negotiation history
- `graphbus profile` — runtime performance profiler
- `graphbus dashboard` — web-based visualization
- `graphbus state` — agent state persistence management
- `graphbus coherence` — inter-agent coherence check
- `graphbus contract` — schema contract validation
- `graphbus migrate` — artifact version migration
- `graphbus docker build/run` — Docker build and run helpers
- `graphbus k8s generate/deploy` — Kubernetes manifest generation and deployment
- `graphbus ci github/gitlab` — CI pipeline generation

#### API Server (`graphbus_api`)
- REST API for triggering builds and querying runtime state
- WebSocket server for real-time event streaming to UI

#### MCP Server (`graphbus-mcp-server`)
- MCP (Model Context Protocol) server — expose agents as tools to any MCP-compatible client

#### Examples
- `examples/hello_graphbus/` — minimal 4-agent Hello World pipeline
- `examples/hello_world_mcp/` — MCP integration example
- `examples/news_summarizer/` — 3-agent news fetching → cleaning → formatting pipeline

#### Testing
- Full test suite: 832 passing, 4 skipped (TUI — pending implementation)
- Build pipeline: 100% coverage (scanner, extractor, graph builder, artifact writer)
- Runtime engine: 100% coverage (loader, message bus, event router, executor)
- CLI: all commands smoke-tested via Click test runner
- Integration: end-to-end build + run cycles tested

#### Developer Experience
- `CONTRIBUTING.md` — setup guide, PR process, conventional commit format
- `CODE_OF_CONDUCT.md` — Contributor Covenant based
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/workflows/ci.yml` — GitHub Actions (pytest on Python 3.9/3.10/3.11/3.12 + ruff)
- `LICENSE` — MIT

### Architecture Notes
- **Build/Runtime separation** is the core design principle — LLMs can run at build time, runtime, or both; the bus routes messages regardless
- **networkx DAG** is the graph backbone; topological sort determines evaluation order
- **Typed pub/sub** message bus serves both build (proposals) and runtime (application events)
- **JSON artifacts** are the deployment unit — agents are loaded from artifacts at runtime

### Known Limitations
- LLM backends: Claude (Anthropic) only. OpenAI/Ollama adapters planned.
- TUI (`graphbus tui`) CLI command exists but Textual UI implementation is in progress
- PyPI package not yet published — install from source
- `IS_ARBITER = True` agents cannot have `__init__` parameters (known bug, workaround: use `super().__init__()`)

---

## Pre-Alpha History

### 2025-Q4
- Protocol design and architecture decisions
- Initial `GraphBusNode` prototype
- Build/Runtime mode separation concept validated

### 2026-01
- Full build pipeline implemented and tested
- Runtime engine implemented and tested
- CLI scaffolded with all command stubs
- Negotiation protocol first working version
- MCP server integration prototype

---

[Unreleased]: https://github.com/graphbus/graphbus-core/compare/v0.1.0-alpha...HEAD
[0.1.0-alpha]: https://github.com/graphbus/graphbus-core/releases/tag/v0.1.0-alpha
