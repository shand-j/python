"""
OpenClaw Configuration UI - Backend API
FastAPI server for handling configuration and deployment
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
import json
import os
import asyncio
from datetime import datetime

app = FastAPI(title="OpenClaw Config UI API", version="1.0.0")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Data Models
class DeploymentType(BaseModel):
    type: str = Field(..., description="docker, serverless, or direct")
    platform: Optional[str] = Field(None, description="Platform for serverless (cloudflare, aws, gcp)")


class APIKeys(BaseModel):
    anthropic_key: Optional[str] = None
    openai_key: Optional[str] = None
    local_model: Optional[str] = None


class AgentConfig(BaseModel):
    name: str
    model: str
    description: Optional[str] = None
    skills: List[str] = []


class ChannelConfig(BaseModel):
    type: str = Field(..., description="whatsapp, telegram, slack, discord")
    enabled: bool = True
    allowed_users: List[str] = []


class OpenClawConfig(BaseModel):
    deployment: DeploymentType
    api_keys: APIKeys
    agents: List[AgentConfig]
    channels: List[ChannelConfig]
    user_email: Optional[str] = None


# In-memory storage (replace with database in production)
configurations = {}
deployment_status = {}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "OpenClaw Configuration UI API",
        "version": "1.0.0"
    }


@app.post("/api/validate-config")
async def validate_config(config: OpenClawConfig):
    """Validate OpenClaw configuration"""
    errors = []
    warnings = []

    # Validate deployment type
    if config.deployment.type not in ["docker", "serverless", "direct"]:
        errors.append("Invalid deployment type. Must be docker, serverless, or direct")

    # Validate API keys
    if not config.api_keys.anthropic_key and not config.api_keys.openai_key and not config.api_keys.local_model:
        errors.append("At least one AI provider must be configured (Anthropic, OpenAI, or local model)")

    # Validate agents
    if not config.agents or len(config.agents) == 0:
        warnings.append("No agents configured. At least one agent is recommended")

    # Validate channels
    if not config.channels or len(config.channels) == 0:
        warnings.append("No communication channels configured")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


@app.post("/api/generate-config")
async def generate_config(config: OpenClawConfig):
    """Generate OpenClaw configuration file"""
    
    # Build openclaw.json structure
    openclaw_config = {
        "env": {},
        "agents": {
            "defaults": {
                "model": {}
            }
        },
        "channels": {}
    }

    # Add API keys to env
    if config.api_keys.anthropic_key:
        openclaw_config["env"]["ANTHROPIC_API_KEY"] = config.api_keys.anthropic_key
    if config.api_keys.openai_key:
        openclaw_config["env"]["OPENAI_API_KEY"] = config.api_keys.openai_key

    # Configure default agent
    if config.agents:
        first_agent = config.agents[0]
        openclaw_config["agents"]["defaults"]["model"]["primary"] = first_agent.model

    # Configure channels
    for channel in config.channels:
        if channel.enabled:
            openclaw_config["channels"][channel.type] = {
                "enabled": True,
                "allowFrom": channel.allowed_users if channel.allowed_users else []
            }

    # Generate Docker Compose if needed
    docker_compose = None
    if config.deployment.type == "docker":
        docker_compose = generate_docker_compose()

    return {
        "openclaw_config": openclaw_config,
        "docker_compose": docker_compose,
        "deployment_instructions": get_deployment_instructions(config.deployment.type)
    }


@app.post("/api/deploy")
async def deploy_openclaw(config: OpenClawConfig):
    """Trigger deployment of OpenClaw"""
    config_id = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Store configuration
    configurations[config_id] = config.dict()
    
    # Initialize deployment status
    deployment_status[config_id] = {
        "status": "initializing",
        "progress": 0,
        "message": "Preparing deployment...",
        "started_at": datetime.now().isoformat()
    }

    # Start async deployment (simulated)
    asyncio.create_task(run_deployment(config_id, config))

    return {
        "deployment_id": config_id,
        "status": "started",
        "message": "Deployment initiated successfully"
    }


@app.get("/api/deployment/{deployment_id}/status")
async def get_deployment_status(deployment_id: str):
    """Get deployment status"""
    if deployment_id not in deployment_status:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return deployment_status[deployment_id]


async def run_deployment(deployment_id: str, config: OpenClawConfig):
    """Simulate deployment process"""
    stages = [
        ("Validating configuration", 10),
        ("Generating configuration files", 20),
        ("Setting up infrastructure", 40),
        ("Installing OpenClaw", 60),
        ("Configuring agents", 80),
        ("Starting services", 90),
        ("Deployment complete", 100)
    ]

    for message, progress in stages:
        deployment_status[deployment_id] = {
            "status": "in_progress" if progress < 100 else "completed",
            "progress": progress,
            "message": message,
            "started_at": deployment_status[deployment_id]["started_at"],
            "updated_at": datetime.now().isoformat()
        }
        await asyncio.sleep(2)  # Simulate work


def generate_docker_compose():
    """Generate Docker Compose configuration"""
    return """version: '3.8'
services:
  openclaw:
    image: openclaw/openclaw:latest
    container_name: openclaw
    restart: unless-stopped
    ports:
      - "18789:18789"  # Gateway
    volumes:
      - ~/.openclaw:/root/.openclaw
    environment:
      - NODE_ENV=production
"""


def get_deployment_instructions(deployment_type: str):
    """Get deployment instructions for the chosen type"""
    instructions = {
        "docker": [
            "1. Save the docker-compose.yml file to your server",
            "2. Create ~/.openclaw directory and add openclaw.json",
            "3. Run: docker compose up -d",
            "4. Check status: docker compose ps",
            "5. View logs: docker compose logs -f"
        ],
        "serverless": [
            "1. Install Cloudflare CLI: npm install -g wrangler",
            "2. Login: wrangler login",
            "3. Deploy: wrangler deploy",
            "4. Set secrets with your API keys",
            "5. Access your deployment URL"
        ],
        "direct": [
            "1. Install Node.js 18 or higher",
            "2. Install OpenClaw: npm install -g openclaw@latest",
            "3. Run onboarding: openclaw onboard --install-daemon",
            "4. Configure agents and channels",
            "5. Start: openclaw start"
        ]
    }
    return instructions.get(deployment_type, [])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
