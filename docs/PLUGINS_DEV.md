# Zentra Core Plugin Development Guide (v0.9.9)

## 1. Overview
Plugins in Zentra Core are modular extensions located in the `plugins/` directory. Each plugin is a self-contained folder that follows a specific structure and interface.

---

## 2. Plugin Structure
A standard plugin directory should look like this:
```text
plugins/my_plugin/
├── __init__.py
├── main.py        # Core logic
└── config.json    # (Optional) Plugin-specific settings
```

The system automatically scans `plugins/` and registers the capabilities found.

---

## 3. Native Function Calling (Recommended)
Zentra Core uses **LiteLLM Tools** (OpenAI JSON Schema) to allow AI to call Python functions directly.

### Step 1: Define the `Tools` class in `main.py`
```python
class Tools:
    def greet_user(self, name: str):
        """
        Greets the user by name.
        :param name: The name of the person to greet.
        """
        return f"Hello, {name}! I am Zentra."

# Export tool instance
tools = Tools()
```

### Step 2: The system handles registration
The `plugin_loader.py` will automatically extract the function name, its arguments, and its docstring to build the JSON Schema that is sent to the LLM. No manual JSON writing is required if you follow standard docstring formats.

---

## 4. Legacy Pattern (Regex Tags)
If you prefer not to use native function calling, you can use the legacy `esegui` method. Zentra will look for tags like `[MY_PLUGIN: action]` in the AI response.

```python
def esegui(comando: str):
    """
    Standard entry point for legacy tag processing.
    """
    if "greet" in comando:
        return "Hello from legacy plugin!"
    return None
```

---

## 5. Plugin Guidelines
- **Return Type**: Functions should return strings or JSON-serializable objects. 
- **Dependency**: If your plugin requires external libraries, list them in `requirements.txt` at the root.
- **Security**: Never use `eval()` on AI input. Use the provided `executor` plugin for controlled system commands.
- **Config Access**: Plugins can access their own config through the `ConfigManager` or via a local `config.json`.
- **I18N Support**: New plugins should use the `core/i18n` system for any user-facing strings to support English, Italian, and Spanish.

---

## 6. Example: Simple Calculator Plugin
```python
# plugins/calculator/main.py

class Tools:
    def add(self, a: float, b: float):
        """Adds two numbers."""
        return str(a + b)

    def multiply(self, a: float, b: float):
        """Multiplies two numbers."""
        return str(a * b)

tools = Tools()
```
*When activated, the AI will automatically know it can call `tools__add` or `tools__multiply` when math is requested.*
