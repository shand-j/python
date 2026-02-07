# OpenClaw Configuration UI

A user-friendly web interface for configuring and deploying OpenClaw AI assistants - designed for non-technical users!

## 🎯 Purpose

This tool empowers anyone, regardless of technical background, to deploy and configure OpenClaw agentic workflows. Whether you're an operations manager looking to automate your work or someone who's never touched code before, this wizard will guide you through every step.

## ✨ Features

- **Simple Wizard Interface**: Step-by-step guided setup
- **Multiple Deployment Options**: Docker, Cloud (Serverless), or Direct Install
- **AI Provider Integration**: Support for Anthropic Claude, OpenAI, and local models
- **Channel Configuration**: Connect via WhatsApp, Telegram, Slack, or Discord
- **Real-time Deployment Status**: Watch your deployment progress live
- **No Technical Knowledge Required**: Plain English, helpful explanations throughout

## 🏗️ Architecture

- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **Backend**: Python FastAPI for configuration and deployment
- **Infrastructure**: Pulumi for automated deployment
- **Monolithic Design**: Everything in one place for simplicity

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** (3.10+ recommended)
- **Node.js 18+**
- **Docker** (if using Docker deployment)
- API keys from Anthropic or OpenAI

### Installation

1. **Clone the repository**:
   ```bash
   cd python/openclaw-config-ui
   ```

2. **Run the setup script**:

   **On Mac/Linux**:
   ```bash
   ./setup.sh
   ```

   **On Windows**:
   ```bash
   setup.bat
   ```

3. **Start the backend** (in one terminal):
   ```bash
   cd backend
   source venv/bin/activate  # On Windows: venv\Scripts\activate.bat
   python main.py
   ```

4. **Start the frontend** (in another terminal):
   ```bash
   cd frontend
   npm run dev
   ```

5. **Open your browser**:
   ```
   http://localhost:3000
   ```

## 📖 Using the Wizard

**Visual Walkthrough**: See complete screenshots of all workflows in [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md)

The wizard walks you through 7 simple steps:

### Step 1: Welcome
- Introduction to what you'll be setting up
- No action required, just read and click "Next"

### Step 2: Choose Deployment Type
Choose where to run your AI assistant:

- **Docker (Recommended)**: Easiest option, works on any computer
- **Cloud (Serverless)**: Run in the cloud without managing servers
- **Direct Install**: Install directly on your system

### Step 3: API Keys
Enter your AI service API keys:

- **Anthropic Claude**: Get from [console.anthropic.com](https://console.anthropic.com/)
- **OpenAI**: Get from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Local Model**: Optional, for running AI locally with Ollama

### Step 4: Configure Your Assistant
- Give your assistant a name
- Choose which AI model to use
- Add an optional description

### Step 5: Communication Channels
Select how you want to chat with your assistant:
- WhatsApp
- Telegram
- Slack
- Discord

### Step 6: Review Configuration
- Review all your settings
- Make sure everything looks correct
- Click "Deploy Now" when ready

### Step 7: Deployment
- Watch the deployment progress in real-time
- Get your deployment ID and next steps
- Start using your AI assistant!

## 🎨 Design Philosophy

This tool follows the "Dorothy Test":

> Dorothy is a 64-year-old operations manager who wants to automate her work so she can retire in 6 months. She's only comfortable with Word and Outlook. If Dorothy can successfully deploy OpenClaw using this tool, we've succeeded.

Design principles:
- **No jargon**: Everything explained in plain English
- **Clear guidance**: Every step has helpful explanations
- **Visual feedback**: Progress indicators and status updates
- **Error prevention**: Validation and warnings before problems occur
- **Hand-holding**: Assume zero technical knowledge

## 🛠️ Development

### Project Structure

```
openclaw-config-ui/
├── backend/              # Python FastAPI backend
│   ├── main.py          # Main API server
│   └── requirements.txt  # Python dependencies
├── frontend/            # Next.js frontend
│   ├── pages/           # Next.js pages
│   ├── components/      # React components
│   │   └── Wizard.tsx   # Main wizard component
│   ├── styles/          # CSS styles
│   └── package.json     # Node.js dependencies
├── deployment/          # Pulumi deployment scripts
│   ├── __main__.py      # Pulumi infrastructure code
│   └── Pulumi.yaml      # Pulumi configuration
├── docs/                # Documentation
├── setup.sh             # Unix setup script
├── setup.bat            # Windows setup script
└── README.md            # This file
```

### Backend API Endpoints

- `GET /` - Health check
- `POST /api/validate-config` - Validate configuration
- `POST /api/generate-config` - Generate OpenClaw config files
- `POST /api/deploy` - Start deployment
- `GET /api/deployment/{id}/status` - Get deployment status

### Frontend Components

- **Wizard**: Main wizard container managing state and steps
- **WelcomeStep**: Introduction and overview
- **DeploymentStep**: Choose deployment type
- **APIKeysStep**: Configure AI providers
- **AgentsStep**: Configure AI assistant
- **ChannelsStep**: Select communication channels
- **ReviewStep**: Review configuration
- **DeployStep**: Deployment progress and completion

## 🔧 Configuration

### Backend Configuration

The backend runs on port 8000 by default. You can modify `backend/main.py` to change this.

### Frontend Configuration

The frontend runs on port 3000 by default. API calls are proxied to the backend via `next.config.js`.

## 🚢 Deployment Options

### Docker Deployment

The wizard generates a `docker-compose.yml` file that can be used to deploy OpenClaw locally or on any Docker-compatible system.

### Serverless Deployment

For cloud deployment, the wizard provides instructions for deploying to Cloudflare Workers using the Moltworker variant of OpenClaw.

### Direct Installation

For advanced users, the wizard provides step-by-step instructions for installing OpenClaw directly on a system.

## 🔐 Security Notes

- API keys are never stored persistently
- Configuration files are generated client-side when possible
- Deployment uses secure environment variables
- Follow OpenClaw security best practices

## 🤝 Contributing

Contributions welcome! When adding features:

1. Keep it simple - remember Dorothy!
2. Add clear explanations for everything
3. Test with non-technical users
4. Maintain the step-by-step wizard flow
5. Follow existing code style

## 📝 License

See individual project licenses in the main repository.

## 🆘 Troubleshooting

### Backend won't start
- Make sure Python 3.8+ is installed
- Activate the virtual environment
- Install requirements: `pip install -r backend/requirements.txt`

### Frontend won't start
- Make sure Node.js 18+ is installed
- Delete `node_modules` and `package-lock.json`, then run `npm install` again
- Check that port 3000 is not in use

### Deployment fails
- Verify your API keys are correct
- Check Docker is running (for Docker deployments)
- Review deployment logs for specific errors

### Can't access the UI
- Make sure both backend (port 8000) and frontend (port 3000) are running
- Try accessing directly: `http://localhost:3000`
- Check firewall settings

## 📚 Additional Resources

- [OpenClaw Official Documentation](https://docs.openclaw.ai/)
- [OpenClaw GitHub Repository](https://github.com/openclaw/openclaw)
- [Docker Documentation](https://docs.docker.com/)
- [Pulumi Documentation](https://www.pulumi.com/docs/)

## 💡 Future Enhancements

Planned features:
- One-click deployment to major cloud providers
- Pre-configured templates for common use cases
- Built-in testing and validation
- Multi-agent configuration
- Custom skill/plugin installer
- Video tutorials integrated in the UI

## 🎉 Success Stories

*Share your success stories! Did Dorothy retire successfully?*

---

Built with ❤️ to democratize AI automation and help everyone build agentic systems, regardless of technical background.
