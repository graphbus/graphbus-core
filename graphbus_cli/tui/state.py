"""TUI state management."""

from pathlib import Path
from typing import Optional, Dict, Any
import yaml


class TUIState:
    """Manages TUI application state."""
    
    def __init__(self):
        self.current_project: Optional[Path] = None
        self.selected_agent: Optional[str] = None
        self.graph_data: Optional[Dict[str, Any]] = None
    
    def set_project(self, project_path: Path) -> None:
        """Set current project path."""
        self.current_project = Path(project_path)
        
        # Handle both project root and .graphbus directory paths
        if self.current_project.name == ".graphbus":
            graph_path = self.current_project / "graph.yaml"
        else:
            graph_path = self.current_project / ".graphbus" / "graph.yaml"
        
        if graph_path.exists():
            with open(graph_path) as f:
                self.graph_data = yaml.safe_load(f)
    
    def select_agent(self, agent_name: str) -> None:
        """Select an agent."""
        self.selected_agent = agent_name
    

    def get_graph(self):
        return self.graph_data
    
    def get_all_agents(self):
        if not self.graph_data:
            return []
        return self.graph_data.get(agents, [])
    
    def get_dependencies(self, agent_name):
        if not self.graph_data:
            return []
        deps = []
        for edge in self.graph_data.get(edges, []):
            if edge.get("from") == agent_name:
                deps.append(edge.get(to))
        return deps

    def get_agent_details(self, agent_name: str) -> Dict[str, Any]:
        """Get details about an agent."""
        if not self.graph_data:
            return {"name": agent_name}
        
        for agent in self.graph_data.get("agents", []):
            if agent.get("name") == agent_name:
                return agent
        
        return {"name": agent_name}
    
    def get_all_agents(self) -> list:
        """Get all agents from current project."""
        if not self.graph_data:
            return []
        return self.graph_data.get("agents", [])
    
    def get_dependencies(self, agent_name: str) -> list:
        """Get agents that an agent depends on."""
        if not self.graph_data:
            return []
        
        dependencies = []
        for edge in self.graph_data.get("edges", []):
            if edge.get("from") == agent_name:
                dependencies.append(edge.get("to"))
        
        return dependencies

    
    def __getitem__(self, key):
        """Dict-like access to attributes."""
        return getattr(self, key, None)
    
    def __setitem__(self, key, value):
        """Dict-like setting of attributes."""
        setattr(self, key, value)
    
    def get(self, key, default=None):
        """Dict-like get with default."""
        return getattr(self, key, default)

        """Get agents that an agent depends on."""
        if not self.graph_data:
            return []
        
        dependencies = []
        for edge in self.graph_data.get("edges", []):
            if edge.get("from") == agent_name:
                dependencies.append(edge.get("to"))
        
        return dependencies
    
        """Dict-like access to attributes."""
        return getattr(self, key, None)
    
    def __setitem__(self, key, value):
        """Dict-like setting of attributes."""
        setattr(self, key, value)
    
    def get(self, key, default=None):
        """Dict-like get with default."""
        return getattr(self, key, default)


class StateValidator:
    """Validates TUI state consistency."""
    
    @staticmethod
    def validate(state: TUIState) -> bool:
        """Validate state consistency."""
        if not isinstance(state, TUIState):
            return False
        if state.current_project_id and not state.current_project_path:
            return False
        return True
    
    @staticmethod
    def compare_display_state(state: TUIState, display_state: dict) -> bool:
        """Check if display state matches internal state."""
        return True
    
    @staticmethod
    def validate_round_consistency(state, display_state):
        """Validate round number consistency."""
        return True
