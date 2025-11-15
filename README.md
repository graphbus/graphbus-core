# GraphBus Core

Agent-driven code refactoring framework using LLMs and graph-based orchestration.

## 🎯 Overview

GraphBus Core is a Python library that treats each class as an agent node in a graph. It operates in two distinct modes:

### Build Mode (Agents Active - Code Mutable)
- Each Python class has an **LLM-powered agent** with a system prompt
- Agents can **read and analyze** their source code
- Agents **negotiate** with each other via proposals/evaluations/commits
- Agents can **refactor code** collaboratively based on consensus
- Uses **networkx** for DAG-based agent orchestration
- Output: **Modified source code** + build artifacts

### Runtime Mode (Agents Dormant - Code Immutable)
- Code executes **statically** (traditional Python)
- No LLM reasoning, no negotiations, no modifications
- Simple pub/sub message routing (optional)
- Agents are metadata only
- Output: **Program execution** results

## 📦 Installation

```bash
pip install -r requirements.txt
```

**Requirements:** Python 3.10+, networkx >= 3.0

## 🚀 Quick Start

The Hello World example demonstrates the basic Build Mode workflow:

```bash
cd examples/hello_graphbus
python3 build.py
```

See the full example in `examples/hello_graphbus/` and detailed docs in `docs/core/`.

## ✅ Current Status

### Implemented
- ✅ Core model primitives (Message, Event, Proposal, Schema, etc.)
- ✅ GraphBusNode base class with Build/Runtime mode distinction
- ✅ Decorators (@schema_method, @subscribe, @depends_on)
- ✅ Build Mode infrastructure (scanner, extractor, graph builder)
- ✅ networkx-based agent graph with topological sort
- ✅ BuildArtifacts with JSON serialization
- ✅ Hello World example project

### Next Priorities
- 🚧 LLMAgent implementation
- 🚧 NegotiationEngine
- 🚧 RuntimeEngine
- 🚧 macOS Swift frontend

## 📚 Documentation

- `docs/core/design.md` - Full architecture specification
- `docs/core/sample_proj.md` - Hello World walkthrough
- `docs/core/pipeline.md` - Build/Runtime pipeline details
- `docs/core/pipeline-additional-info.md` - Negotiation mechanics