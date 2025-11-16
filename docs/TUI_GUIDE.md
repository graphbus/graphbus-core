# GraphBus TUI (Text User Interface) Guide

## Overview

The GraphBus TUI provides an interactive, menu-driven terminal interface for all GraphBus CLI commands. It offers a visual way to build, run, and manage agent graphs without memorizing command-line syntax.

## Installation

The TUI requires the `textual` package:

```bash
# Install textual
pip install textual

# Or install graphbus with TUI support
pip install graphbus[tui]
```

## Launching the TUI

```bash
# Launch with default dark theme
graphbus tui

# Launch with light theme
graphbus tui --theme light
```

## Features

### 🎨 Visual Interface
- Menu-driven navigation
- Tabbed interface for command categories
- Real-time output display
- Interactive forms with input validation
- Syntax-highlighted output

### ⌨️ Keyboard Shortcuts
- `h` - Home screen
- `b` - Build & Validate
- `r` - Runtime
- `d` - Dev Tools
- `p` - Deploy
- `a` - Advanced
- `q` - Quit
- `?` - Help
- `Tab` - Move between fields
- `Enter` - Submit/Select
- `Escape` - Go back

### 📋 Command Categories

#### 1. Home Screen (h)
- Welcome and overview
- Quick action buttons
- System information

#### 2. Build & Validate (b)
**Tabs:**
- **Build**: Build agent graphs from source
  - Input: Agents directory, output directory
  - Options: Basic build, build + validate, build with agent orchestration
- **Validate**: Validate agent definitions
  - Options: Basic, strict mode, check cycles
- **Inspect**: Inspect build artifacts
  - Options: Graph, agents, topics

#### 3. Runtime (r)
**Tabs:**
- **Run**: Start GraphBus runtime
  - Checkboxes: State persistence, hot reload, health monitoring, debug mode
  - Actions: Start, stop, show stats
- **REPL**: Interactive runtime REPL
  - Launches in external terminal for full interactivity
- **State**: Manage agent state
  - Actions: Save, load, clear, inspect

#### 4. Dev Tools (d)
**Tabs:**
- **Init Project**: Create new project from template
  - Templates: basic, microservices, etl, chatbot, workflow
- **Generate Agent**: Create agent boilerplate
  - Inputs: Agent name, methods, subscriptions
  - Options: With or without tests
- **Profile**: Performance profiling
  - Output formats: Text, JSON, HTML flame graphs
- **Dashboard**: Launch web visualization
  - Configurable port

#### 5. Deploy (p)
**Tabs:**
- **Docker**: Containerization
  - Generate Dockerfile and docker-compose.yml
  - Build and run containers
  - Python version selection
- **Kubernetes**: K8s deployment
  - Generate manifests (Deployment, Service, ConfigMap, etc.)
  - Apply to cluster
  - Check deployment status
- **CI/CD**: Pipeline generation
  - Platforms: GitHub Actions, GitLab CI, Jenkins
  - Options: Docker build, K8s deploy, coverage

#### 6. Advanced (a)
**Tabs:**
- **Contracts**: API contract management
  - Actions: List, validate, diff, impact analysis
- **Migrations**: Schema migration framework
  - Actions: Create, plan, apply, status
- **Coherence**: Long-form coherence tracking
  - Actions: Check, report, drift detection, visualize
- **Negotiation**: LLM agent orchestration (EXPERIMENTAL)
  - LLM models: Claude, GPT-4
  - Requires API key in environment

## Usage Examples

### Example 1: Create and Build a New Project

1. Launch TUI: `graphbus tui`
2. Press `d` (Dev Tools)
3. Go to "Init Project" tab
4. Enter project name: `my-agent-system`
5. Select template: `microservices`
6. Click "Create Project"
7. Press `b` (Build & Validate)
8. Go to "Build" tab
9. Enter agents directory: `my-agent-system/agents`
10. Click "Build"

### Example 2: Run and Monitor Runtime

1. Launch TUI: `graphbus tui`
2. Press `r` (Runtime)
3. Go to "Run" tab
4. Enter artifacts directory: `.graphbus`
5. Check "Enable State Persistence"
6. Check "Enable Health Monitoring"
7. Click "Start Runtime"
8. View output in real-time

### Example 3: Deploy with Docker

1. Launch TUI: `graphbus tui`
2. Press `p` (Deploy)
3. Go to "Docker" tab
4. Enter project directory: `.`
5. Enter image name: `my-graphbus-app`
6. Select Python version: `3.11`
7. Check "Generate docker-compose.yml"
8. Click "Generate Dockerfile"
9. Click "Build Image"
10. Click "Run Container"

### Example 4: Profile Performance

1. Launch TUI: `graphbus tui`
2. Press `d` (Dev Tools)
3. Go to "Profile" tab
4. Enter artifacts directory: `.graphbus`
5. Enter duration: `60` (seconds)
6. Enter output file: `profile_report.html`
7. Click "Profile (HTML)"
8. Open report in browser

## Tips & Tricks

### Navigation
- Use keyboard shortcuts for fast navigation
- Tab key cycles through input fields
- Mouse clicks work on all buttons

### Output Display
- Output areas are scrollable with mouse or arrow keys
- Copy output text with mouse selection
- Output updates in real-time for long-running commands

### Command Execution
- All commands run with proper error handling
- Exit codes and error messages are displayed
- Commands timeout after 30-60 seconds (configurable)

### Interactive Commands
- REPL launches in external terminal for full interactivity
- Dashboard opens in web browser automatically
- Runtime can run in background while using TUI

### Themes
- Dark theme (default): Better for low-light environments
- Light theme: Better for bright environments
- Theme persists only for current session

## Troubleshooting

### TUI Won't Launch
**Error:** "textual package is required"
**Solution:** Install textual: `pip install textual`

### Commands Not Found
**Error:** "graphbus command not found"
**Solution:** Ensure graphbus is installed: `pip install graphbus`

### Output Not Updating
- Try clicking the button again
- Check that the command hasn't timed out
- Verify input paths are correct

### REPL Won't Start
- REPL requires external terminal
- On macOS: Ensure Terminal.app is available
- On Linux: Install x-terminal-emulator
- On Windows: cmd.exe should be available

### Dashboard Won't Open
- Check that port is not already in use
- Verify artifacts directory exists
- Browser should open automatically

## Architecture

### Component Structure
```
graphbus_cli/tui/
├── __init__.py           # TUI package
├── app.py                # Main TUI application
└── screens/
    ├── __init__.py
    ├── home.py           # Home screen
    ├── build.py          # Build & Validate
    ├── runtime.py        # Runtime management
    ├── dev_tools.py      # Dev tools
    ├── deploy.py         # Deployment
    └── advanced.py       # Advanced features
```

### How It Works
1. **App Layer**: Main TUI app with navigation and layout
2. **Screen Layer**: Individual screens for command categories
3. **Widget Layer**: Textual widgets (buttons, inputs, text areas)
4. **Execution Layer**: Subprocess calls to GraphBus CLI commands

### Command Execution
- All commands execute via `subprocess.run()`
- Output is captured and displayed in real-time
- Errors are caught and displayed with helpful messages
- Timeouts prevent hanging on long-running commands

## Comparison: TUI vs CLI

| Feature | TUI | CLI |
|---------|-----|-----|
| **Ease of Use** | Visual, menu-driven | Command-line syntax |
| **Learning Curve** | Gentle, discoverable | Steeper, requires memorization |
| **Speed** | Slower (navigation) | Faster (direct commands) |
| **Automation** | Not suitable | Perfect for scripts |
| **Output** | Formatted, scrollable | Raw text |
| **Help** | Built-in, contextual | `--help` flags |
| **Best For** | Learning, exploration | Production, automation |

## When to Use TUI

✅ **Use TUI when:**
- Learning GraphBus for the first time
- Exploring available commands and options
- Developing interactively
- Visual feedback is helpful
- Working with complex multi-step workflows

❌ **Use CLI when:**
- Writing automation scripts
- CI/CD pipelines
- Speed is critical
- Headless environments
- Remote SSH sessions with poor terminal support

## Advanced Usage

### Custom Keyboard Shortcuts
Currently, keyboard shortcuts are fixed. Future versions may support customization.

### Extending the TUI
To add new screens or commands:

1. Create new screen in `graphbus_cli/tui/screens/`
2. Import in `app.py`
3. Add navigation button and action
4. Implement command forms and handlers

### Integration with External Tools
- TUI can launch external tools (dashboard, REPL)
- Dashboard runs on configurable port
- REPL opens in native terminal

## Performance

- **Launch Time**: <1 second
- **Command Execution**: Same as CLI
- **Memory Usage**: ~50-100 MB (textual framework)
- **Responsiveness**: Real-time for most operations

## Accessibility

- Full keyboard navigation
- Mouse support optional
- High contrast themes available
- Screen reader compatibility (basic)

## Future Enhancements

Planned features:
- [ ] Command history and favorites
- [ ] Multi-runtime management
- [ ] Real-time logs streaming
- [ ] Configuration profiles
- [ ] Custom keyboard shortcuts
- [ ] Export command history
- [ ] Interactive tutorials
- [ ] Plugin system

## Contributing

To contribute to TUI development:

1. Install development dependencies: `pip install textual-dev`
2. Run textual console: `textual console`
3. Launch TUI: `graphbus tui`
4. View live debugging in console

See [CONTRIBUTING.md](../CONTRIBUTING.md) for more details.

## Support

- Issues: https://github.com/graphbus/graphbus/issues
- Discussions: https://github.com/graphbus/graphbus/discussions
- Documentation: https://docs.graphbus.dev

## License

GraphBus TUI is part of GraphBus and is released under the same license.
