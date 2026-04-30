# 🛠️ 5. Developer Best Practices

When developing new plugins or extending Hecos, follow these guidelines:

1.  **Modularity**: Keep plugin logic isolated and use provided system APIs (e.g., `self.core.speak()`).
2.  **Validation**: Always use Pydantic to define new configuration schemas.
3.  **Security**: Never execute system commands directly; always use the `SubprocessAdapter`.
4.  **Logging**: Use `logger.debug()` and `logger.info()` to track your plugin's operations.
5.  **Documentation**: Always add a short technical description of your code to facilitate future maintenance.
