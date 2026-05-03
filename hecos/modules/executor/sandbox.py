import os
import sys
import ast
import subprocess

try:
    from app.config import ConfigManager
except ImportError:
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    def FakeConfigManager(): return DummyConfigMgr()
    ConfigManager = FakeConfigManager

# ── AST Security Analyzer ───────────────────────────────────────────────────────
FORBIDDEN_IMPORTS = {
    'os', 'sys', 'subprocess', 'shutil', 'socket', 'pathlib',
    'pty', 'tempfile', 'requests', 'urllib', 'ftplib', 'ctypes', 'winreg'
}
FORBIDDEN_CALLS = {'eval', 'exec', 'compile', 'open'}

class SecurityAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.errors = []

    def visit_Import(self, node):
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module in FORBIDDEN_IMPORTS:
                self.errors.append(f"Forbidden import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in FORBIDDEN_IMPORTS:
                self.errors.append(f"Forbidden import from: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.errors.append(f"Forbidden function: {node.func.id}")
        self.generic_visit(node)


def run_python_code_tool(code: str, workspace_dir: str, tag: str) -> str:
    """
    Executes a block of Python code safely after strict Static Analysis (AST).
    Use for math, data manipulation, and algorithm building.
    :param code: The Python script to execute.
    """
    try:
        tree = ast.parse(code)
    except Exception as e:
        return f"Parsing Error: {e}"

    analyzer = SecurityAnalyzer()
    analyzer.visit(tree)
    if analyzer.errors:
        return f"SECURITY VIOLATION: {', '.join(analyzer.errors)}"

    script_path = os.path.join(workspace_dir, "ai_last_script.py")
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception as e:
        return f"I/O Error: {e}"

    cfg = ConfigManager()
    try:
        timeout = int(cfg.get_plugin_config(tag, "timeout_seconds", 10))
    except (ValueError, TypeError):
        timeout = 10

    try:
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            cwd=workspace_dir
        )
        output, _ = process.communicate(timeout=timeout)
        return output[-2000:] if len(output or "") > 2000 else (output or "")
    except subprocess.TimeoutExpired:
        process.kill()
        return f"Timeout Error: Execution expired after {timeout}s."
    except Exception as e:
        return f"Internal Error: {e}"
