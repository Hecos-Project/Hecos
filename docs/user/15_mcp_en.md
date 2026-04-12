# 🔌 Universal Tool Hub (MCP Bridge)
Transform Zentra into a multi-tool superpower by connecting external servers via the **Model Context Protocol**.

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
- **Auto-Discovery**: Zentra automatically scans connected servers and lists available tools in real-time.

## Using MCP Tools
Once a server is connected and showing as "connected" in the inventory:
1. The AI will automatically detect the new capabilities.
2. You can ask Zentra to perform actions like "Search on Brave" or "Check my GitHub issues".
3. Zentra will route the request to the external MCP server and return the results.
