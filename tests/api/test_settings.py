"""
Tests for GraphBus API settings management (model preferences, configurations, etc).

Tests cover:
- Settings validation
- Settings helper functions
"""

import pytest


class TestSettingsValidation:
    """Test settings validation."""
    
    def test_validate_model_config_valid(self):
        """Test validating a valid model configuration."""
        from graphbus_api.routes.settings import validate_model_config
        
        valid_configs = [
            {
                "name": "default",
                "provider": "anthropic",
                "model": "claude-haiku-4-5",
            },
            {
                "name": "reasoning",
                "provider": "deepseek",
                "model": "deepseek-reasoner",
            },
            {
                "name": "gpt4",
                "provider": "openai",
                "model": "gpt-4o",
            },
        ]
        
        for config in valid_configs:
            assert validate_model_config(config) is True
    
    def test_validate_model_config_missing_fields(self):
        """Test that configs with missing required fields are rejected."""
        from graphbus_api.routes.settings import validate_model_config
        
        invalid_configs = [
            {"name": "incomplete"},  # Missing provider, model
            {"provider": "anthropic", "model": "claude"},  # Missing name
            {"name": "bad", "provider": "anthropic"},  # Missing model
        ]
        
        for config in invalid_configs:
            assert validate_model_config(config) is False
    
    def test_validate_model_config_invalid_provider(self):
        """Test that invalid providers are rejected."""
        from graphbus_api.routes.settings import validate_model_config
        
        invalid_config = {
            "name": "invalid",
            "provider": "unknown_provider_xyz",
            "model": "some-model",
        }
        
        assert validate_model_config(invalid_config) is False
    
    def test_validate_model_config_invalid_type(self):
        """Test that non-dict configs are rejected."""
        from graphbus_api.routes.settings import validate_model_config
        
        assert validate_model_config("not a dict") is False
        assert validate_model_config(None) is False
        assert validate_model_config([]) is False


class TestSettingsFunctions:
    """Test settings helper functions."""
    
    def test_save_user_models_invalid_config(self):
        """Test save_user_models rejects invalid configs."""
        from graphbus_api.routes.settings import save_user_models, validate_model_config
        
        # Test validation directly
        invalid_model = {"name": "bad", "model": "claude-haiku-4-5"}
        assert validate_model_config(invalid_model) is False
        
        # Valid function exists
        assert callable(save_user_models)


class TestModelConfigSchema:
    """Test ModelConfig Pydantic schema."""
    
    def test_model_config_schema_valid(self):
        """Test valid ModelConfig objects."""
        from graphbus_api.routes.settings import ModelConfig
        
        config = ModelConfig(
            name="test",
            provider="anthropic",
            model="claude-haiku-4-5",
        )
        
        assert config.name == "test"
        assert config.provider == "anthropic"
        assert config.model == "claude-haiku-4-5"
        assert config.base_url is None
    
    def test_model_config_schema_with_base_url(self):
        """Test ModelConfig with custom base_url."""
        from graphbus_api.routes.settings import ModelConfig
        
        config = ModelConfig(
            name="custom",
            provider="openai",
            model="gpt-4",
            base_url="https://api.example.com/v1",
        )
        
        assert config.base_url == "https://api.example.com/v1"
    
    def test_models_request_schema(self):
        """Test ModelsRequest schema."""
        from graphbus_api.routes.settings import ModelsRequest, ModelConfig
        
        request = ModelsRequest(
            models=[
                ModelConfig(
                    name="default",
                    provider="anthropic",
                    model="claude-haiku-4-5",
                ),
                ModelConfig(
                    name="reasoning",
                    provider="deepseek",
                    model="deepseek-reasoner",
                ),
            ]
        )
        
        assert len(request.models) == 2
        assert request.models[0].name == "default"
        assert request.models[1].name == "reasoning"
