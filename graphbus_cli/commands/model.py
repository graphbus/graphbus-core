"""
graphbus model — Configure agent model assignments and routing.
"""

import click
from pathlib import Path
import yaml
import json


@click.group()
@click.pass_context
def model(ctx):
    """Configure agent model assignments and routing.
    
    Override the auto-detected model tiers to customize which LLM
    handles each agent.
    
    Examples:
      graphbus model set APIAgent medium claude-haiku-4-5
      graphbus model set DataProcessor light gemma-3-4b
      graphbus model list
      graphbus model reset
    """
    ctx.ensure_object(dict)


@model.command()
@click.argument("agent_name")
@click.argument("tier", type=click.Choice(["light", "medium", "heavy"]))
@click.argument("model")
@click.option("--graphbus-dir", default=".graphbus", help="Path to .graphbus/")
def set(agent_name, tier, model, graphbus_dir):
    """Assign a specific model to an agent.
    
    Args:
        agent_name: Name of the agent (e.g., APIAgent)
        tier: Model tier (light|medium|heavy) — mainly for reference
        model: Model ID (e.g., claude-haiku-4-5, gemma-3-4b)
    
    Example:
        graphbus model set APIAgent medium claude-haiku-4-5
        graphbus model set DataProcessor light gemma-3-4b
    """
    graphbus_path = Path(graphbus_dir)
    config_path = graphbus_path / "model-config.yaml"
    
    # Load existing config or create new
    if config_path.exists():
        config = yaml.safe_load(config_path.read_text()) or {}
    else:
        config = {}
    
    if "overrides" not in config:
        config["overrides"] = {}
    
    config["overrides"][agent_name] = {
        "tier": tier,
        "model": model,
    }
    
    graphbus_path.mkdir(exist_ok=True)
    config_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))
    click.echo(f"✓ Set {agent_name} to {model} ({tier})")


@model.command()
@click.option("--graphbus-dir", default=".graphbus", help="Path to .graphbus/")
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
def list(graphbus_dir, format):
    """List all agent model assignments.
    
    Shows auto-detected tiers and any custom overrides.
    
    Example:
        graphbus model list
        graphbus model list --format json
    """
    graphbus_path = Path(graphbus_dir)
    graph_path = graphbus_path / "graph.yaml"
    config_path = graphbus_path / "model-config.yaml"
    
    if not graph_path.exists():
        click.echo("Error: .graphbus/graph.yaml not found. Run 'graphbus ingest' first.")
        return
    
    graph = yaml.safe_load(graph_path.read_text())
    overrides = {}
    
    if config_path.exists():
        config = yaml.safe_load(config_path.read_text()) or {}
        overrides = config.get("overrides", {})
    
    agents = graph.get("agents", [])
    
    if format == "json":
        result = []
        for agent in agents:
            name = agent["name"]
            override = overrides.get(name)
            if override:
                result.append({
                    "name": name,
                    "auto_tier": agent["model_tier"],
                    "auto_provider": agent["model_provider"],
                    "override_tier": override["tier"],
                    "override_model": override["model"],
                    "status": "overridden",
                })
            else:
                result.append({
                    "name": name,
                    "tier": agent["model_tier"],
                    "provider": agent["model_provider"],
                    "model": _get_model_for_tier(agent["model_tier"], agent["model_provider"]),
                    "status": "auto",
                })
        click.echo(json.dumps(result, indent=2))
    else:
        # Table format
        click.echo(f"\n{'Agent':<25} {'Auto':<20} {'Override':<30} {'Status':<10}")
        click.echo("-" * 85)
        
        for agent in agents:
            name = agent["name"]
            auto = f"{agent['model_tier']} ({agent['model_provider']})"
            override = overrides.get(name)
            
            if override:
                override_str = f"{override['tier']} ({override['model']})"
                status = "overridden"
            else:
                override_str = "—"
                status = "auto"
            
            click.echo(f"{name:<25} {auto:<20} {override_str:<30} {status:<10}")
        
        click.echo()


@model.command()
@click.argument("agent_name")
@click.option("--graphbus-dir", default=".graphbus", help="Path to .graphbus/")
def unset(agent_name, graphbus_dir):
    """Remove override for an agent (revert to auto-detected tier).
    
    Example:
        graphbus model unset APIAgent
    """
    graphbus_path = Path(graphbus_dir)
    config_path = graphbus_path / "model-config.yaml"
    
    if not config_path.exists():
        click.echo("No custom overrides found.")
        return
    
    config = yaml.safe_load(config_path.read_text()) or {}
    overrides = config.get("overrides", {})
    
    if agent_name not in overrides:
        click.echo(f"No override found for {agent_name}")
        return
    
    del overrides[agent_name]
    config["overrides"] = overrides
    
    if not overrides:
        config_path.unlink()
        click.echo(f"✓ Removed override for {agent_name} (reverted to auto-detect)")
    else:
        config_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))
        click.echo(f"✓ Removed override for {agent_name} (reverted to auto-detect)")


@model.command()
@click.option("--graphbus-dir", default=".graphbus", help="Path to .graphbus/")
def reset(graphbus_dir):
    """Reset all overrides and use auto-detected tiers.
    
    Example:
        graphbus model reset
    """
    graphbus_path = Path(graphbus_dir)
    config_path = graphbus_path / "model-config.yaml"
    
    if config_path.exists():
        config_path.unlink()
        click.echo("✓ All model overrides removed. Using auto-detected tiers.")
    else:
        click.echo("No custom overrides to reset.")


def _get_model_for_tier(tier: str, provider: str) -> str:
    """Get the default model for a tier/provider combo."""
    models = {
        ("light", "ollama"): "gemma-3-4b",
        ("medium", "anthropic"): "claude-haiku-4-5",
        ("heavy", "anthropic"): "claude-sonnet-4-6",
    }
    return models.get((tier, provider), "unknown")


def register(cli):
    """Register the model command with the CLI."""
    cli.add_command(model)
