# Screenshot Capture Instructions

This directory contains screenshots of the OpenClaw Configuration UI wizard.

## How to Generate Screenshots

Since this is a web application, screenshots need to be captured by running the application:

### Prerequisites
1. Follow setup instructions in `../README.md`
2. Ensure both backend and frontend are running

### Steps to Capture Screenshots

1. **Start the Application**:
   ```bash
   cd openclaw-config-ui
   ./start.sh  # or start.bat on Windows
   ```

2. **Open Browser**:
   - Navigate to `http://localhost:3000`
   - Wait for the application to load

3. **Capture Each Step**:
   - **Step 1 - Welcome**: Capture initial welcome screen
   - **Step 2 - Deployment**: Select Docker option, capture
   - **Step 3 - API Keys**: Enter a test API key (dummy), capture
   - **Step 4 - Agents**: Fill in agent details, capture
   - **Step 5 - Channels**: Select channels, capture
   - **Step 6 - Review**: Capture review screen
   - **Step 7a - Deploying**: Capture progress at ~60%
   - **Step 7b - Complete**: Capture completion screen

### Screenshot Naming Convention

Screenshots should be named according to their step:
- `01-welcome.png` - Welcome screen
- `02-deployment.png` - Deployment type selection
- `03-api-keys.png` - API keys configuration
- `04-agents.png` - Agent configuration
- `05-channels.png` - Communication channels
- `06-review.png` - Review configuration
- `07-deploying.png` - Deployment in progress
- `07-complete.png` - Deployment complete

### Screenshot Specifications

- **Format**: PNG (lossless)
- **Resolution**: 1920x1080 (Full HD) or higher
- **Browser**: Chrome or Firefox (latest version)
- **Window Size**: Maximized or 1920x1080
- **Quality**: 100% (no compression)

## Current Screenshot Status

As of 2026-02-07, the application is fully functional and ready for screenshot capture. The mockups in `SCREENSHOTS.md` accurately represent what the actual UI looks like.

Until actual screenshots are captured, the workflow is documented with:
- Detailed descriptions in `SCREENSHOTS.md`
- ASCII art mockups in `VISUAL_GUIDE.md`
- Component code in `frontend/components/Wizard.tsx`

These provide complete visual documentation of all workflows.
