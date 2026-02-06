# Technical Architecture

This document describes the technical architecture of the OpenClaw Configuration UI.

## System Overview

The OpenClaw Configuration UI is a monolithic web application that provides a user-friendly interface for configuring and deploying OpenClaw AI assistants.

### Technology Stack

**Frontend:**
- Next.js 14 (React framework)
- TypeScript (type safety)
- Tailwind CSS (styling)
- Axios (HTTP client)

**Backend:**
- Python 3.8+
- FastAPI (web framework)
- Uvicorn (ASGI server)
- Pydantic (data validation)

**Infrastructure:**
- Pulumi (infrastructure as code)
- Docker (containerization)
- AWS (optional cloud deployment)

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                          Browser                                │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               Next.js Frontend (Port 3000)                │  │
│  │                                                           │  │
│  │  Components:                                              │  │
│  │  - Wizard.tsx (main component)                            │  │
│  │  - WelcomeStep, DeploymentStep, APIKeysStep, etc.        │  │
│  │                                                           │  │
│  │  State Management:                                        │  │
│  │  - React useState hooks                                   │  │
│  │  - Configuration object                                   │  │
│  │  - Deployment status                                      │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           │
                           │ HTTP/REST API (JSON)
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│              Python FastAPI Backend (Port 8000)                  │
│                                                                  │
│  Endpoints:                                                      │
│  - GET  /                          (health check)                │
│  - POST /api/validate-config       (validate configuration)      │
│  - POST /api/generate-config       (generate config files)       │
│  - POST /api/deploy                (trigger deployment)          │
│  - GET  /api/deployment/{id}/status (get deployment status)     │
│                                                                  │
│  Data Models (Pydantic):                                         │
│  - DeploymentType                                                │
│  - APIKeys                                                       │
│  - AgentConfig                                                   │
│  - ChannelConfig                                                 │
│  - OpenClawConfig                                                │
│                                                                  │
│  Business Logic:                                                 │
│  - Configuration validation                                      │
│  - OpenClaw config generation (openclaw.json)                    │
│  - Docker Compose generation                                     │
│  - Deployment orchestration                                      │
│  - Status tracking (in-memory)                                   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           │ Invokes
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│                    Pulumi Deployment Layer                       │
│                                                                  │
│  Deployment Strategies:                                          │
│  1. Docker Local                                                 │
│     - Pull OpenClaw image                                        │
│     - Create container with config                               │
│     - Expose port 18789                                          │
│                                                                  │
│  2. AWS ECS/Fargate                                              │
│     - Create VPC, subnet, security groups                        │
│     - Create ECS cluster                                         │
│     - Define task with OpenClaw container                        │
│     - Create and start service                                   │
│                                                                  │
│  3. Direct Install (instructions only)                           │
│     - Generate step-by-step guide                                │
│     - User executes manually                                     │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Configuration Flow

```
User Input → Frontend State → Validation → Backend API → Config Generation → Deployment
```

**Detailed Steps:**

1. **User Input Collection**
   - User interacts with wizard steps
   - Each step updates React state
   - State persists across steps

2. **Client-Side Validation**
   - Basic validation in TypeScript
   - UI feedback for invalid input
   - Prevents bad data from reaching backend

3. **Backend Validation**
   - POST to `/api/validate-config`
   - Pydantic model validation
   - Business logic validation
   - Returns errors/warnings

4. **Configuration Generation**
   - POST to `/api/generate-config`
   - Generate `openclaw.json`
   - Generate `docker-compose.yml` (if Docker)
   - Generate deployment instructions

5. **Deployment Execution**
   - POST to `/api/deploy`
   - Store configuration
   - Initialize deployment status
   - Trigger async deployment
   - Return deployment ID

6. **Status Monitoring**
   - GET `/api/deployment/{id}/status`
   - Poll every 2 seconds
   - Update UI with progress
   - Complete when status = "completed"

## Component Architecture

### Frontend Components

```
pages/
├── _app.tsx              # Next.js app wrapper
└── index.tsx             # Home page, renders Wizard

components/
└── Wizard.tsx            # Main wizard component
    ├── WelcomeStep       # Step 1: Introduction
    ├── DeploymentStep    # Step 2: Choose deployment type
    ├── APIKeysStep       # Step 3: Configure API keys
    ├── AgentsStep        # Step 4: Configure AI assistant
    ├── ChannelsStep      # Step 5: Select communication channels
    ├── ReviewStep        # Step 6: Review configuration
    └── DeployStep        # Step 7: Deployment progress

styles/
└── globals.css           # Global styles and wizard-specific classes
```

### Backend Structure

```
backend/
└── main.py
    ├── FastAPI app initialization
    ├── CORS middleware
    ├── Data models (Pydantic)
    ├── API endpoints
    ├── Configuration generators
    ├── Deployment orchestration
    └── Status tracking
```

### Deployment Structure

```
deployment/
├── __main__.py           # Pulumi program
├── Pulumi.yaml          # Pulumi config
└── requirements.txt     # Python dependencies
```

## API Specification

### Health Check

```
GET /
Response: 200 OK
{
  "status": "healthy",
  "service": "OpenClaw Configuration UI API",
  "version": "1.0.0"
}
```

### Validate Configuration

```
POST /api/validate-config
Request Body:
{
  "deployment": {
    "type": "docker",
    "platform": null
  },
  "api_keys": {
    "anthropic_key": "sk-ant-...",
    "openai_key": null,
    "local_model": null
  },
  "agents": [
    {
      "name": "Assistant",
      "model": "anthropic/claude-opus-4",
      "description": "",
      "skills": []
    }
  ],
  "channels": [
    {
      "type": "whatsapp",
      "enabled": true,
      "allowed_users": []
    }
  ],
  "user_email": "user@example.com"
}

Response: 200 OK
{
  "valid": true,
  "errors": [],
  "warnings": ["No agents configured. At least one agent is recommended"]
}
```

### Generate Configuration

```
POST /api/generate-config
Request Body: (same as validate-config)

Response: 200 OK
{
  "openclaw_config": {
    "env": {
      "ANTHROPIC_API_KEY": "sk-ant-..."
    },
    "agents": {
      "defaults": {
        "model": {
          "primary": "anthropic/claude-opus-4"
        }
      }
    },
    "channels": {
      "whatsapp": {
        "enabled": true,
        "allowFrom": []
      }
    }
  },
  "docker_compose": "version: '3.8'\nservices:\n  openclaw:\n    ...",
  "deployment_instructions": [
    "1. Save the docker-compose.yml file...",
    "2. Create ~/.openclaw directory...",
    ...
  ]
}
```

### Deploy

```
POST /api/deploy
Request Body: (same as validate-config)

Response: 200 OK
{
  "deployment_id": "20260206230742",
  "status": "started",
  "message": "Deployment initiated successfully"
}
```

### Get Deployment Status

```
GET /api/deployment/{deployment_id}/status

Response: 200 OK
{
  "status": "in_progress",
  "progress": 60,
  "message": "Setting up infrastructure",
  "started_at": "2026-02-06T23:07:42.000Z",
  "updated_at": "2026-02-06T23:08:12.000Z"
}

// When complete:
{
  "status": "completed",
  "progress": 100,
  "message": "Deployment complete",
  "started_at": "2026-02-06T23:07:42.000Z",
  "updated_at": "2026-02-06T23:09:32.000Z"
}
```

## State Management

### Frontend State

The wizard uses React's `useState` hook to manage configuration:

```typescript
interface ConfigData {
  deployment: {
    type: string;
    platform?: string;
  };
  apiKeys: {
    anthropic_key?: string;
    openai_key?: string;
    local_model?: string;
  };
  agents: Array<{
    name: string;
    model: string;
    description?: string;
    skills: string[];
  }>;
  channels: Array<{
    type: string;
    enabled: boolean;
    allowed_users: string[];
  }>;
  user_email?: string;
}
```

### Backend State

The backend uses in-memory dictionaries for state:

```python
configurations = {}  # {deployment_id: config}
deployment_status = {}  # {deployment_id: status}
```

**Note:** In production, this should be replaced with a persistent database (Redis, PostgreSQL, etc.).

## Security Considerations

### API Key Handling

- API keys are never logged
- Keys are transmitted over HTTPS only
- Keys are not stored persistently
- Keys are masked in UI (password input)
- Keys are only in memory during deployment

### CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production:** Restrict `allow_origins` to specific domains.

### Environment Variables

All sensitive configuration should use environment variables:

```bash
# Backend
ALLOWED_ORIGINS=https://yourdomain.com
DATABASE_URL=postgresql://...

# Frontend
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

## Deployment Strategies

### 1. Docker Local Deployment

**Process:**
1. Generate `docker-compose.yml`
2. Generate `openclaw.json` config
3. Pull OpenClaw image
4. Create and start container
5. Expose port 18789

**Pulumi Code:**
```python
openclaw_image = docker.RemoteImage(
    "openclaw-image",
    name="openclaw/openclaw:latest",
)

openclaw_container = docker.Container(
    "openclaw-container",
    image=openclaw_image.repo_digest,
    name="openclaw",
    ports=[docker.ContainerPortArgs(
        internal=18789,
        external=18789,
    )],
    restart="unless-stopped",
    envs=["ANTHROPIC_API_KEY=...", ...],
)
```

### 2. AWS ECS/Fargate Deployment

**Process:**
1. Create VPC and subnet
2. Create ECS cluster
3. Define task definition with OpenClaw container
4. Create ECS service with Fargate launch type
5. Configure networking and security groups

**Pulumi Code:**
```python
vpc = aws.ec2.Vpc("openclaw-vpc", cidr_block="10.0.0.0/16")
subnet = aws.ec2.Subnet("openclaw-subnet", vpc_id=vpc.id, cidr_block="10.0.1.0/24")
cluster = aws.ecs.Cluster("openclaw-cluster")

task_definition = aws.ecs.TaskDefinition(
    "openclaw-task",
    family="openclaw",
    cpu="256",
    memory="512",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    container_definitions=json.dumps([...])
)

service = aws.ecs.Service(
    "openclaw-service",
    cluster=cluster.arn,
    desired_count=1,
    launch_type="FARGATE",
    task_definition=task_definition.arn,
    network_configuration=...
)
```

### 3. Direct Installation

**Process:**
1. Generate step-by-step instructions
2. User installs Node.js
3. User installs OpenClaw: `npm install -g openclaw@latest`
4. User runs onboarding: `openclaw onboard --install-daemon`
5. User configures via CLI or config file

## Performance Considerations

### Frontend Optimization

- **Code Splitting**: Next.js automatically splits by page
- **Image Optimization**: Use Next.js Image component
- **CSS Optimization**: Tailwind CSS purges unused styles
- **Bundle Size**: Monitor with `next build --analyze`

### Backend Optimization

- **Async Operations**: Use FastAPI's async/await for I/O
- **Connection Pooling**: Reuse HTTP connections
- **Caching**: Cache deployment templates
- **Rate Limiting**: Implement rate limiting for API endpoints

### Deployment Optimization

- **Parallel Operations**: Pulumi runs operations in parallel when possible
- **Resource Reuse**: Reuse existing infrastructure when available
- **Incremental Updates**: Only update changed resources

## Monitoring & Logging

### Backend Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

### Deployment Logging

Pulumi automatically logs all infrastructure changes:
- Resources created
- Resources updated
- Resources deleted
- Errors and warnings

### Production Monitoring

Recommended tools:
- **Application Monitoring**: Sentry, Datadog
- **Infrastructure Monitoring**: CloudWatch, Prometheus
- **Logging**: ELK Stack, CloudWatch Logs
- **Alerting**: PagerDuty, Opsgenie

## Testing Strategy

### Frontend Testing

```bash
# Unit tests
npm test

# E2E tests
npm run test:e2e
```

### Backend Testing

```bash
# Unit tests
pytest backend/tests/

# Integration tests
pytest backend/tests/integration/

# API tests
pytest backend/tests/api/
```

### Deployment Testing

```bash
# Preview deployment
pulumi preview

# Test deployment
pulumi up --stack test

# Destroy test resources
pulumi destroy --stack test
```

## Scaling Considerations

### Horizontal Scaling

- **Frontend**: Deploy to CDN (Vercel, Netlify, CloudFront)
- **Backend**: Deploy multiple instances behind load balancer
- **Database**: Add when persistent state is needed

### Vertical Scaling

- **Frontend**: Increase Next.js memory limits
- **Backend**: Increase Uvicorn worker count
- **Database**: Upgrade instance size

## Future Enhancements

### Phase 2 Features

1. **Persistent Storage**
   - Database for configurations
   - User accounts and authentication
   - Deployment history

2. **Advanced Features**
   - Multi-agent configuration
   - Custom skill/plugin installer
   - Template library
   - Pre-configured use cases

3. **Monitoring Dashboard**
   - Real-time status
   - Usage analytics
   - Cost tracking
   - Performance metrics

4. **Enhanced Deployment**
   - Support for more cloud providers (GCP, Azure)
   - Kubernetes deployment
   - Auto-scaling configuration
   - High availability setup

## Conclusion

The OpenClaw Configuration UI is designed as a simple, monolithic application that prioritizes ease of use over complexity. The architecture supports the primary goal: enabling non-technical users to deploy OpenClaw assistants without requiring technical knowledge.

The modular design allows for future enhancements while maintaining simplicity in the initial implementation.
