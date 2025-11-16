# GraphBus Chat Interface

## The Better Way to Use GraphBus

Instead of remembering CLI commands or navigating through menus, just **tell GraphBus what you want to do** in plain English!

## Launch

```bash
graphbus tui
```

## How It Works

You see a chat interface. Just type what you want:

```
You: create a new microservices project called my-api
```

GraphBus figures out you want:
```bash
$ graphbus init my-api --template microservices
```

And runs it for you!

## What You Can Say

### 🚀 Getting Started

**Create Projects:**
- "Create a new microservices project called my-api"
- "Start a new chatbot project"
- "Init an ETL project called data-pipeline"

**Build:**
- "Build the agents in ./agents"
- "Build and validate my agents"
- "Compile agents from src/agents"

**Run:**
- "Run the runtime"
- "Start with state persistence"
- "Run with hot reload and health monitoring"
- "Start interactive REPL"

### 🔍 Inspection

- "Show me the agent graph"
- "List all agents"
- "Show all topics"
- "Inspect the artifacts"

### 🛠️ Development

- "Generate agent OrderProcessor"
- "Create agent PaymentService with tests"
- "Validate agents in strict mode"
- "Profile performance"
- "Launch dashboard"

### 🚢 Deployment

- "Deploy to docker"
- "Deploy to kubernetes"
- "Generate docker files"
- "Create k8s manifests"

### 📚 Help

- `help` - Show all capabilities
- `examples` - See more example requests
- `clear` - Clear the chat
- `quit` or `exit` - Leave the TUI

## Examples of Natural Requests

Just type naturally - the interface understands:

```
You: create a new project called order-system
Assistant: Creating a basic project called 'order-system'...
$ graphbus init order-system --template basic
✅ Success!
```

```
You: build agents from ./src/agents with validation
Assistant: Building agents from './src/agents'...
$ graphbus build ./src/agents --validate
✅ Success!
```

```
You: run with state persistence and hot reload
Assistant: Starting runtime from '.graphbus'...
$ graphbus run .graphbus --enable-state-persistence --enable-hot-reload
✅ Success!
```

```
You: generate agent PaymentProcessor with tests
Assistant: Generating agent 'PaymentProcessor'...
$ graphbus generate agent PaymentProcessor --with-tests
✅ Success!
```

## Key Features

✅ **No memorization** - Just describe what you want
✅ **Natural language** - Type like you're talking to a person
✅ **Smart parsing** - Figures out project names, directories, options
✅ **Real-time feedback** - See commands and output immediately
✅ **Conversational** - Chat history preserved during session
✅ **Helpful** - Type 'help' or 'examples' anytime

## Keyboard Shortcuts

- `Ctrl+C` - Quit
- `Ctrl+L` - Clear chat
- `Enter` - Send message
- `↑/↓` - Scroll chat history (mouse/trackpad)

## Comparison: Old vs New

### Old TUI (Form-based)
```
Navigate → Dev Tools → Init Project tab
Fill in: Project Name [_______]
         Template   [dropdown▼]
Click: [Create Project]
```

### New TUI (Chat-based) ✨
```
You: create a microservices project called my-api
```

Much better! 🎉

## Smart Features

### Extracts Information Automatically

**Project names:**
- "called my-api" → project name: my-api
- "named data-processor" → project name: data-processor

**Templates:**
- "microservices project" → --template microservices
- "etl system" → --template etl
- "chatbot" → --template chatbot

**Directories:**
- "in ./agents" → agents directory: ./agents
- "from src/agents" → agents directory: src/agents

**Options:**
- "with validation" → adds --validate
- "with state persistence" → adds --enable-state-persistence
- "with tests" → adds --with-tests
- "strict mode" → adds --strict

### Understands Synonyms

All of these work:
- "create" / "init" / "start" / "new project"
- "build" / "compile"
- "run" / "start" / "execute"
- "show" / "list" / "display" / "view"

## Why This Is Better

1. **Faster** - Type one line vs navigate menus
2. **Intuitive** - No learning curve
3. **Flexible** - Any phrasing works
4. **Conversational** - Feels natural
5. **Error-friendly** - Just rephrase if misunderstood

## When to Use What

### Use Chat TUI When:
- ✅ Learning GraphBus
- ✅ Interactive development
- ✅ Quick one-off tasks
- ✅ Exploring features
- ✅ You prefer UI over terminal

### Use CLI When:
- ✅ Scripting/automation
- ✅ CI/CD pipelines
- ✅ Precise control needed
- ✅ Batch operations
- ✅ You prefer terminal

## Tips

1. **Be specific** - "create microservices project called my-api" is better than just "create project"
2. **Use natural language** - Don't try to mimic command syntax
3. **Check output** - Commands and results are shown
4. **Type 'examples'** - See what's possible
5. **Type 'help'** - See all capabilities

## Future Enhancements

Coming soon:
- [ ] Multi-step workflows (e.g., "create, build, and run my-api")
- [ ] Question asking (TUI asks for missing info)
- [ ] Command suggestions
- [ ] History navigation (↑/↓ in input)
- [ ] Tab completion
- [ ] AI-powered intent recognition
- [ ] Save frequently used commands

## Feedback

This is the new default! If you prefer the old form-based interface, you can still access it:

```python
from graphbus_cli.tui.app import GraphBusTUI
app = GraphBusTUI()
app.run()
```

But we think you'll love the chat interface! 💬

## Summary

**Before:** Navigate menus → Fill forms → Click buttons
**Now:** Just type what you want! 🚀

Launch it:
```bash
graphbus tui
```

Then just tell it what you want to do!
