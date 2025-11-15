"""
CLI Configuration utilities

Loads and saves CLI configuration from .graphbus.yaml
"""

import os
import copy
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class CLIConfig:
    """
    Manages CLI configuration from .graphbus.yaml files.

    Configuration is loaded in this order (last wins):
    1. System default config
    2. User home directory config (~/.graphbus.yaml)
    3. Current directory config (./.graphbus.yaml)
    """

    DEFAULT_CONFIG = {
        "build": {
            "output_dir": ".graphbus",
            "validate": True,
            "verbose": False
        },
        "run": {
            "mode": "standard",
            "interactive": False,
            "message_bus": True,
            "verbose": False
        },
        "inspect": {
            "format": "table"
        },
        "validate": {
            "strict": False,
            "check_types": False,
            "check_cycles": False
        }
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize CLI config.

        Args:
            config_file: Optional path to config file. If None, searches standard locations.
        """
        self.config: Dict[str, Any] = copy.deepcopy(self.DEFAULT_CONFIG)

        if config_file:
            # Load specific config file
            self.load_from_file(config_file)
        else:
            # Load from standard locations
            self.load_standard_configs()

    def load_standard_configs(self):
        """Load config from standard locations in order."""
        # User home directory config
        home_config = Path.home() / ".graphbus.yaml"
        if home_config.exists():
            self.load_from_file(str(home_config))

        # Current directory config
        local_config = Path.cwd() / ".graphbus.yaml"
        if local_config.exists():
            self.load_from_file(str(local_config))

    def load_from_file(self, config_file: str):
        """
        Load configuration from a YAML file.

        Args:
            config_file: Path to config file
        """
        try:
            with open(config_file, 'r') as f:
                loaded_config = yaml.safe_load(f) or {}
                self._merge_config(loaded_config)
        except Exception as e:
            # Fail silently - config is optional
            pass

    def _merge_config(self, new_config: Dict[str, Any]):
        """Recursively merge new config into existing config."""
        for key, value in new_config.items():
            if key in self.config and isinstance(self.config[key], dict) and isinstance(value, dict):
                # Recursively merge nested dicts
                self.config[key].update(value)
            else:
                self.config[key] = value

    def get(self, command: str, option: str, default: Any = None) -> Any:
        """
        Get a config value for a command.

        Args:
            command: Command name (e.g., 'build', 'run')
            option: Option name (e.g., 'verbose', 'output_dir')
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        if command in self.config:
            return self.config[command].get(option, default)
        return default

    def save(self, config_file: str):
        """
        Save current configuration to a file.

        Args:
            config_file: Path to save config to
        """
        with open(config_file, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self.config.copy()


def load_cli_config(config_file: Optional[str] = None) -> CLIConfig:
    """
    Load CLI configuration.

    Args:
        config_file: Optional path to config file

    Returns:
        CLIConfig instance
    """
    return CLIConfig(config_file)


def create_default_config(output_file: str = ".graphbus.yaml"):
    """
    Create a default configuration file.

    Args:
        output_file: Path to create config file at
    """
    config = CLIConfig()
    config.save(output_file)
