"""
Unit tests for CLI config utilities
"""

import pytest
import yaml
from pathlib import Path

from graphbus_cli.utils.config import CLIConfig, load_cli_config, create_default_config


class TestCLIConfig:
    """Test CLI configuration management"""

    def test_default_config_loaded(self):
        """Test that default config is loaded"""
        config = CLIConfig()

        assert config.get('build', 'output_dir') == '.graphbus'
        assert config.get('build', 'validate') is True
        assert config.get('run', 'mode') == 'standard'

    def test_load_from_file(self, tmp_path):
        """Test loading config from file"""
        config_file = tmp_path / "test_config.yaml"
        config_data = {
            'build': {
                'output_dir': 'custom_output',
                'verbose': True
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = CLIConfig(str(config_file))

        assert config.get('build', 'output_dir') == 'custom_output'
        assert config.get('build', 'verbose') is True
        # Default values still present
        assert config.get('build', 'validate') is True

    def test_config_merge(self, tmp_path):
        """Test that loaded config merges with defaults"""
        config_file = tmp_path / "test_config.yaml"
        config_data = {
            'build': {
                'verbose': True
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = CLIConfig(str(config_file))

        # New value from file
        assert config.get('build', 'verbose') is True
        # Default value still present
        assert config.get('build', 'output_dir') == '.graphbus'

    def test_get_with_default(self):
        """Test getting config with default value"""
        config = CLIConfig()

        # Existing value
        assert config.get('build', 'output_dir') == '.graphbus'

        # Non-existent value with default
        assert config.get('build', 'nonexistent', 'default') == 'default'

        # Non-existent command
        assert config.get('nonexistent_command', 'option', 'default') == 'default'

    def test_save_config(self, tmp_path):
        """Test saving config to file"""
        config = CLIConfig()
        output_file = tmp_path / "saved_config.yaml"

        config.save(str(output_file))

        # Verify file exists and is valid YAML
        assert output_file.exists()

        with open(output_file) as f:
            loaded_data = yaml.safe_load(f)

        assert 'build' in loaded_data
        assert 'run' in loaded_data
        assert loaded_data['build']['output_dir'] == '.graphbus'

    def test_to_dict(self):
        """Test converting config to dict"""
        config = CLIConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert 'build' in config_dict
        assert 'run' in config_dict
        assert config_dict['build']['output_dir'] == '.graphbus'

    def test_invalid_config_file_silent_fail(self):
        """Test that invalid config files don't crash"""
        config = CLIConfig('/nonexistent/path/to/config.yaml')

        # Should fall back to defaults
        assert config.get('build', 'output_dir') == '.graphbus'

    def test_malformed_yaml_silent_fail(self, tmp_path):
        """Test that malformed YAML doesn't crash"""
        config_file = tmp_path / "malformed.yaml"

        # Write invalid YAML
        with open(config_file, 'w') as f:
            f.write("{ invalid yaml content")

        config = CLIConfig(str(config_file))

        # Should fall back to defaults
        assert config.get('build', 'output_dir') == '.graphbus'

    def test_nested_config_values(self, tmp_path):
        """Test nested configuration values"""
        config_file = tmp_path / "nested_config.yaml"
        config_data = {
            'build': {
                'output_dir': 'custom',
                'options': {
                    'nested': True
                }
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = CLIConfig(str(config_file))

        assert config.get('build', 'output_dir') == 'custom'

    def test_all_default_sections_present(self):
        """Test that all default config sections are present"""
        config = CLIConfig()
        config_dict = config.to_dict()

        assert 'build' in config_dict
        assert 'run' in config_dict
        assert 'inspect' in config_dict
        assert 'validate' in config_dict

    def test_default_build_config(self):
        """Test default build configuration"""
        config = CLIConfig()

        assert config.get('build', 'output_dir') == '.graphbus'
        assert config.get('build', 'validate') is True
        assert config.get('build', 'verbose') is False

    def test_default_run_config(self):
        """Test default run configuration"""
        config = CLIConfig()

        assert config.get('run', 'mode') == 'standard'
        assert config.get('run', 'interactive') is False
        assert config.get('run', 'message_bus') is True
        assert config.get('run', 'verbose') is False

    def test_default_inspect_config(self):
        """Test default inspect configuration"""
        config = CLIConfig()

        assert config.get('inspect', 'format') == 'table'

    def test_default_validate_config(self):
        """Test default validate configuration"""
        config = CLIConfig()

        assert config.get('validate', 'strict') is False
        assert config.get('validate', 'check_types') is False
        assert config.get('validate', 'check_cycles') is False


class TestConfigHelpers:
    """Test helper functions"""

    def test_load_cli_config(self):
        """Test load_cli_config helper"""
        config = load_cli_config()

        assert isinstance(config, CLIConfig)
        assert config.get('build', 'output_dir') == '.graphbus'

    def test_load_cli_config_with_file(self, tmp_path):
        """Test load_cli_config with custom file"""
        config_file = tmp_path / "config.yaml"
        config_data = {'build': {'verbose': True}}

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = load_cli_config(str(config_file))

        assert config.get('build', 'verbose') is True

    def test_create_default_config(self, tmp_path):
        """Test create_default_config helper"""
        output_file = tmp_path / ".graphbus.yaml"

        create_default_config(str(output_file))

        assert output_file.exists()

        # Verify content
        with open(output_file) as f:
            data = yaml.safe_load(f)

        assert 'build' in data
        assert 'run' in data


class TestConfigPrecedence:
    """Test config file precedence and merging"""

    def test_config_file_overrides_defaults(self, tmp_path):
        """Test that config file values override defaults"""
        config_file = tmp_path / "override.yaml"
        config_data = {
            'build': {
                'output_dir': 'custom_dir',
                'verbose': True
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = CLIConfig(str(config_file))

        # Overridden values
        assert config.get('build', 'output_dir') == 'custom_dir'
        assert config.get('build', 'verbose') is True

        # Default values still present
        assert config.get('build', 'validate') is True
        assert config.get('run', 'mode') == 'standard'

    def test_partial_config_merge(self, tmp_path):
        """Test that partial config sections merge correctly"""
        config_file = tmp_path / "partial.yaml"
        config_data = {
            'build': {
                'verbose': True
                # output_dir and validate not specified
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = CLIConfig(str(config_file))

        # New value
        assert config.get('build', 'verbose') is True

        # Defaults still present
        assert config.get('build', 'output_dir') == '.graphbus'
        assert config.get('build', 'validate') is True

    def test_empty_config_file(self, tmp_path):
        """Test that empty config file doesn't break defaults"""
        config_file = tmp_path / "empty.yaml"

        with open(config_file, 'w') as f:
            f.write("")

        config = CLIConfig(str(config_file))

        # All defaults should be present
        assert config.get('build', 'output_dir') == '.graphbus'
        assert config.get('run', 'mode') == 'standard'

    def test_new_config_section(self, tmp_path):
        """Test that new config sections can be added"""
        config_file = tmp_path / "new_section.yaml"
        config_data = {
            'custom_command': {
                'option1': 'value1',
                'option2': True
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = CLIConfig(str(config_file))

        # New section accessible
        assert config.get('custom_command', 'option1') == 'value1'
        assert config.get('custom_command', 'option2') is True

        # Defaults still present
        assert config.get('build', 'output_dir') == '.graphbus'
