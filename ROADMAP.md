# GraphBus Roadmap

This document describes where GraphBus is going and roughly when. Dates are targets, not guarantees — we ship when things are right.

> **Want to influence the roadmap?** Open a [GitHub Discussion](https://github.com/graphbus/graphbus-core/discussions) or comment on the relevant issue. The most-requested features move up.

---

## Vision

GraphBus is the message bus and negotiation layer for distributed agent systems. The goal: make multi-agent coordination as natural as function calls — but with typed contracts, observable messaging, and LLM-assisted schema negotiation built in.

Long-term, every serious AI-assisted codebase will need a way to distribute reasoning across specialized agents. GraphBus is the infrastructure layer for that.

---

## Status Key

| Symbol | Meaning |
|--------|---------|
| ✅ | Shipped |
| 🔨 | In progress |
| 📅 | Planned (committed) |
| 💡 | Under consideration |
| ❌ | Deferred / won't do |

---

## v0.1 — Alpha Foundation ✅

*Released: February 2026*

The core protocol, build pipeline, and runtime are working end-to-end.

- ✅ `GraphBusNode` base class with `SYSTEM_PROMPT`, `schema_method`, `subscribe`
- ✅ Static build pipeline — analyzes agents, extracts schemas, writes `.graphbus/` artifacts
- ✅ LLM negotiation build mode (`--enable-agents`) — agents propose, vote, arbiter commits
- ✅ ArbiterService — manages proposal lifecycle, consensus scoring, commit/rollback
- ✅ RuntimeExecutor — loads artifacts, routes typed messages, validates contracts
- ✅ GraphBus message bus — typed pub/sub, topic routing, graph-aware delivery
- ✅ 18-command CLI (`graphbus init`, `build`, `run`, `inspect`, `validate`, `generate`, and more)
- ✅ REST API server (`graphbus serve`) — invoke agents over HTTP
- ✅ MCP server (`graphbus mcp`) — Claude Desktop and compatible clients
- ✅ 3 working examples: `hello_world`, `code_refactor`, `news_summarizer`
- ✅ 800+ tests, CI with GitHub Actions
- ✅ MIT licensed, CONTRIBUTING.md, CODE_OF_CONDUCT.md, issue templates

---

## v0.2 — Developer Experience 🔨

*Target: March – April 2026*

Making GraphBus easier to adopt and debug.

### CLI & Developer Tools
- 🔨 **`graphbus dev`** — hot-reload mode; re-builds on file change during development
- 📅 **`graphbus test`** — run agent unit tests with the full runtime wired in
- 📅 **`graphbus diff`** — show what changed between two `.graphbus/` artifact snapshots
- 📅 **`graphbus explain`** — natural language summary of what any agent does and why

### Debugging & Observability
- 📅 **Message trace UI** — web UI to replay message flows, inspect payloads, trace agent calls
- 📅 **Negotiation replay** — step through a past build negotiation event-by-event
- 📅 **Contract violation reports** — structured output when a message fails schema validation
- 📅 **`graphbus watch`** — tail the message bus in real time during development

### Error Messages
- 📅 Actionable error messages when schema contracts are violated at runtime
- 📅 Build-time warning when an agent's `SYSTEM_PROMPT` doesn't match its method signatures
- 📅 Suggestion engine: "did you mean `/News/Cleaned` instead of `/news/cleaned`?"

---

## v0.3 — Multi-Agent Patterns 📅

*Target: May – June 2026*

Higher-level primitives for common multi-agent architectures.

### Patterns Library
- 📅 **Pipeline pattern** — chain agents sequentially with typed handoffs (like the news pipeline tutorial)
- 📅 **Fan-out / fan-in** — one agent broadcasts; many process; results aggregate
- 📅 **Retry + circuit breaker** — built-in resilience for agents that call external APIs
- 📅 **Stateful agents** — agents with persistent state between invocations (Redis/SQLite backends)

### Schema Registry
- 📅 **Central schema registry** — define schemas once, reference them across agents
- 📅 **Schema versioning** — `v1`, `v2` schemas with backward-compatibility checking
- 📅 **Schema import/export** — share schemas between GraphBus projects

### Agent Marketplace (Early)
- 💡 **Official agent catalog** — curated agents for common tasks (HTTP fetch, DB query, LLM summarize)
- 💡 **`graphbus install fetcher-http`** — install a community-contributed agent into your project

---

## v0.4 — Scale & Production 📅

*Target: July – September 2026*

Running GraphBus at scale, in real infrastructure.

### Distributed Runtime
- 📅 **Multi-process runtime** — run agents in separate OS processes; bus handles IPC
- 📅 **Kubernetes native mode** — each agent as a separate pod; bus via message queue (Redis Streams or NATS)
- 📅 **Horizontal scaling** — multiple instances of stateless agents behind a load balancer

### Reliability
- 📅 **Dead letter queue** — capture and replay failed messages
- 📅 **Exactly-once delivery** — idempotency keys on messages
- 📅 **Health checks** — `graphbus health` endpoint; K8s readiness/liveness probes

### Monitoring
- 📅 **Prometheus metrics** — messages/sec, schema violations, negotiation duration, error rates
- 📅 **OpenTelemetry traces** — distributed tracing across multi-agent flows
- 📅 **Grafana dashboard template** — ready-to-import dashboard for GraphBus metrics

---

## v0.5 — Ecosystem 💡

*Target: Q4 2026*

The things that make GraphBus feel like a platform, not just a library.

### Integrations
- 💡 **LangChain bridge** — wrap any LangChain tool as a GraphBus agent
- 💡 **LlamaIndex bridge** — use LlamaIndex query engines as GraphBus nodes
- 💡 **Temporal integration** — GraphBus agents as Temporal activities
- 💡 **Slack / Discord bots** — ship a working bot with one `graphbus init --template slack-bot`

### Developer Cloud (Optional)
- 💡 **GraphBus Cloud** — managed bus + negotiation history + team sharing (freemium)
- 💡 **Build history** — see every negotiation round across your team's history
- 💡 **Remote agents** — share agents across projects/teams without copy-paste

### Language Support
- 💡 **TypeScript/JavaScript SDK** — `npm install graphbus-js`
- 💡 **Rust agent SDK** — for performance-critical agents
- 💡 **Protocol spec** — language-agnostic GraphBus wire format so any language can participate

---

## Not Planned (for now)

These came up in discussions but we've decided not to pursue them in the near term:

- ❌ **GUI builder for agent graphs** — the CLI is the interface; drag-and-drop adds complexity without proportional value for our target users (backend engineers)
- ❌ **Built-in vector store** — use LlamaIndex, Chroma, Pinecone, etc.; GraphBus focuses on messaging and negotiation
- ❌ **Managed LLM proxy** — we're infrastructure, not an LLM provider
- ❌ **Non-Python runtimes in v0.x** — Python first; other SDKs come after the protocol is stable

---

## How Decisions Get Made

1. **Usage data**: what are early adopters actually building?
2. **GitHub discussions**: what are people asking for?
3. **Issue votes**: 👍 on an issue moves it up the list
4. **Contributor interest**: features with willing contributors ship faster

We don't do big-bang releases. Each item above will ship as soon as it's ready — we use semantic versioning but iterate quickly within minor versions.

---

## Contributing to the Roadmap

Have a use case not covered here?

1. Open a [GitHub Discussion](https://github.com/graphbus/graphbus-core/discussions) — describe your use case, not just the feature
2. If there's existing interest, open an issue with the `roadmap` label
3. Want to build it yourself? See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to get started

The best way to get something on the roadmap is to show us you need it.

---

*Last updated: February 2026. Owned by the GraphBus core team.*
