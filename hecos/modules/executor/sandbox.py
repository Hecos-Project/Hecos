import os
import sys
import ast
import subprocess

try:
    from app.config import ConfigManager
    from hecos.core.agent.traces import AgentTracer
except ImportError:
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    def FakeConfigManager(): return DummyConfigMgr()
    ConfigManager = FakeConfigManager
    class DummyTracer:
        @staticmethod
        def emit_action(t, c, o): print(f"[ACTION] {t}: {c}\n{o}")
    AgentTracer = DummyTracer()

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


def run_python_code_tool(code: str, workspace_dir: str, tag: str, projects_workspace_dir: str = "") -> str:
    """
    Executes a block of Python code safely after strict Static Analysis (AST).
    Stores the ephemeral runner script in workspace_dir (sandbox), while keeping
    projects_workspace_dir on sys.path and as cwd so workspace modules import cleanly.
    :param code: The Python script to execute.
    """
    cmd_preview = "Python Code Sandbox:\n" + code[:100] + ("..." if len(code) > 100 else "")
    
    try:
        tree = ast.parse(code)
    except Exception as e:
        err = f"Parsing Error: {e}"
        AgentTracer.emit_action(tag, cmd_preview, err)
        return err

    analyzer = SecurityAnalyzer()
    analyzer.visit(tree)
    if analyzer.errors:
        err = f"SECURITY VIOLATION: {', '.join(analyzer.errors)}"
        AgentTracer.emit_action(tag, cmd_preview, err)
        return err

    os.makedirs(workspace_dir, exist_ok=True)
    script_path = os.path.join(workspace_dir, "ai_last_script.py")
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception as e:
        err = f"I/O Error: {e}"
        AgentTracer.emit_action(tag, cmd_preview, err)
        return err

    cfg = ConfigManager()
    try:
        timeout = int(cfg.get_plugin_config(tag, "timeout_seconds", 10))
    except (ValueError, TypeError):
        timeout = 10

    try:
        # Ensure projects_workspace_dir is importable even under embeddable Python (_pth omits cwd/script dir)
        import_root = os.path.abspath(projects_workspace_dir or workspace_dir)
        script_abs = os.path.abspath(script_path)
        runner_code = (
            "import sys, runpy; "
            f"sys.path.insert(0, {import_root!r}); "
            f"sys.argv[0] = {script_abs!r}; "
            f"runpy.run_path({script_abs!r}, run_name='__main__')"
        )
        process = subprocess.Popen(
            [sys.executable, "-c", runner_code],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            cwd=import_root
        )
        output, _ = process.communicate(timeout=timeout)
        final_out = output[-2000:] if len(output or "") > 2000 else (output or "")
        AgentTracer.emit_action(tag, cmd_preview, final_out)
        return final_out
    except subprocess.TimeoutExpired:
        process.kill()
        err = f"Timeout Error: Execution expired after {timeout}s."
        AgentTracer.emit_action(tag, cmd_preview, err)
        return err
    except Exception as e:
        err = f"Internal Error: {e}"
        AgentTracer.emit_action(tag, cmd_preview, err)
        return err
