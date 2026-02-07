# Quick Start Guide - Get OpenClaw Running in 10 Minutes

This guide will have you deploying your own AI assistant in about 10 minutes, even if you've never done anything like this before!

## What You'll Need

1. A computer (Mac, Windows, or Linux)
2. An API key from either:
   - Anthropic (Claude AI) - [Get it here](https://console.anthropic.com/)
   - OpenAI (ChatGPT) - [Get it here](https://platform.openai.com/api-keys)
3. 10 minutes of your time ☕

## Step-by-Step Instructions

### 1. Install Prerequisites (5 minutes)

#### Install Python
- **Mac**: Already installed! Skip this step.
- **Windows**: Download from [python.org](https://www.python.org/downloads/) and run the installer
- **Linux**: Run `sudo apt-get install python3` (Ubuntu/Debian)

#### Install Node.js
- Download from [nodejs.org](https://nodejs.org/) and run the installer
- Choose the LTS (Long Term Support) version

#### Install Docker (Optional - only if using Docker deployment)
- Download from [docker.com](https://www.docker.com/products/docker-desktop/)
- Run the installer and start Docker

### 2. Get Your API Key (2 minutes)

**For Anthropic Claude (Recommended)**:
1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Sign up or log in
3. Click "API Keys" in the menu
4. Click "Create Key"
5. Copy your key (starts with `sk-ant-`)

**For OpenAI**:
1. Go to [platform.openai.com](https://platform.openai.com/)
2. Sign up or log in
3. Click your profile → "API Keys"
4. Click "Create new secret key"
5. Copy your key (starts with `sk-`)

💡 **Tip**: Save your key in a text file temporarily - you'll need it in a moment!

### 3. Run the Setup (2 minutes)

Open a terminal/command prompt:

**Mac/Linux**:
```bash
cd openclaw-config-ui
./setup.sh
```

**Windows**:
```cmd
cd openclaw-config-ui
setup.bat
```

The setup will install everything you need. Grab a coffee while it runs! ☕

### 4. Start the Application (1 minute)

You need to open TWO terminal windows:

**Terminal 1 - Start the Backend**:
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate.bat
python main.py
```

You should see: `Application startup complete`

**Terminal 2 - Start the Frontend**:
```bash
cd frontend
npm run dev
```

You should see: `ready - started server on 0.0.0.0:3000`

### 5. Open the Wizard (10 seconds)

Open your web browser and go to:
```
http://localhost:3000
```

You should see the OpenClaw Setup Wizard! 🎉

### 6. Follow the Wizard (5 minutes)

The wizard will guide you through everything. Here's what to expect:

1. **Welcome** - Just read and click "Next"
2. **Deployment** - Choose "Docker (Recommended)" and click "Next"
3. **API Keys** - Paste your API key from Step 2
4. **Assistant** - Give it a name like "My Helper" and pick a model
5. **Channels** - Check WhatsApp, Telegram, or whatever you want to use
6. **Review** - Make sure everything looks good
7. **Deploy** - Click "Deploy Now" and watch it work!

### 7. Start Chatting! 🎊

Once deployment completes:
1. Check your email for connection details
2. Open WhatsApp (or your chosen channel)
3. Add your new AI assistant
4. Start automating your work!

## Common Issues & Solutions

### "Python not found"
- Make sure you installed Python from Step 1
- On Windows, make sure you checked "Add Python to PATH" during installation
- Try `python3` instead of `python`

### "Node not found"
- Make sure you installed Node.js from Step 1
- Restart your terminal after installing
- Try `node --version` to verify it's installed

### "Port already in use"
- Something else is using port 3000 or 8000
- Close other applications and try again
- Or change the port in the configuration

### Setup script fails
- Make sure you have internet connection
- Try running the setup script again
- Check that you have write permissions in the folder

### Can't access http://localhost:3000
- Make sure both backend and frontend are running
- Check that you see "server started" messages in both terminals
- Try `http://127.0.0.1:3000` instead

## Next Steps

Once you have OpenClaw running:

1. **Customize Your Assistant**
   - Add more agents for different tasks
   - Configure specific skills and capabilities
   - Set up automation workflows

2. **Connect More Channels**
   - Add multiple communication methods
   - Set up team access
   - Configure notification preferences

3. **Explore Advanced Features**
   - Create custom workflows
   - Integrate with your tools
   - Build multi-agent systems

## Getting Help

- Check the [full README](README.md) for detailed documentation
- Visit [OpenClaw Documentation](https://docs.openclaw.ai/)
- Review [deployment guides](docs/)

## Success Tips for Non-Technical Users

**Dorothy's Advice** (our 64-year-old testing champion):

> "Don't be intimidated by all the technical terms! Just follow the steps one at a time. If you can use Word and Outlook, you can do this. The wizard explains everything in plain English. I automated half my job in an afternoon, and I'd never written a line of code in my life!"

### Remember:
- ✅ **Read each step carefully** - Don't rush
- ✅ **Copy and paste** - Don't try to type complex codes
- ✅ **Save your API key** - You'll need it!
- ✅ **Keep both terminals open** - You need backend AND frontend running
- ✅ **Ask for help** - There's no such thing as a stupid question

## You're Ready!

That's it! You now have everything you need to deploy your own AI assistant. Follow the steps above, take your time, and in 10 minutes you'll have your own personal AI helper.

Welcome to the future of automation! 🚀

---

**Questions or stuck?** Open an issue in the repository or reach out for help. We're here to make this work for everyone!
