"""Graph visualization."""

from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml


def render_graph(graph: Dict[str, Any]) -> str:
    """Render ASCII graph visualization."""
    lines = []
    agents = graph.get("agents", [])
    
    lines.append("Agent Graph:")
    lines.append("=" * 50)
    
    for agent in agents:
        name = agent.get("name", "Unknown")
        tier = agent.get("model_tier", "unknown")
        lines.append(f"  • {name} ({tier})")
    
    edges = graph.get("edges", [])
    if edges:
        lines.append("\nDependencies:")
        for edge in edges:
            from_agent = edge.get("from")
            to_agent = edge.get("to")
            lines.append(f"  {from_agent} → {to_agent}")
    
    return "\n".join(lines)


class GraphViewer:
    """View and interact with agent graph."""
    
    def __init__(self, graphbus_dir: Path):
        self.graphbus_dir = Path(graphbus_dir)
        self.selected: Optional[str] = None
        self.graph_data: Optional[Dict[str, Any]] = None
        self._load_graph()
    
    def _load_graph(self) -> None:
        """Load graph.yaml from .graphbus directory."""
        graph_path = self.graphbus_dir / "graph.yaml"
        if graph_path.exists():
            with open(graph_path) as f:
                self.graph_data = yaml.safe_load(f)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """Get all agents from graph."""
        if not self.graph_data:
            return []
        return self.graph_data.get("agents", [])
    
    def select_agent(self, agent_name: str) -> None:
        """Select an agent."""
        self.selected = agent_name
    
    def get_agent_details(self, agent_name: str) -> Dict[str, Any]:
        """Get details about a specific agent."""
        if not self.graph_data:
            return {"name": agent_name}
        
        for agent in self.list_agents():
            if agent.get("name") == agent_name:
                return agent
        
        return {"name": agent_name}
    
    def get_dependencies(self, agent_name: str) -> List[str]:
        """Get agents that depend on this agent."""
        if not self.graph_data:
            return []
        
        deps = []
        for edge in self.graph_data.get("edges", []):
            if edge.get("from") == agent_name:
                deps.append(edge.get("to"))
        
        return deps
    
    def render(self) -> str:
        """Render graph visualization."""
        if not self.graph_data:
            return "No graph data loaded"
        return render_graph(self.graph_data)
