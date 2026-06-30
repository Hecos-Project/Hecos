# 🔌 Universal Tool Hub (MCP Bridge)
Transform Hecos into a multi-tool superpower by connecting external servers via the **Model Context Protocol**.

## What is MCP?
The Model Context Protocol (MCP) is a standard that allows AI agents to securely connect to external tools like:
- **Web Search**: Brave Search, Google Search.
- **Developer Tools**: GitHub, GitLab, Terminal.
- **Databases**: PostgreSQL, SQLite.
- **Knowledge**: Google Maps, Wikipedia.

## Setup & Configuration
Go to **Configuration -> MCP Bridge** to manage your servers.
- **Presets**: Choose from a list of popular servers for a quick setup.
- **Custom Servers**: Add your own by specifying the command (usually `npx`) and arguments.
- **Auto-Discovery**: Hecos automatically scans connected servers and lists available tools in real-time.

## 🔎 Multi-Registry Discovery
Hecos makes it easy to find new tools without leaving the application. Go to the **Discovery** tab in the MCP Bridge to search across multiple registries:
- **Smithery.ai**: Browse thousands of community-verified MCP servers.
- **MCPSkills**: Discover specialized agents and toolsets.
- **GitHub**: Directly install servers hosted on GitHub repositories.
- **Hugging Face**: Access AI-ready tools and models.

Simply click **"Install"** on any discovered tool, and Hecos will handle the environment setup and configuration automatically.

## Using MCP Tools
Once a server is connected and showing as "connected" in the inventory:
1. The AI will automatically detect the new capabilities.
2. You can ask Hecos to perform actions like "Search on Brave" or "Check my GitHub issues".
3. Hecos will route the request to the external MCP server and return the results.
