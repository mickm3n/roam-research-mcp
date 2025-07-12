# Roam Research MCP Server

A Model Context Protocol (MCP) server that provides tools to interact with Roam Research API, enabling Claude Desktop to read from and write to your Roam Research graph.

## Features

- **Get Page Content**: Retrieve content from any page in your Roam Research graph
- **Get Page References**: Find all references to a specific page
- **Write to Page**: Add new blocks to existing pages
- **Write to Today**: Add content to today's daily page (auto-creates if needed)

## Installation

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Roam Research API token and graph access

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd roam-research-mcp
```

2. Install dependencies:
```bash
uv sync
```

3. Set up environment variables:
```bash
export ROAM_TOKEN="your_roam_research_api_token"
export ROAM_GRAPH_NAME="your_graph_name"
```

## Claude Desktop Integration

Add this configuration to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "roam-research": {
      "command": "uv",
      "args": ["run", "python", "/absolute/path/to/roam-research-mcp/src/roam_research_mcp/server.py"],
      "env": {
        "ROAM_TOKEN": "your_actual_roam_token",
        "ROAM_GRAPH_NAME": "your_graph_name"
      }
    }
  }
}
```

## Usage

Once configured with Claude Desktop, you can:

- Ask Claude to read content from your Roam pages
- Have Claude write notes and thoughts to your daily pages
- Query page references and connections
- Add structured content to specific pages

## Development

See [CLAUDE.md](./CLAUDE.md) for development guidelines and git commit conventions.

## API Requirements

- Valid Roam Research API token
- Graph name with API access enabled
- Network access to `api.roamresearch.com`

## License

MIT License