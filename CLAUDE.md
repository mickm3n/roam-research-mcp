# Claude Code Guidelines for Roam Research MCP

## Git Commit Rules

### Use Gitmoji for Commit Messages
Follow the [gitmoji](https://gitmoji.dev/) convention for consistent, semantic commit messages.

### Commit Separation by Purpose
Separate commits based on the type of change to maintain clear history:

#### 🎉 Initial Setup
- `:tada:` Initial commit and project setup
- `:wrench:` Configuration files (pyproject.toml, .env templates)
- `:see_no_evil:` .gitignore and environment setup

#### ✨ Features
- `:sparkles:` New features and functionality
- `:art:` Code structure improvements
- `:zap:` Performance improvements

#### 🐛 Bug Fixes
- `:bug:` Bug fixes
- `:ambulance:` Critical hotfixes
- `:fire:` Remove code or files

#### 📚 Documentation
- `:memo:` Documentation updates
- `:bulb:` Comments and code documentation

#### 🧹 Maintenance
- `:recycle:` Code refactoring
- `:truck:` Move or rename files
- `:heavy_minus_sign:` Remove dependencies

#### 🔧 Development
- `:white_check_mark:` Add or update tests
- `:construction_worker:` CI/CD updates
- `:green_heart:` Fix CI build

### Example Commit Structure
```
:sparkles: Add page content retrieval functionality

- Implement get_page_content method
- Add Datalog query support
- Handle API authentication

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Testing Commands
- Run tests: `python -m pytest` (when tests are added)
- Run server: `uv run python -m src.roam_research_mcp.server`
- Test API connection: Create test script as needed

## Development Notes
- Always use environment variables for sensitive data (ROAM_TOKEN, ROAM_GRAPH_NAME)
- Follow Python typing conventions
- Keep MCP server patterns consistent
- Document all public methods and classes