"""Model tier editor."""

from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml


# Model tier definitions
MODELS_BY_TIER = {
    "light": ["gemma-3-4b", "gemma-3-8b"],
    "medium": ["claude-haiku-4-5"],
    "heavy": ["claude-sonnet-4-6", "claude-opus-4-6"],
}


def get_available_models(tier):
    """Get available models for a tier."""
    return MODELS_BY_TIER.get(tier, [])


def validate_model(model, tier):
    """Validate model is valid for tier."""
    return model in MODELS_BY_TIER.get(tier, []) or model in [m for models in MODELS_BY_TIER.values() for m in models]


class ModelEditor:
    """Edit and manage model assignments for agents."""
    
    def __init__(self, graphbus_dir: Path):
        self.graphbus_dir = Path(graphbus_dir)
        self.selected: Optional[str] = None
        self.overrides: Dict[str, Dict[str, str]] = {}
        self._load_overrides()
        self.graph_data = self._load_graph()
    
    def _load_graph(self) -> Dict[str, Any]:
        """Load graph.yaml."""
        graph_path = self.graphbus_dir / "graph.yaml"
        if graph_path.exists():
            with open(graph_path) as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _load_overrides(self) -> None:
        """Load model config overrides."""
        config_path = self.graphbus_dir / "model-config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
                self.overrides = data.get("overrides", {})
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents with their tiers."""
        agents = []
        for agent in self.graph_data.get("agents", []):
            name = agent.get("name")
            tier = agent.get("model_tier", "unknown")
            override = self.overrides.get(name)
            agents.append({
                "name": name,
                "tier": tier,
                "provider": agent.get("model_provider"),
                "override": override,
            })
        return agents
    
    def select_agent(self, agent_name: str) -> None:
        """Select an agent."""
        self.selected = agent_name
    
    def get_override_options(self, agent_name: str) -> List[str]:
        """Get available model options for an agent."""
        options = []
        for tier, models in MODELS_BY_TIER.items():
            options.extend(models)
        return options
    
    def apply_override(self, agent_name: str, tier: str, model: str) -> None:
        """Apply a model override to an agent."""
        if agent_name not in self.overrides:
            self.overrides[agent_name] = {}
        
        self.overrides[agent_name] = {"tier": tier, "model": model}
        self._save_overrides()
    
    def revert_override(self, agent_name: str) -> None:
        """Remove override for an agent."""
        if agent_name in self.overrides:
            del self.overrides[agent_name]
            self._save_overrides()
    
    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Get current status of an agent's model assignment."""
        agent = None
        for a in self.graph_data.get("agents", []):
            if a.get("name") == agent_name:
                agent = a
                break
        
        if not agent:
            return {}
        
        override = self.overrides.get(agent_name)
        return {
            "name": agent_name,
            "auto_tier": agent.get("model_tier"),
            "auto_provider": agent.get("model_provider"),
            "override": override,
        }
    
    def _save_overrides(self) -> None:
        """Save overrides to model-config.yaml."""
        config_path = self.graphbus_dir / "model-config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {"overrides": self.overrides}
        with open(config_path, "w") as f:
            yaml.dump(data, f)
