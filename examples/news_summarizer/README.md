# GraphBus News Summarizer - Real-World Pipeline

This example demonstrates a **production-like multi-agent pipeline**: agents fetch news, clean it, and format a digest — all with negotiated schemas and deterministic runtime execution.

## What You'll Learn

- Building **linear pipelines** with agent dependencies
- **Schema negotiation** — agents agree on data contracts between stages
- **Event publishing and routing** — how agents coordinate through the message bus
- Real-world patterns for data transformation (ETL-style)

## Prerequisites

1. **Install GraphBus** (from repo):
   ```bash
   cd /path/to/graphbus-core
   pip install -e .
   ```

2. **Optional: For agent negotiation**, set an LLM API key:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   # or: OPENAI_API_KEY=..., DEEPSEEK_API_KEY=...
   ```

## Quick Start

### 1. Build the pipeline

```bash
cd examples/news_summarizer
python build.py
```

This discovers three agents and their schema contracts:
- **FetcherService** → publishes headlines
- **CleanerService** → receives raw headlines, deduplicates them
- **FormatterService** → formats cleaned headlines into a digest

**Output:**
```
✅ Build complete: 3 agents, 1 topics
Artifacts saved to: examples/news_summarizer/.graphbus
```

### 2. Run the pipeline

```bash
python run.py
```

This loads the built artifacts and demonstrates:
1. Fetching raw headlines (with mock data)
2. Cleaning and deduplicating
3. Formatting into a human-readable digest

**Example output:**
```
[FetcherService] Fetching headlines for topic: technology...
Headlines: [
  'GraphBus framework hits 1000 stars on GitHub',
  'Multi-agent systems reshape software development in 2026',
  'LLM-powered code refactoring now production-ready',
  '  Whitespace-heavy    headline   needs cleaning  '
]

[CleanerService] Auto-cleaned 3 headlines via bus (removed 1 duplicate)

[FormatterService] Formatting digest...
📰 News Digest — Technology — 2024-11-14 14:35
==================================================
  1. GraphBus framework hits 1000 stars on GitHub
  2. Multi-agent systems reshape software development in 2026
  3. LLM-powered code refactoring now production-ready
==================================================
```

### 3. Enable agent negotiation (optional)

With an LLM API key, agents propose improvements to their schemas and logic:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python build.py
```

Agents might propose:
- **FetcherService:** "Add filtering by date range"
- **CleanerService:** "Add sentiment analysis filtering"
- **FormatterService:** "Render HTML instead of plain text"

After negotiation, run the updated pipeline:
```bash
python run.py
```

## Project Structure

```
news_summarizer/
├── README.md                 # This file
├── agents/                  # Agent source code
│   ├── __init__.py
│   ├── fetcher.py          # FetcherService: fetch headlines
│   ├── cleaner.py          # CleanerService: normalize & deduplicate
│   └── formatter.py        # FormatterService: format digest
├── build.py                # Build script
├── run.py                  # Runtime demo
└── .graphbus/              # Build artifacts (created by build.py)
    ├── agents.json
    ├── graph.json
    └── topics.json
```

## The Agents

### FetcherService
**Role:** Retrieve mock news headlines by topic

```python
@schema_method(
    input_schema={"topic": str},
    output_schema={"headlines": list}
)
def fetch_headlines(self, topic: str = "technology") -> dict:
    """Return mock headlines for a given topic."""
    mock_data = {
        "technology": [...],
        "default": [...]
    }
    return {"headlines": mock_data.get(topic, mock_data["default"])}
```

**Responsibilities:**
- Provides headlines as a list of strings
- Supports multiple topics (mocked)

**In Build Mode:** Agents might propose:
- Adding real API integration (RSS, NewsAPI)
- Adding date filtering or source preferences
- Caching recent fetches

### CleanerService
**Role:** Normalize and deduplicate headlines

```python
@schema_method(
    input_schema={"headlines": list},
    output_schema={"cleaned": list, "removed": int}
)
def clean(self, headlines: list) -> dict:
    """Normalize whitespace and remove duplicates."""
    seen = set()
    cleaned = []
    for h in headlines:
        h = " ".join(h.split())  # normalize whitespace
        if h and h.lower() not in seen:
            seen.add(h.lower())
            cleaned.append(h)
    return {"cleaned": cleaned, "removed": len(headlines) - len(cleaned)}

@subscribe("/News/Raw")
def on_raw_news(self, event):
    result = self.clean(event.get("headlines", []))
    print(f"[CleanerService] Auto-cleaned {len(result['cleaned'])} headlines via bus")
```

**Responsibilities:**
- Whitespace normalization
- Case-insensitive deduplication
- Reporting removal count

**In Build Mode:** Agents might propose:
- Sentiment analysis to filter negative stories
- Language detection to filter non-English
- Spam detection heuristics
- Trend-based filtering (popular vs. niche)

### FormatterService
**Role:** Render cleaned headlines into a human-readable digest

```python
@schema_method(
    input_schema={"headlines": list, "topic": str},
    output_schema={"digest": str}
)
def format_digest(self, headlines: list, topic: str = "technology") -> dict:
    """Render a simple text digest."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"📰 News Digest — {topic.title()} — {now}", "=" * 50]
    for i, h in enumerate(headlines, 1):
        lines.append(f"  {i}. {h}")
    lines.append("=" * 50)
    return {"digest": "\n".join(lines)}
```

**Responsibilities:**
- Add header with topic and timestamp
- Number items for readability
- Format as plain text (can be extended to HTML/Markdown)

**In Build Mode:** Agents might propose:
- Markdown or HTML rendering
- Emoji icons per category
- Summary statistics (e.g., "3 articles, 2 sources")
- Sorting by relevance or date

## Schema Contracts

The agents negotiate **typed contracts** at each stage:

```
FetcherService output     CleanerService input
{"headlines": [...]}  →   {"headlines": [...]}
                          ↓
                    CleanerService output
                    {"cleaned": [...], "removed": 3}
                          ↓ (FormatterService input)
                    {"headlines": [...], "topic": str}
                          ↓
                    FormatterService output
                    {"digest": "📰 News Digest..."}
```

In Build Mode, agents can propose:
- Adding new fields (e.g., `"source"`, `"date"`, `"category"`)
- Changing field types (e.g., `headlines: list → headlines: dict`)
- Adding constraints (e.g., `"min_length": 1`)

The arbitration agent ensures compatibility across boundaries.

## Extending the Example

### Add a new agent in the pipeline

Example: **SummarizerService** (between Cleaner and Formatter)

1. Create `agents/summarizer.py`:
```python
from graphbus_core import GraphBusNode, schema_method

class SummarizerService(GraphBusNode):
    SYSTEM_PROMPT = """
    I generate 1-line summaries of headlines.
    """
    
    @schema_method(
        input_schema={"headlines": list},
        output_schema={"summaries": list}
    )
    def summarize(self, headlines: list) -> dict:
        # In Build Mode, an agent might propose using an LLM here
        summaries = [h[:50] + "..." if len(h) > 50 else h for h in headlines]
        return {"summaries": summaries}
```

2. Update `agents/formatter.py` to accept summaries instead of raw headlines.

3. Rebuild:
```bash
python build.py
```

Agents will negotiate the new schema and dependencies automatically.

### Modify the mock data

In `agents/fetcher.py`, add more topics or link to a real API:

```python
import requests  # Add to dependencies

@schema_method(...)
def fetch_headlines(self, topic: str = "technology"):
    # Real API call instead of mock data
    response = requests.get(f"https://newsapi.org/v2/everything?q={topic}")
    return {"headlines": [a["title"] for a in response.json()["articles"]]}
```

Then rebuild to let agents negotiate the new error handling.

## Commands Reference

```bash
# Build only (no LLM)
python build.py

# Build with agent negotiation
export ANTHROPIC_API_KEY="..."
python build.py

# Run the pipeline
python run.py

# Inspect the graph structure
graphbus inspect .graphbus --graph

# Inspect agent schemas
graphbus inspect .graphbus --agents

# View negotiation history
graphbus inspect-negotiation .graphbus --format timeline
```

## Real-World Extensions

This example can be extended to:

1. **Multi-source aggregation** — fetch from RSS, Reddit, HN, Twitter
2. **NLP pipeline** — add sentiment, entity extraction, topic modeling
3. **Personalization** — filter by user preferences (topics, keywords, authors)
4. **Distribution** — email digest, Slack bot, web dashboard
5. **Feedback loop** — users rate articles → agents learn preferences

All without changing the core pattern: **agents read source, propose improvements, negotiate schemas, execute deterministically at runtime.**

## Troubleshooting

### Build fails with schema errors

**Error:** `SchemaConflict: CleanerService output doesn't match FormatterService input`

**Cause:** Agents negotiated incompatible types

**Solution:** Review the negotiation log:
```bash
graphbus inspect-negotiation .graphbus
```

Then manually align schemas in source, or re-run negotiation with a different arbiter.

### Headlines not deduplicating

**Error:** Duplicate headlines appear in output

**Cause:** Case sensitivity or extra whitespace

**Check:** Look at CleanerService output in run.py logs. Verify normalization is working:
```python
# Debug: print before/after
print(f"Before clean: {headlines}")
result = self.clean(headlines)
print(f"After clean: {result['cleaned']}")
```

### Agent negotiation skipped

**Error:** Build runs but doesn't propose changes

**Solution:** Verify API key is set:
```bash
echo $ANTHROPIC_API_KEY   # Should not be empty
python build.py           # Should show "[AGENT]" lines
```

## Performance Notes

**Runtime (after build):**
- Fetch mock headlines: ~1ms
- Clean 4 headlines: ~0.1ms
- Format digest: ~0.5ms
- **Total: ~2ms** (zero LLM calls)

**Build time (with negotiation):**
- Depends on LLM latency and number of rounds
- Typical: 5-30 seconds with Claude API

## Next Steps

1. **Explore other examples:**
   - `hello_graphbus/` — Basic 4-agent pipeline
   - `spec_to_service/` — Advanced orchestration
   - `hello_world_mcp/` — MCP integration

2. **Read the architecture docs:**
   - [README.md](../../README.md) — Core concepts
   - [ROADMAP.md](../../ROADMAP.md) — Future features

3. **Build your own:**
   ```bash
   graphbus init my-data-pipeline
   cd my-data-pipeline
   # Create agents/stage1.py, agents/stage2.py, etc.
   graphbus build agents/
   ```

## Support

- **Documentation:** [README.md](../../README.md)
- **Issues:** [GitHub Issues](https://github.com/graphbus/graphbus-core/issues)
- **Questions:** [GitHub Discussions](https://github.com/graphbus/graphbus-core/discussions)

---

**Happy pipelining!** 📰
