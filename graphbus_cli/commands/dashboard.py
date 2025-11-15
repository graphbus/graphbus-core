"""
Dashboard command - Web-based visualization dashboard
"""

import click
import sys
import webbrowser
import threading
import time
from pathlib import Path

from graphbus_core.runtime.executor import RuntimeExecutor
from graphbus_core.config import RuntimeConfig
from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header
)
from graphbus_cli.utils.errors import RuntimeError as CLIRuntimeError


@click.command()
@click.argument('artifacts_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    '--port',
    type=int,
    default=8080,
    help='Web server port (default: 8080)'
)
@click.option(
    '--host',
    default='localhost',
    help='Web server host (default: localhost)'
)
@click.option(
    '--no-browser',
    is_flag=True,
    help='Do not open browser automatically'
)
@click.option(
    '--no-message-bus',
    is_flag=True,
    help='Disable message bus'
)
def dashboard(artifacts_dir: str, port: int, host: str, no_browser: bool, no_message_bus: bool):
    """
    Start web-based visualization dashboard.

    \b
    Launches a web server with an interactive dashboard showing:
      - Agent graph visualization
      - Real-time message flow
      - Agent status indicators
      - Live metrics and statistics
      - Event history timeline
      - Method call logs

    \b
    Examples:
      graphbus dashboard .graphbus                # Start on localhost:8080
      graphbus dashboard .graphbus --port 3000    # Custom port
      graphbus dashboard .graphbus --no-browser   # Don't auto-open browser

    \b
    Dashboard Features:
      - Interactive graph visualization (D3.js)
      - Real-time updates via WebSockets
      - Agent health monitoring
      - Event flow animation
      - Performance metrics charts

    \b
    Access:
      Open http://localhost:8080 in your browser
      Press Ctrl+C to stop the dashboard
    """
    artifacts_path = Path(artifacts_dir).resolve()
    executor = None

    try:
        # Check if Flask is available
        try:
            import flask
            from flask import Flask, render_template, jsonify, request
            from flask_socketio import SocketIO, emit
        except ImportError:
            print_error("Flask and Flask-SocketIO are required for the dashboard")
            print_info("Install with: pip install flask flask-socketio")
            raise click.Abort()

        # Add parent directory to Python path
        parent_dir = artifacts_path.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))

        # Display startup info
        print_header("GraphBus Visualization Dashboard")
        print_info(f"Loading artifacts from: {artifacts_path}")
        console.print()

        # Create runtime config
        config = RuntimeConfig(
            artifacts_dir=str(artifacts_path),
            enable_message_bus=not no_message_bus
        )

        # Start runtime
        with console.status("[cyan]Starting runtime...[/cyan]", spinner="dots"):
            executor = RuntimeExecutor(config)
            executor.start()

        console.print()
        print_success("Runtime started")
        console.print()

        # Create Flask app
        app = Flask(__name__, template_folder=_get_template_dir())
        app.config['SECRET_KEY'] = 'graphbus-dashboard-secret'
        socketio = SocketIO(app, cors_allowed_origins="*")

        # Setup routes
        _setup_routes(app, socketio, executor)

        # Start background thread for updates
        stop_event = threading.Event()
        update_thread = threading.Thread(
            target=_update_loop,
            args=(socketio, executor, stop_event)
        )
        update_thread.daemon = True
        update_thread.start()

        # Open browser
        url = f"http://{host}:{port}"
        if not no_browser:
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()

        console.print()
        print_success(f"Dashboard running at: {url}")
        print_info("Press Ctrl+C to stop")
        console.print()

        # Run Flask app
        socketio.run(app, host=host, port=port, debug=False, use_reloader=False)

    except KeyboardInterrupt:
        console.print()
        print_info("Shutting down dashboard...")
        if executor:
            executor.stop()
        print_success("Dashboard stopped")

    except Exception as e:
        console.print()
        if executor:
            executor.stop()
        raise CLIRuntimeError(f"Dashboard error: {str(e)}")


def _get_template_dir() -> str:
    """Get dashboard template directory"""
    # Templates are in graphbus_cli/dashboard/templates
    from pathlib import Path
    cli_dir = Path(__file__).parent.parent
    template_dir = cli_dir / "dashboard" / "templates"

    # Create if doesn't exist
    template_dir.mkdir(parents=True, exist_ok=True)

    # Create index.html if it doesn't exist
    index_path = template_dir / "index.html"
    if not index_path.exists():
        index_path.write_text(_get_default_template())

    return str(template_dir)


def _setup_routes(app, socketio, executor: RuntimeExecutor):
    """Setup Flask routes"""

    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')

    @app.route('/api/graph')
    def get_graph():
        """Get agent graph data"""
        from flask import jsonify

        nodes = []
        edges = []

        # Get agents
        for name, node in executor.get_all_nodes().items():
            nodes.append({
                'id': name,
                'label': name,
                'type': 'agent',
                'status': 'running'
            })

        # Get subscriptions (edges)
        if executor.router:
            all_handlers = executor.router.get_all_handlers()
            for topic, handlers in all_handlers.items():
                for handler_info in handlers:
                    node_name = handler_info['node_name']
                    edges.append({
                        'source': topic,
                        'target': node_name,
                        'label': handler_info['handler_name']
                    })

                # Add topic node
                if topic not in [n['id'] for n in nodes]:
                    nodes.append({
                        'id': topic,
                        'label': topic,
                        'type': 'topic',
                        'status': 'active'
                    })

        return jsonify({'nodes': nodes, 'edges': edges})

    @app.route('/api/stats')
    def get_stats():
        """Get runtime statistics"""
        from flask import jsonify
        stats = executor.get_stats()
        return jsonify(stats)

    @app.route('/api/agents')
    def get_agents():
        """Get agent list"""
        from flask import jsonify
        agents = []

        for name, node in executor.get_all_nodes().items():
            agent_info = {
                'name': name,
                'status': 'running',
                'type': type(node).__name__
            }

            # Add health info if available
            if executor.health_monitor:
                health = executor.health_monitor.get_agent_health(name)
                if health:
                    agent_info['health'] = health['status']
                    agent_info['success_rate'] = health.get('success_rate', 100.0)

            agents.append(agent_info)

        return jsonify(agents)

    @app.route('/api/events')
    def get_events():
        """Get recent event timeline"""
        from flask import jsonify, request
        limit = int(request.args.get('limit', 100))

        events = []
        if hasattr(executor, '_event_history'):
            # Get recent events from executor's history
            events = executor._event_history[-limit:]

        return jsonify(events)

    @app.route('/api/method_logs')
    def get_method_logs():
        """Get recent method call logs"""
        from flask import jsonify, request
        limit = int(request.args.get('limit', 100))

        logs = []
        if hasattr(executor, '_method_call_history'):
            # Get recent method calls from executor's history
            logs = executor._method_call_history[-limit:]

        return jsonify(logs)

    @socketio.on('connect')
    def handle_connect():
        """Handle WebSocket connection"""
        print("[Dashboard] Client connected")
        emit('connected', {'status': 'connected'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle WebSocket disconnection"""
        print("[Dashboard] Client disconnected")


def _update_loop(socketio, executor: RuntimeExecutor, stop_event):
    """Background thread to push updates to clients"""
    last_event_count = 0
    last_method_count = 0

    while not stop_event.is_set():
        try:
            # Get current stats
            stats = executor.get_stats()

            # Emit stats update to all connected clients
            socketio.emit('stats_update', stats)

            # Emit new events if any
            if hasattr(executor, '_event_history'):
                current_event_count = len(executor._event_history)
                if current_event_count > last_event_count:
                    new_events = executor._event_history[last_event_count:]
                    socketio.emit('new_events', new_events)
                    last_event_count = current_event_count

            # Emit new method logs if any
            if hasattr(executor, '_method_call_history'):
                current_method_count = len(executor._method_call_history)
                if current_method_count > last_method_count:
                    new_logs = executor._method_call_history[last_method_count:]
                    socketio.emit('new_method_logs', new_logs)
                    last_method_count = current_method_count

            # Sleep for 1 second
            time.sleep(1)

        except Exception as e:
            print(f"[Dashboard] Update error: {e}")
            time.sleep(1)


def _get_default_template() -> str:
    """Get default HTML template for dashboard"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GraphBus Dashboard</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
        }

        header {
            background: #2d2d2d;
            padding: 20px;
            border-bottom: 3px solid #00bcd4;
        }

        h1 {
            color: #00bcd4;
            font-size: 28px;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto auto;
            gap: 20px;
            padding: 20px;
            height: calc(100vh - 100px);
        }

        .panel {
            background: #2d2d2d;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }

        .panel h2 {
            color: #00bcd4;
            margin-bottom: 15px;
            font-size: 20px;
        }

        #graph {
            grid-column: 1 / 3;
            height: 400px;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }

        .stat-card {
            background: #3d3d3d;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }

        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #00bcd4;
        }

        .stat-label {
            font-size: 14px;
            color: #999;
            margin-top: 5px;
        }

        .agent-list {
            max-height: 300px;
            overflow-y: auto;
        }

        .agent-item {
            background: #3d3d3d;
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .status-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }

        .status-running {
            background: #4caf50;
            color: white;
        }

        .status-healthy {
            background: #4caf50;
            color: white;
        }

        .status-degraded {
            background: #ff9800;
            color: white;
        }

        .status-failed {
            background: #f44336;
            color: white;
        }

        svg {
            width: 100%;
            height: 100%;
        }

        .node circle {
            fill: #00bcd4;
            stroke: #fff;
            stroke-width: 2px;
        }

        .node.topic circle {
            fill: #9c27b0;
        }

        .node text {
            fill: #e0e0e0;
            font-size: 12px;
            text-anchor: middle;
        }

        .link {
            stroke: #666;
            stroke-width: 2px;
            marker-end: url(#arrowhead);
        }

        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }

        .connected {
            background: #4caf50;
            color: white;
        }

        .disconnected {
            background: #f44336;
            color: white;
        }
    </style>
</head>
<body>
    <div class="connection-status disconnected" id="connectionStatus">Disconnected</div>

    <header>
        <h1>🚀 GraphBus Dashboard</h1>
        <p style="color: #999; margin-top: 5px;">Real-time agent graph visualization and monitoring</p>
    </header>

    <div class="container">
        <div class="panel" id="graph">
            <h2>Agent Graph</h2>
            <svg id="graphSvg"></svg>
        </div>

        <div class="panel">
            <h2>Statistics</h2>
            <div class="stat-grid" id="statsGrid">
                <div class="stat-card">
                    <div class="stat-value" id="nodeCount">0</div>
                    <div class="stat-label">Agents</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="messageCount">0</div>
                    <div class="stat-label">Messages</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="statusValue">STOPPED</div>
                    <div class="stat-label">Status</div>
                </div>
            </div>
        </div>

        <div class="panel">
            <h2>Agents</h2>
            <div class="agent-list" id="agentList"></div>
        </div>
    </div>

    <script>
        // WebSocket connection
        const socket = io();

        socket.on('connect', () => {
            console.log('Connected to server');
            document.getElementById('connectionStatus').textContent = 'Connected';
            document.getElementById('connectionStatus').className = 'connection-status connected';
            loadInitialData();
        });

        socket.on('disconnect', () => {
            console.log('Disconnected from server');
            document.getElementById('connectionStatus').textContent = 'Disconnected';
            document.getElementById('connectionStatus').className = 'connection-status disconnected';
        });

        socket.on('stats_update', (data) => {
            updateStats(data);
        });

        // Load initial data
        function loadInitialData() {
            fetch('/api/graph')
                .then(r => r.json())
                .then(data => renderGraph(data));

            fetch('/api/agents')
                .then(r => r.json())
                .then(data => updateAgentList(data));
        }

        // Update stats
        function updateStats(stats) {
            document.getElementById('nodeCount').textContent = stats.nodes_count || 0;
            document.getElementById('statusValue').textContent = stats.is_running ? 'RUNNING' : 'STOPPED';

            if (stats.message_bus) {
                document.getElementById('messageCount').textContent = stats.message_bus.messages_published || 0;
            }
        }

        // Update agent list
        function updateAgentList(agents) {
            const list = document.getElementById('agentList');
            list.innerHTML = agents.map(agent => `
                <div class="agent-item">
                    <span>${agent.name}</span>
                    <span class="status-badge status-${agent.status || 'running'}">${agent.status || 'running'}</span>
                </div>
            `).join('');
        }

        // Render graph visualization
        function renderGraph(data) {
            const svg = d3.select('#graphSvg');
            svg.selectAll('*').remove();

            const width = document.getElementById('graph').clientWidth - 40;
            const height = 350;

            // Add arrow marker
            svg.append('defs').append('marker')
                .attr('id', 'arrowhead')
                .attr('viewBox', '-0 -5 10 10')
                .attr('refX', 20)
                .attr('refY', 0)
                .attr('orient', 'auto')
                .attr('markerWidth', 8)
                .attr('markerHeight', 8)
                .append('path')
                .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
                .attr('fill', '#666');

            const simulation = d3.forceSimulation(data.nodes)
                .force('link', d3.forceLink(data.edges).id(d => d.id).distance(150))
                .force('charge', d3.forceManyBody().strength(-300))
                .force('center', d3.forceCenter(width / 2, height / 2));

            const g = svg.append('g');

            const link = g.append('g')
                .selectAll('line')
                .data(data.edges)
                .enter().append('line')
                .attr('class', 'link');

            const node = g.append('g')
                .selectAll('g')
                .data(data.nodes)
                .enter().append('g')
                .attr('class', d => `node ${d.type}`)
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));

            node.append('circle')
                .attr('r', 12);

            node.append('text')
                .attr('dy', 25)
                .text(d => d.label);

            simulation.on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);

                node
                    .attr('transform', d => `translate(${d.x},${d.y})`);
            });

            function dragstarted(event, d) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }

            function dragged(event, d) {
                d.fx = event.x;
                d.fy = event.y;
            }

            function dragended(event, d) {
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }
        }

        // Initial load
        if (socket.connected) {
            loadInitialData();
        }

        // Refresh graph every 5 seconds
        setInterval(() => {
            if (socket.connected) {
                fetch('/api/agents')
                    .then(r => r.json())
                    .then(data => updateAgentList(data));
            }
        }, 5000);
    </script>
</body>
</html>
"""
