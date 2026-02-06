# OpenClaw Configuration UI - User Guide

This guide explains how to use the OpenClaw Configuration UI wizard to set up your AI assistant.

## Table of Contents

1. [Before You Begin](#before-you-begin)
2. [Starting the Wizard](#starting-the-wizard)
3. [Wizard Steps](#wizard-steps)
4. [After Deployment](#after-deployment)
5. [Troubleshooting](#troubleshooting)

## Before You Begin

### What You Need

- **API Keys**: Get an API key from one of these providers:
  - [Anthropic Claude](https://console.anthropic.com/) (Recommended)
  - [OpenAI](https://platform.openai.com/api-keys)
  
- **Email Address**: For deployment notifications and instructions

- **Communication Platform**: Choose at least one:
  - WhatsApp
  - Telegram
  - Slack
  - Discord

### Understanding Deployment Options

The wizard offers three ways to run OpenClaw:

1. **Docker (Recommended for beginners)**
   - Runs in a container on your computer
   - Easiest to set up and manage
   - Works on any operating system
   - Perfect if you've never deployed software before

2. **Cloud/Serverless (Recommended for always-on access)**
   - Runs in the cloud (Cloudflare, AWS, etc.)
   - No need to keep your computer on
   - Accessible from anywhere
   - Small monthly cost for hosting

3. **Direct Install (For advanced users)**
   - Installs directly on your system
   - More control and customization
   - Requires comfort with terminal/command line

## Starting the Wizard

1. Open a terminal/command prompt
2. Navigate to the openclaw-config-ui directory
3. Run the start script:
   - **Mac/Linux**: `./start.sh`
   - **Windows**: `start.bat`
4. Wait for both servers to start
5. Open your browser to `http://localhost:3000`

## Wizard Steps

### Step 1: Welcome

**What it does**: Introduces you to the setup process

**What you do**: 
- Read the introduction
- Click "Next" to continue

**Tips**:
- Take a moment to read what you'll be setting up
- Don't rush - the wizard will guide you through everything

---

### Step 2: Choose Deployment Type

**What it does**: Lets you choose where to run OpenClaw

**What you do**:
1. Read the description of each option
2. Select one:
   - **Docker**: Best for most users, easiest setup
   - **Cloud**: Best if you want 24/7 availability
   - **Direct**: Only if you're comfortable with technical setup
3. Click "Next"

**Recommendations**:
- **First time?** Choose Docker
- **Want it always available?** Choose Cloud
- **Comfortable with tech?** Any option works

**Example**: "I want to try OpenClaw on my laptop first, so I'll choose Docker."

---

### Step 3: API Keys Configuration

**What it does**: Connects your AI service provider

**What you do**:
1. Copy your API key from Anthropic or OpenAI
2. Paste it into the appropriate field
3. Click "Next"

**Getting Your API Key**:

**Anthropic Claude**:
1. Visit [console.anthropic.com](https://console.anthropic.com/)
2. Sign up or log in
3. Click "API Keys"
4. Click "Create Key"
5. Copy the key (looks like `sk-ant-api03-...`)

**OpenAI**:
1. Visit [platform.openai.com](https://platform.openai.com/)
2. Sign up or log in
3. Click your profile → "API Keys"
4. Click "Create new secret key"
5. Copy the key (looks like `sk-...`)

**Important**:
- Keep your API key secure - treat it like a password
- Never share your API key publicly
- You only need ONE provider (either Anthropic OR OpenAI)

**Tips**:
- Anthropic Claude is better for complex, long conversations
- OpenAI is faster and cheaper for simple tasks
- You can use local models (like Ollama) if you're advanced

---

### Step 4: Configure Your Assistant

**What it does**: Sets up your AI assistant's personality and capabilities

**What you do**:
1. Enter a name for your assistant
2. Choose an AI model
3. Optionally add a description
4. Click "Next"

**Choosing a Name**:
- Pick something friendly: "My Assistant", "Work Helper", "Dorothy's Helper"
- You can change this later
- Make it memorable and easy to reference

**Choosing a Model**:
- **Claude Opus**: Most capable, best for complex tasks, costs more
- **Claude Sonnet**: Balanced performance and cost (Recommended)
- **GPT-4 Turbo**: Fast and smart, good for most tasks
- **GPT-4**: Very reliable
- **GPT-3.5**: Fastest and cheapest, good for simple tasks

**Cost Comparison** (approximate per 1M tokens):
- Claude Opus: $15
- Claude Sonnet: $3
- GPT-4 Turbo: $10
- GPT-4: $30
- GPT-3.5: $0.50

**Example Configuration**:
```
Name: Work Assistant
Model: Claude Sonnet
Description: Helps me automate my daily work tasks and manage my calendar
```

---

### Step 5: Communication Channels

**What it does**: Selects how you'll chat with your assistant

**What you do**:
1. Check the boxes for channels you want to use
2. You can select multiple
3. Click "Next"

**Available Channels**:

**WhatsApp** 💬
- Most popular choice
- Works on phone and computer
- Easy to use
- Great for quick messages

**Telegram** ✈️
- Very feature-rich
- Excellent bot support
- Good for power users
- Free and open source

**Slack** 💼
- Perfect for work environments
- Team collaboration
- Integration with work tools
- Professional setting

**Discord** 🎮
- Great for communities
- Voice and text
- Good for teams
- Popular with tech users

**Recommendation**: Start with one channel (WhatsApp is easiest), you can add more later.

---

### Step 6: Review Configuration

**What it does**: Shows you everything you've configured

**What you do**:
1. Review all your settings
2. Make sure everything looks correct
3. Go back if you need to change anything
4. Click "Deploy Now" when ready

**What to Check**:
- ✅ Deployment type is what you want
- ✅ API key is entered (shows as ✓)
- ✅ Assistant name and model look right
- ✅ Communication channels are selected
- ✅ Everything matches your plan

**Example Review**:
```
Deployment: Docker
AI Provider: ✓ Anthropic Claude
Assistant: Work Helper (Claude Sonnet)
Channels: WhatsApp, Slack
```

---

### Step 7: Deployment

**What it does**: Deploys your OpenClaw instance

**What happens**:
1. Validates your configuration
2. Generates configuration files
3. Sets up infrastructure
4. Installs OpenClaw
5. Configures agents
6. Starts services

**What you see**:
- Progress bar showing % complete
- Status messages for each step
- Estimated time remaining

**Timeline**:
- Docker: 2-5 minutes
- Cloud: 5-10 minutes
- Direct: 3-7 minutes

**While You Wait**:
- Don't close the browser
- Don't close the terminal windows
- The page will update automatically
- Grab a coffee! ☕

**When Complete**:
- You'll see a success message 🎉
- Get your deployment ID (save this!)
- Receive next steps via email
- Get connection instructions

---

## After Deployment

### Connecting Your Communication Channel

**WhatsApp**:
1. Check your email for QR code/link
2. Open WhatsApp on your phone
3. Scan the QR code or open the link
4. Start chatting!

**Telegram**:
1. Check email for bot username
2. Open Telegram
3. Search for the bot
4. Click "Start"
5. Begin chatting!

**Slack**:
1. Check email for installation link
2. Click to add to your workspace
3. Authorize the bot
4. @ mention it in any channel

**Discord**:
1. Check email for bot invite link
2. Click to add to your server
3. Select which server
4. Set permissions
5. Start using in channels

### First Conversations

**Test Commands**:
```
"Hello! Can you introduce yourself?"
"What can you help me with?"
"Set a reminder for tomorrow at 2pm"
"Summarize this email: [paste email]"
"Create a to-do list for my project"
```

### Managing Your Assistant

**View Logs**: Check what your assistant has been doing
**Update Configuration**: Change settings anytime
**Add Channels**: Connect more communication platforms
**Create Workflows**: Set up automated tasks
**Monitor Usage**: Track API usage and costs

---

## Troubleshooting

### Deployment Failed

**Problem**: Deployment stops with an error

**Solutions**:
1. Check your API key is valid
2. Verify you have internet connection
3. For Docker: Make sure Docker is running
4. Try deploying again
5. Check deployment logs for specific error

---

### Can't Connect to Assistant

**Problem**: Assistant doesn't respond in your chat app

**Solutions**:
1. Check deployment completed successfully
2. Verify channel is configured in Step 5
3. Wait a few minutes for channels to activate
4. Try sending "hello" to test connection
5. Check email for specific connection instructions

---

### API Key Not Working

**Problem**: Error about invalid API key

**Solutions**:
1. Copy the key again (don't type it)
2. Make sure no extra spaces
3. Verify key is active in provider console
4. Check you have credits/billing set up
5. Try creating a new API key

---

### Wizard Won't Load

**Problem**: Can't access http://localhost:3000

**Solutions**:
1. Check both backend and frontend are running
2. Look for errors in terminal windows
3. Try http://127.0.0.1:3000 instead
4. Make sure port 3000 isn't used by another app
5. Restart both servers

---

### Slow Deployment

**Problem**: Deployment taking longer than expected

**Solutions**:
1. Check internet connection
2. Wait - some steps take time
3. Don't close browser or terminals
4. Check if Docker is downloading images (first time)
5. Be patient - it can take 10-15 minutes sometimes

---

## Tips for Success

### For First-Time Users (Like Dorothy!)

1. **Read Each Step**: Don't skip the explanations
2. **Copy-Paste**: Don't manually type API keys or codes
3. **One Thing at a Time**: Complete one step before moving to next
4. **Save Your Keys**: Keep API keys and deployment ID safe
5. **Start Simple**: Use one channel first, add more later
6. **Ask Questions**: No question is too basic

### Best Practices

- **Test First**: Try with simple commands before complex workflows
- **Start Small**: Configure one agent before adding multiple
- **Monitor Costs**: Check API usage regularly
- **Keep Updated**: Note your deployment ID for updates
- **Secure Keys**: Never share API keys or deployment credentials

### Common Mistakes to Avoid

❌ Closing browser during deployment
❌ Using multiple API keys from same provider
❌ Not saving deployment ID
❌ Selecting too many channels at once
❌ Rushing through without reading

✅ Let deployment complete fully
✅ Use one API key per provider
✅ Save all IDs and credentials
✅ Start with one or two channels
✅ Take time to understand each step

---

## Getting More Help

- **Documentation**: Check the [README](README.md)
- **Quick Start**: See [QUICKSTART.md](QUICKSTART.md)
- **OpenClaw Docs**: [docs.openclaw.ai](https://docs.openclaw.ai/)
- **Issues**: Report problems on GitHub
- **Community**: Join OpenClaw community forums

---

## Appendix: Dorothy's Story

**Dorothy, 64, Operations Manager**

*"I wanted to automate my work so I could retire early. I'd never used anything technical beyond Word and Outlook - even Excel formulas confused me! But this wizard made it so simple. It explained everything in plain English, no confusing tech terms.*

*I followed the steps one by one, took my time, and in about 15 minutes I had my own AI assistant. Now it helps me manage my schedule, draft emails, create reports, and track projects. I've automated about 60% of my repetitive tasks.*

*If I can do it, anyone can. Just take your time, read each step, and don't be afraid to ask for help if you need it."*

---

**You're ready to deploy your AI assistant! Good luck! 🚀**
