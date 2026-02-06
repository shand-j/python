"""
Basic tests for OpenClaw Config UI Backend API
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app

client = TestClient(app)


def test_health_check():
    """Test the root health check endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "OpenClaw Configuration UI API"
    assert "version" in data


def test_validate_config_valid():
    """Test configuration validation with valid config"""
    config = {
        "deployment": {
            "type": "docker"
        },
        "api_keys": {
            "anthropic_key": "sk-ant-test123"
        },
        "agents": [
            {
                "name": "Test Agent",
                "model": "anthropic/claude-opus-4",
                "skills": []
            }
        ],
        "channels": [
            {
                "type": "whatsapp",
                "enabled": True,
                "allowed_users": []
            }
        ]
    }
    
    response = client.post("/api/validate-config", json=config)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] == True
    assert len(data["errors"]) == 0


def test_validate_config_invalid_deployment():
    """Test configuration validation with invalid deployment type"""
    config = {
        "deployment": {
            "type": "invalid"
        },
        "api_keys": {
            "anthropic_key": "sk-ant-test123"
        },
        "agents": [],
        "channels": []
    }
    
    response = client.post("/api/validate-config", json=config)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] == False
    assert len(data["errors"]) > 0


def test_validate_config_no_api_keys():
    """Test configuration validation without API keys"""
    config = {
        "deployment": {
            "type": "docker"
        },
        "api_keys": {},
        "agents": [],
        "channels": []
    }
    
    response = client.post("/api/validate-config", json=config)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] == False
    assert any("AI provider" in error for error in data["errors"])


def test_generate_config():
    """Test configuration file generation"""
    config = {
        "deployment": {
            "type": "docker"
        },
        "api_keys": {
            "anthropic_key": "sk-ant-test123",
            "openai_key": "sk-test456"
        },
        "agents": [
            {
                "name": "Test Agent",
                "model": "anthropic/claude-opus-4",
                "description": "Test description",
                "skills": []
            }
        ],
        "channels": [
            {
                "type": "whatsapp",
                "enabled": True,
                "allowed_users": ["+1234567890"]
            }
        ]
    }
    
    response = client.post("/api/generate-config", json=config)
    assert response.status_code == 200
    data = response.json()
    
    # Check openclaw config structure
    assert "openclaw_config" in data
    assert "env" in data["openclaw_config"]
    assert "ANTHROPIC_API_KEY" in data["openclaw_config"]["env"]
    assert "agents" in data["openclaw_config"]
    assert "channels" in data["openclaw_config"]
    
    # Check docker compose for docker deployment
    assert "docker_compose" in data
    assert data["docker_compose"] is not None
    
    # Check deployment instructions
    assert "deployment_instructions" in data
    assert len(data["deployment_instructions"]) > 0


def test_deploy():
    """Test deployment initiation"""
    config = {
        "deployment": {
            "type": "docker"
        },
        "api_keys": {
            "anthropic_key": "sk-ant-test123"
        },
        "agents": [
            {
                "name": "Test Agent",
                "model": "anthropic/claude-opus-4",
                "skills": []
            }
        ],
        "channels": [
            {
                "type": "whatsapp",
                "enabled": True,
                "allowed_users": []
            }
        ]
    }
    
    response = client.post("/api/deploy", json=config)
    assert response.status_code == 200
    data = response.json()
    
    assert "deployment_id" in data
    assert "status" in data
    assert data["status"] == "started"
    
    # Check deployment status
    deployment_id = data["deployment_id"]
    status_response = client.get(f"/api/deployment/{deployment_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert "status" in status_data
    assert "progress" in status_data


def test_deployment_status_not_found():
    """Test getting status for non-existent deployment"""
    response = client.get("/api/deployment/invalid-id/status")
    assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
