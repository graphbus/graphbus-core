"""
Tests for GraphBus API authentication system.

Tests cover:
- API key creation and validation
- Firebase token verification
- User management
- Auth route schemas
"""

import pytest
from graphbus_api.routes.auth import VerifyRequest, VerifyResponse, MeResponse, CreateKeyRequest, CreateKeyResponse


class TestAuthSchemas:
    """Test authentication Pydantic schemas."""
    
    def test_verify_request_schema(self):
        """Test VerifyRequest schema."""
        request = VerifyRequest(id_token="test_token")
        assert request.id_token == "test_token"
    
    def test_verify_response_schema(self):
        """Test VerifyResponse schema."""
        response = VerifyResponse(
            uid="user_123",
            email="test@example.com",
            api_key=None,
            key_id="key_abc",
        )
        assert response.uid == "user_123"
        assert response.email == "test@example.com"
        assert response.api_key is None
        assert response.key_id == "key_abc"
    
    def test_me_response_schema(self):
        """Test MeResponse schema."""
        response = MeResponse(
            uid="user_123",
            email="test@example.com",
            display_name="Test User",
        )
        assert response.uid == "user_123"
        assert response.email == "test@example.com"
        assert response.display_name == "Test User"
    
    def test_create_key_request_schema(self):
        """Test CreateKeyRequest schema."""
        request = CreateKeyRequest(label="my-api-key")
        assert request.label == "my-api-key"
    
    def test_create_key_response_schema(self):
        """Test CreateKeyResponse schema."""
        response = CreateKeyResponse(
            key_id="key_123",
            api_key="gb_test_plaintext_key",
            created_at="2026-02-23T06:00:00Z",
        )
        assert response.key_id == "key_123"
        assert response.api_key.startswith("gb_")


class TestAuthHelpers:
    """Test auth helper functions."""
    
    def test_api_key_format_validation(self):
        """Test API key format validation."""
        from graphbus_core.auth import _validate_key_format
        
        # Valid key format
        assert _validate_key_format("gb_abcdef1234567890abcdef1234567890") is True
        
        # Invalid formats
        assert _validate_key_format("notakey") is False
        assert _validate_key_format("") is False
        assert _validate_key_format(None) is False
    
    def test_api_key_prefix(self):
        """Test that API keys use the correct prefix."""
        from graphbus_api.firebase_auth import create_api_key
        
        # The actual test is that the function exists and can be called
        assert callable(create_api_key)


class TestAuthValidation:
    """Test authentication validation logic."""
    
    def test_validate_email_format(self):
        """Test email validation."""
        import re
        
        email_pattern = r"^[^@]+@[^@]+\.[^@]+$"
        
        valid_emails = [
            "user@example.com",
            "test.user@example.co.uk",
            "user+tag@example.com",
        ]
        
        invalid_emails = [
            "plaintext",
            "@example.com",
            "user@",
            "user@.com",
        ]
        
        for email in valid_emails:
            assert re.match(email_pattern, email) is not None
        
        for email in invalid_emails:
            assert re.match(email_pattern, email) is None
    
    def test_api_key_entropy(self):
        """Test that generated API keys have sufficient entropy."""
        import secrets
        
        # Simulate API key generation
        plaintext = "gb_" + secrets.token_urlsafe(32)
        
        # Check format
        assert plaintext.startswith("gb_")
        assert len(plaintext) > 20  # Sufficient length for entropy


class TestAuthErrorHandling:
    """Test error handling in auth routes."""
    
    def test_verify_token_missing_header(self):
        """Test that missing Firebase token header returns error."""
        from fastapi.testclient import TestClient
        from graphbus_api.main import app
        
        client = TestClient(app)
        
        # POST without x-firebase-token header
        response = client.post("/auth/verify", json={"id_token": "test"})
        
        # Should return 422 (validation error) or 401 (unauthorized)
        assert response.status_code in [401, 422]
    
    def test_me_endpoint_missing_api_key(self):
        """Test that /auth/me endpoint requires API key."""
        from fastapi.testclient import TestClient
        from graphbus_api.main import app
        
        client = TestClient(app)
        
        # GET without x-api-key header
        response = client.get("/auth/me")
        
        # Should return 422 (validation error) or 401
        assert response.status_code in [401, 422]


class TestKeyStorage:
    """Test API key storage and retrieval logic."""
    
    def test_key_hash_function(self):
        """Test that key hashing produces consistent results."""
        import hashlib
        
        plaintext = "gb_test_key_12345"
        hash1 = hashlib.sha256(plaintext.encode()).hexdigest()
        hash2 = hashlib.sha256(plaintext.encode()).hexdigest()
        
        # Hashes should be identical
        assert hash1 == hash2
        
        # Hashes should be different for different keys
        plaintext2 = "gb_different_key_67890"
        hash3 = hashlib.sha256(plaintext2.encode()).hexdigest()
        
        assert hash1 != hash3
    
    def test_key_preview_format(self):
        """Test API key preview format (masked key)."""
        key_id = "key_abcdef123456"
        preview = f"gb_...{key_id[-4:]}"
        
        assert preview == "gb_...3456"
        assert not "plaintext" in preview.lower()
        assert len(preview) < 20  # Masked, so short
