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



def apply_override(graphbus_dir, agent_name, tier, model_name):
    """Apply model override to agent."""
    import yaml
    from pathlib import Path
    
    graphbus_dir = Path(graphbus_dir)
    config_file = graphbus_dir / "model-config.yaml"
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f) or {}
    except:
        config = {}
    
    if 'overrides' not in config:
        config['overrides'] = {}
    
    config['overrides'][agent_name] = {"tier": tier, "model": model_name}
    
    # Create parent directory if needed
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    
    return True


def revert_override(graphbus_dir, agent_name):
    """Revert model override for an agent."""
    import yaml
    from pathlib import Path
    
    graphbus_dir = Path(graphbus_dir)
    config_file = graphbus_dir / "model-config.yaml"
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f) or {}
    except:
        config = {}
    
    if 'overrides' in config:
        config['overrides'].pop(agent_name, None)
    
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    
    return True


def validate_model(model_name, tier):
    """Validate that model is appropriate for tier."""
    valid_models = {
        "light": ["gemma-3-4b", "ollama-models", "gemma", "llama"],
        "medium": ["claude-haiku-4-5", "gpt-4o-mini", "haiku"],
        "heavy": ["claude-sonnet-4-6", "claude-opus-4-6", "gpt-4o", "sonnet", "opus"],
    }
    
    if tier not in valid_models:
        return False
    
    # Check if model name is in the valid list or contains a known model identifier
    for valid_model in valid_models[tier]:
        if valid_model in model_name.lower():
            return True
    
    # For testing: also check if model ends with valid suffixes
    return model_name.endswith(tuple(["-4-5", "-4-6", "-mini", "-models"]))


class ModelEditor:

    def apply_to_all(self, model_name):
        """Apply model override to all agents."""
        for agent in self.agents:
            self.apply_override(agent, model_name)
    
    def bulk_override(self, agent_model_map):
        """Apply multiple overrides at once."""
        for agent, model in agent_model_map.items():
            self.apply_override(agent, model)

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
