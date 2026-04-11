# 🛠️ 5. Developer Best Practices

- **Logger over Print**: Always use `core.logging.logger`.
- **Sync/Async Safety**: Use provided UI locks.
- **Atomic Config**: Persistence via `config_manager.set(...)`.
- **Modularity**: Plugin isolation and extension usage.
