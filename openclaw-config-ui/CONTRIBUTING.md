# Contributing to OpenClaw Configuration UI

Thank you for your interest in contributing to the OpenClaw Configuration UI! This project aims to make AI automation accessible to everyone, regardless of technical background.

## Core Principles

When contributing, please keep these principles in mind:

1. **Simplicity First**: This tool is designed for non-technical users. Every feature should be simple and intuitive.
2. **Dorothy Test**: If our test persona (Dorothy, 64-year-old operations manager) can't understand it, it needs to be simpler.
3. **Clear Language**: No jargon, no technical terms without explanation.
4. **Hand-Holding**: Assume zero technical knowledge from users.
5. **Minimal Changes**: Keep changes surgical and focused.

## Getting Started

### Development Environment Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/python.git
   cd python/openclaw-config-ui
   ```

2. **Run Setup**
   ```bash
   ./setup.sh  # or setup.bat on Windows
   ```

3. **Start Development Servers**
   
   Terminal 1 (Backend):
   ```bash
   cd backend
   source venv/bin/activate
   python main.py
   ```
   
   Terminal 2 (Frontend):
   ```bash
   cd frontend
   npm run dev
   ```

### Project Structure

```
openclaw-config-ui/
├── backend/              # Python FastAPI backend
│   ├── main.py          # Main API server
│   ├── test_api.py      # Backend tests
│   └── requirements.txt # Python dependencies
├── frontend/            # Next.js frontend
│   ├── pages/           # Next.js pages
│   ├── components/      # React components
│   └── styles/          # CSS styles
├── deployment/          # Pulumi deployment
├── docs/                # Documentation
├── setup.sh/bat         # Setup scripts
└── start.sh/bat         # Start scripts
```

## Types of Contributions

### 1. Bug Fixes

Found a bug? Great! Here's how to fix it:

1. Create an issue describing the bug
2. Fork the repository
3. Create a branch: `git checkout -b fix/bug-description`
4. Make your fix
5. Test thoroughly
6. Submit a pull request

**Requirements:**
- Clear description of what was broken
- Steps to reproduce the bug
- Explanation of your fix
- Test cases to prevent regression

### 2. New Features

Want to add a feature? Please follow this process:

1. **Discuss First**: Open an issue to discuss the feature
2. **Get Feedback**: Wait for maintainer feedback
3. **Design for Dorothy**: Ensure it's simple enough for non-technical users
4. **Implement**: Build the feature
5. **Document**: Add clear documentation
6. **Test**: Comprehensive testing
7. **Submit**: Create a pull request

**Requirements:**
- Feature must align with project goals
- Must maintain simplicity
- Must include documentation
- Must include tests

### 3. Documentation

Documentation improvements are always welcome!

**Types:**
- Fixing typos or unclear explanations
- Adding examples
- Improving getting started guides
- Creating video tutorials
- Translating to other languages

**Requirements:**
- Clear, simple language
- Accurate information
- Well-formatted

### 4. UI/UX Improvements

Making the UI better? Excellent!

**Focus areas:**
- Clearer explanations
- Better visual design
- Improved accessibility
- Mobile responsiveness
- Error messages and help text

**Requirements:**
- Must improve user experience
- Must maintain consistency
- Must be accessible
- Screenshots of changes

## Development Guidelines

### Code Style

**Python (Backend):**
- Follow PEP 8
- Use type hints
- Write docstrings
- Keep functions small and focused

**TypeScript (Frontend):**
- Use TypeScript, not JavaScript
- Use functional components
- Use hooks for state management
- Keep components small and focused

**CSS:**
- Use Tailwind CSS utilities
- Follow existing naming conventions
- Keep styles in globals.css

### Testing

**Backend Tests:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements-dev.txt
pytest test_api.py -v
```

**Frontend Tests:**
```bash
cd frontend
npm test
```

**Manual Testing:**
- Test on multiple browsers
- Test on different screen sizes
- Test with slow network
- Test error scenarios

### Commit Messages

Use clear, descriptive commit messages:

**Good:**
```
Add validation for API keys
Fix deployment progress bar
Update quickstart guide with screenshots
```

**Bad:**
```
fix bug
update stuff
changes
```

### Pull Request Process

1. **Update your fork:**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Create a branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make changes and commit:**
   ```bash
   git add .
   git commit -m "Clear description of changes"
   ```

4. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request:**
   - Go to GitHub
   - Click "New Pull Request"
   - Fill out the template
   - Reference any related issues

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] UI/UX improvement

## Dorothy Test
- [ ] Changes are simple enough for non-technical users
- [ ] All text is in plain English
- [ ] Added helpful explanations where needed

## Testing
- [ ] Tested on Chrome
- [ ] Tested on Firefox
- [ ] Tested on Safari
- [ ] Tested on mobile
- [ ] Backend tests pass
- [ ] Manual testing completed

## Screenshots
(If UI changes, add before/after screenshots)

## Related Issues
Closes #123
```

## Code Review Process

All pull requests will be reviewed for:

1. **Functionality**: Does it work as intended?
2. **Simplicity**: Is it simple enough for Dorothy?
3. **Code Quality**: Is the code clean and maintainable?
4. **Documentation**: Is it properly documented?
5. **Testing**: Does it have adequate tests?
6. **Consistency**: Does it fit the existing codebase?

## Reporting Issues

### Bug Reports

When reporting bugs, include:

1. **Description**: What's broken?
2. **Steps to Reproduce**: How can we see the bug?
3. **Expected Behavior**: What should happen?
4. **Actual Behavior**: What actually happens?
5. **Environment**: OS, browser, versions
6. **Screenshots**: If applicable

### Feature Requests

When requesting features, include:

1. **Problem**: What problem does this solve?
2. **Solution**: What's your proposed solution?
3. **Dorothy Test**: How would Dorothy use this?
4. **Alternatives**: What other solutions did you consider?
5. **Additional Context**: Any other relevant information

## Community Guidelines

### Be Respectful

- Be kind and respectful to all contributors
- Welcome newcomers and help them get started
- Provide constructive feedback
- Assume good intentions

### Be Patient

- Remember that this is a volunteer project
- Reviews may take time
- Not all features will be accepted
- Discussion is encouraged

### Be Helpful

- Answer questions from other contributors
- Share your knowledge
- Help test pull requests
- Improve documentation

## Getting Help

Need help contributing?

- **Questions**: Open a discussion on GitHub
- **Bugs**: Create an issue
- **Ideas**: Start a discussion
- **Documentation**: Check the docs/ folder

## Recognition

All contributors will be:
- Listed in CONTRIBUTORS.md
- Thanked in release notes
- Credited in the codebase

## Legal

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

## Special Thanks

Special thanks to Dorothy, our test persona, who reminds us every day that technology should be accessible to everyone, regardless of age or technical background.

If Dorothy can deploy an AI assistant with this tool, we're doing our job right. 🎉

---

**Questions?** Open an issue or start a discussion. We're here to help!

**Ready to contribute?** Pick an issue labeled "good first issue" and get started!

Thank you for making AI automation accessible to everyone! 🚀
