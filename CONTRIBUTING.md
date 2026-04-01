# Zentra Core - Contributing Guidelines (v0.9.9)

Thank you for contributing to Zentra Core! To ensure the project remains accessible and professional for international developers, please follow these language and coding standards.

## 🌍 Language Standard
- **Code:** All variable names, function names, classes, and internal documentation MUST be in **English**.
- **Configuration:** All keys in `config.json` and other configuration files MUST be in **English**.
- **Comments:** Code comments should be written in **English**.
- **Commits:** Git commit messages should be in **English**.

## 🏗️ Configuration Logic
- If you add or modify configuration keys, ensure they are descriptive and follow the camel_case or snake_case convention (snake_case preferred for Python).
- Always update `app/config.py` (default config) when introducing new parameters.

## 🧪 Internationalization (i18n)
- **Strings:** Never hardcode user-facing strings in Python or HTML. Always use the `translator.t()` function.
- **Locales:** Add your strings to both `core/i18n/locales/en.json` and `it.json`.

## 🛠️ PR (Pull Request) Rules
1. Ensure your code does not break the TUI (Terminal) or WebUI bridges.
2. Verify that local backends (Ollama/Kobold) still function correctly.
3. Update the `walkthrough.md` or `README.md` if you introduce major features.

*Zentra Core is built for a global future. Let's keep it clear and unified.*
