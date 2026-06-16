"""
Hecos Flows — Execution Engine
================================
Reads flow YAML files, resolves step dependencies (topological sort),
renders Jinja2 templates for data-passing, executes actions, and emits
real-time SSE events to the WebUI for live log monitoring.

The engine also manages APScheduler jobs for cron/interval triggers.
"""

import time
import threading
import uuid
import datetime
import ctypes
from typing import Any, Callable, Dict, Generator, List, Optional

from hecos.core.logging import logger
class FlowLogger:
    def info(self, msg): logger.info("FLOWS", msg)
    def error(self, msg): logger.error("FLOWS", msg)
    def warning(self, msg): logger.debug("FLOWS", f"[WARN] {msg}")
    def debug(self, msg): logger.debug("FLOWS", msg)

log = FlowLogger()


# ── SSE Event Bus ──────────────────────────────────────────────────────────────

class FlowEventBus:
    """
    Lightweight pub/sub bus for streaming execution events to SSE clients.
    Each active run gets its own queue that the SSE endpoint consumes.
    """

    def __init__(self):
        self._queues: Dict[str, List] = {}
        self._lock = threading.Lock()

    def subscribe(self, run_id: str) -> List:
        with self._lock:
            q = []
            self._queues[run_id] = q
        return q

    def unsubscribe(self, run_id: str):
        with self._lock:
            self._queues.pop(run_id, None)

    def emit(self, run_id: str, event: Dict[str, Any]):
        with self._lock:
            q = self._queues.get(run_id)
            if q is not None:
                q.append(event)


# Singleton bus
_bus = FlowEventBus()

def get_event_bus() -> FlowEventBus:
    return _bus


# ── Abort / active-run tracking ────────────────────────────────────────────────

class FlowAbortException(Exception):
    """Raised inside a flow thread to immediately kill execution."""
    pass

_aborted_runs: set = set()  # run_ids that should be cancelled
_active_runs: Dict[str, str] = {}  # flow_id → run_id
_active_runs_lock = threading.Lock()
_run_threads: Dict[str, int] = {}  # run_id → thread native_id
_run_threads_lock = threading.Lock()
_run_children: Dict[str, set] = {}  # parent_run_id → {child_run_ids}
_run_children_lock = threading.Lock()


def abort_run(run_id: str):
    """Immediately kill a running flow and all registered children (cascade stop)."""
    _aborted_runs.add(run_id)

    # ── Cascade: abort all child sub-runs first ──────────────────────────────
    with _run_children_lock:
        children = set(_run_children.get(run_id, set()))  # snapshot
    for child_run_id in children:
        log.info(f"[Flows.Engine] ☠️ Cascade aborting child run '{child_run_id}' (parent={run_id})")
        abort_run(child_run_id)  # recursive for grandchildren

    # ── Kill the parent thread ───────────────────────────────────────────────
    with _run_threads_lock:
        thread_id = _run_threads.get(run_id)
    if thread_id is not None:
        _inject_exception(thread_id, FlowAbortException)
        log.info(f"[Flows.Engine] ☠️ Injected FlowAbortException into thread {thread_id} (run={run_id})")

    # Crucial: Unblock the thread if it's currently waiting for user input
    _cancel_pending_input(run_id)

def _inject_exception(thread_id: int, exc_type: type) -> bool:
    """Use ctypes to raise an exception in the target thread."""
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_ulong(thread_id),
        ctypes.py_object(exc_type)
    )
    if ret == 0:
        log.warning(f"[Flows.Engine] _inject_exception: thread {thread_id} not found.")
        return False
    elif ret > 1:
        # If > 1 threads were affected, undo
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), None)
        log.error(f"[Flows.Engine] _inject_exception: unexpected result {ret}, reverted.")
        return False
    return True

def is_run_aborted(run_id: str) -> bool:
    return run_id in _aborted_runs

def get_active_run(flow_id: str) -> Optional[str]:
    """Return the current run_id for flow_id, or None if not running."""
    with _active_runs_lock:
        return _active_runs.get(flow_id)

def _register_active_run(flow_id: str, run_id: str):
    with _active_runs_lock:
        _active_runs[flow_id] = run_id
    with _run_threads_lock:
        _run_threads[run_id] = threading.current_thread().ident

def _unregister_active_run(flow_id: str, run_id: str):
    with _active_runs_lock:
        if _active_runs.get(flow_id) == run_id:
            del _active_runs[flow_id]
    with _run_threads_lock:
        _run_threads.pop(run_id, None)
    _aborted_runs.discard(run_id)
    # Clean up child-run registry
    with _run_children_lock:
        _run_children.pop(run_id, None)
        # Also remove this run from any parent's child set
        for parent_children in _run_children.values():
            parent_children.discard(run_id)
    # Clean up any pending input gate if the run finished/aborted
    _cancel_pending_input(run_id)


def register_child_run(parent_run_id: str, child_run_id: str):
    """Link a child sub-run to its parent so abort_run() can cascade."""
    with _run_children_lock:
        if parent_run_id not in _run_children:
            _run_children[parent_run_id] = set()
        _run_children[parent_run_id].add(child_run_id)
    log.info(f"[Flows.Engine] 🔗 Registered child run '{child_run_id}' under parent '{parent_run_id}'")


def get_all_active_runs() -> Dict[str, str]:
    """Return a snapshot of all currently active {flow_id: run_id} pairs."""
    with _active_runs_lock:
        return dict(_active_runs)


# ── User Input Gate ────────────────────────────────────────────────────────────
# Maps run_id → {"event": threading.Event, "value": str|None, "flow_id": str}
_PENDING_INPUTS: Dict[str, Dict] = {}
_PENDING_INPUTS_LOCK = threading.Lock()


def register_pending_input(
    run_id: str,
    flow_id: str,
    intercept_mode: str = "auto",
    multi_run_priority: str = "first",
) -> threading.Event:
    """Register a run as waiting for user input. Returns the Event to wait on."""
    event = threading.Event()
    with _PENDING_INPUTS_LOCK:
        _PENDING_INPUTS[run_id] = {
            "event": event,
            "value": None,
            "flow_id": flow_id,
            "intercept_mode": intercept_mode,
            "multi_run_priority": multi_run_priority,
        }
    log.info(f"[Flows.Engine] ⏸️ Run '{run_id}' waiting for user input (mode={intercept_mode}).")
    return event


def deliver_user_input(run_id: str, text: str) -> bool:
    """Called by the API when the user submits a response. Unblocks the waiting thread."""
    with _PENDING_INPUTS_LOCK:
        entry = _PENDING_INPUTS.get(run_id)
    if entry is None:
        return False
    entry["value"] = text
    entry["event"].set()
    log.info(f"[Flows.Engine] ✅ User input delivered to run '{run_id}': {text[:60]}")
    return True


def get_pending_input_value(run_id: str) -> Optional[str]:
    """Retrieve the user's answer after the event has been set."""
    with _PENDING_INPUTS_LOCK:
        entry = _PENDING_INPUTS.get(run_id)
    return entry["value"] if entry else None


def _cancel_pending_input(run_id: str):
    """Unblock any waiting thread for this run (called on abort/finish)."""
    with _PENDING_INPUTS_LOCK:
        entry = _PENDING_INPUTS.pop(run_id, None)
    if entry:
        entry["event"].set()  # Unblock the waiting thread so it can exit cleanly


def get_all_pending_input_runs() -> list:
    """Returns list of {run_id, flow_id} for all runs currently waiting for input."""
    with _PENDING_INPUTS_LOCK:
        return [{"run_id": rid, "flow_id": v["flow_id"]} for rid, v in _PENDING_INPUTS.items()]


# ── Jinja2 template engine ─────────────────────────────────────────────────────

def _render(template_str: str, context: Dict[str, Any]) -> Any:
    """Render a Jinja2 template string against the flow context."""
    if not isinstance(template_str, str):
        return template_str
    if "{{" not in template_str and "{%" not in template_str:
        return template_str
    try:
        from jinja2 import Environment, Undefined
        env = Environment(undefined=Undefined)
        tmpl = env.from_string(template_str)
        return tmpl.render(**context)
    except Exception as e:
        log.warning(f"[Flows.Engine] Jinja2 render error: {e}")
        return template_str


def _render_params(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively render all string values in a params dict."""
    result = {}
    for k, v in params.items():
        if isinstance(v, str):
            result[k] = _render(v, context)
        elif isinstance(v, dict):
            result[k] = _render_params(v, context)
        elif isinstance(v, list):
            result[k] = [_render(i, context) if isinstance(i, str) else i for i in v]
        else:
            result[k] = v
    return result


# ── Condition evaluation ───────────────────────────────────────────────────────

def _eval_condition(condition: str, context: Dict[str, Any]) -> bool:
    """Evaluate a Jinja2 boolean condition against the context."""
    # Strip any accidental brackets the user might have typed
    clean_cond = condition.replace("{{", "").replace("}}", "")
    
    # Auto-coerce types in context to allow loose comparisons (e.g., string "10" > 5)
    eval_ctx = {}
    for k, v in context.items():
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ["true", "false"]:
                eval_ctx[k] = (v_lower == "true")
            else:
                try:
                    eval_ctx[k] = float(v) if "." in v else int(v)
                except ValueError:
                    eval_ctx[k] = v
        else:
            eval_ctx[k] = v
            
    rendered = _render(f"{{% if {clean_cond} %}}true{{% else %}}false{{% endif %}}", eval_ctx)
    return rendered.strip() == "true"


# ── Topological sort ───────────────────────────────────────────────────────────

def _topological_sort(steps: List[Dict]) -> List[Dict]:
    """
    Sort pipeline steps by their depends_on relationships.
    Steps with no dependencies run first; dependent steps run after all their parents.
    """
    step_map = {s["id"]: s for s in steps}
    visited = set()
    order = []

    def visit(step_id: str):
        if step_id in visited:
            return
        step = step_map.get(step_id)
        if step is None:
            return
        for dep in step.get("depends_on", []):
            dep_id = dep if isinstance(dep, str) else dep.get("node")
            if dep_id:
                visit(dep_id)
        visited.add(step_id)
        order.append(step)

    for step in steps:
        visit(step["id"])

    return order


# ── Logic node handlers ────────────────────────────────────────────────────────

def _execute_branch(branch: Any, step_id_prefix: str, context: Dict, run_id: str, emit: Callable) -> Any:
    if not branch:
        return None
    if isinstance(branch, list):
        res = None
        for i, b in enumerate(branch):
            if isinstance(b, dict):
                sub_step = {
                    "id": f"{step_id_prefix}_{i}",
                    "action": b.get("action", ""),
                    "params": b.get("params", {}),
                }
                res = _execute_step(sub_step, context, run_id, emit)
        return res
    elif isinstance(branch, dict):
        sub_step = {
            "id": step_id_prefix,
            "action": branch.get("action", ""),
            "params": branch.get("params", {}),
        }
        return _execute_step(sub_step, context, run_id, emit)
    return None


def _handle_if_else(step: Dict, context: Dict, run_id: str, emit: Callable) -> Any:
    condition = step["params"].get("condition", "false")
    result = _eval_condition(condition, context)

    branch_key = "true_branch" if result else "false_branch"
    
    if "_branch_results" not in context:
        context["_branch_results"] = {}
    context["_branch_results"][step["id"]] = branch_key

    branch = step["params"].get(branch_key)
    return _execute_branch(branch, f"{step['id']}_{branch_key}", context, run_id, emit)


def _handle_switch(step: Dict, context: Dict, run_id: str, emit: Callable) -> Any:
    expr = _render(step["params"].get("expression", ""), context)
    branches = step["params"].get("branches", {})
    branch = branches.get(expr) if isinstance(branches, dict) else None
    if not branch:
        branch = step["params"].get("default")

    return _execute_branch(branch, f"{step['id']}_branch_{expr}", context, run_id, emit)


def _handle_loop(step: Dict, context: Dict, run_id: str, emit: Callable) -> List:
    over_ref = _render(step["params"].get("over", ""), context)
    as_var   = step["params"].get("as_var", "item")
    body     = step["params"].get("body", {})

    # Resolve the iterable from context
    iterable = context.get(over_ref.strip("{{ }}"), [])
    results = []

    for i, item in enumerate(iterable):
        sub_ctx = dict(context)
        sub_ctx[as_var] = item
        res = _execute_branch(body, f"{step['id']}_iter_{i}", sub_ctx, run_id, emit)
        results.append(res)

    return results


def _handle_delay(step: Dict, context: Dict, **_) -> None:
    seconds = float(_render(str(step["params"].get("seconds", 1)), context))
    time.sleep(seconds)


def _handle_set_variable(step: Dict, context: Dict, **_) -> None:
    name  = step["params"].get("name", "")
    # Strip brackets in case the user used the variable picker for the variable name
    clean_name = name.replace("{{", "").replace("}}", "").strip()
    value = step["params"].get("value", "")
    context[clean_name] = _render(str(value), context)


def _handle_template(step: Dict, context: Dict, **_) -> str:
    template  = step["params"].get("template", "")
    output_as = step["params"].get("output_as", "template_result")
    result    = _render(template, context)
    context[output_as] = result
    return result


def _handle_and_gate(step: Dict, context: Dict, run_id: str, emit: Callable) -> Any:
    conditions = step["params"].get("conditions", [])
    all_pass = all(_eval_condition(_render(c, context), context) for c in conditions)
    branch_key = "on_success" if all_pass else "on_fail"
    branch = step["params"].get(branch_key)
    if branch:
        return _execute_branch(branch, f"{step['id']}_{branch_key}", context, run_id, emit)
    return all_pass


def _handle_or_gate(step: Dict, context: Dict, run_id: str, emit: Callable) -> Any:
    conditions = step["params"].get("conditions", [])
    any_pass = any(_eval_condition(_render(c, context), context) for c in conditions)
    branch_key = "on_success" if any_pass else "on_fail"
    branch = step["params"].get(branch_key)
    if branch:
        return _execute_branch(branch, f"{step['id']}_{branch_key}", context, run_id, emit)
    return any_pass


def _handle_http_request(step: Dict, context: Dict, **_) -> Any:
    import urllib.request, urllib.error, json
    method    = step["params"].get("method", "GET").upper()
    url       = _render(step["params"].get("url", ""), context)
    headers   = _render_params(step["params"].get("headers", {}), context)
    body      = step["params"].get("body")
    output_as = step["params"].get("output_as", "http_response")

    req = urllib.request.Request(url, method=method)
    for k, v in headers.items():
        req.add_header(k, str(v))

    if body and method in ("POST", "PUT", "PATCH"):
        body_str = json.dumps(body) if isinstance(body, dict) else str(body)
        req.data = body_str.encode("utf-8")
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            try:
                result = json.loads(raw)
            except Exception:
                result = raw
        context[output_as] = result
        return result
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} {e.reason} for {url}")


def _handle_abort(step: Dict, context: Dict, **_) -> None:
    reason = _render(step["params"].get("reason", "Aborted by LOGIC__abort node"), context)
    log.info(f"[Flows.Engine] 🛑 LOGIC__abort executed: {reason}")
    raise FlowAbortException(reason)


# ── Logic dispatch table ───────────────────────────────────────────────────────

def _handle_start(step: Dict, context: Dict, **_) -> Any:
    # Just a pass-through entry point
    return True

_LOGIC_HANDLERS = {
    "LOGIC__delay":       _handle_delay,
    "LOGIC__set_variable":_handle_set_variable,
    "LOGIC__template":    _handle_template,
    "LOGIC__if_else":     _handle_if_else,
    "LOGIC__switch":      _handle_switch,
    "LOGIC__loop":        _handle_loop,
    "LOGIC__and_gate":    _handle_and_gate,
    "LOGIC__or_gate":     _handle_or_gate,
    "LOGIC__http_request":_handle_http_request,
    "LOGIC__abort":       _handle_abort,
    "CONTROL__start":     _handle_start,
}


# ── Step executor ──────────────────────────────────────────────────────────────

def _execute_step(
    step: Dict[str, Any],
    context: Dict[str, Any],
    run_id: str,
    emit: Callable,
) -> Any:
    action    = step.get("action", "")
    params    = _render_params(step.get("params", {}), context)
    output_as = step.get("output_as")

    emit(run_id, {
        "type":   "step_start",
        "run_id": run_id,
        "step_id": step["id"],
        "action": action,
        "ts":     datetime.datetime.now().isoformat(),
    })

    if step.get("disabled", False):
        disable_mode = step.get("disable_mode", "skip")
        log.info(f"[Flows.Engine] ⏭️ Step '{step['id']}' bypassed (disabled). Mode: {disable_mode}")
        
        if step.get("action") == "CONTROL__start" and disable_mode == "stop":
            emit(run_id, {
                "type":   "step_error",
                "run_id": run_id,
                "step_id": step["id"],
                "action": action,
                "error":  "Start node is disabled! Please enable the start node to run the flow.",
                "ts":     datetime.datetime.now().isoformat(),
            })
        else:
            emit(run_id, {
                "type":   "step_skip",
                "run_id": run_id,
                "step_id": step["id"],
                "action": action,
                "ts":     datetime.datetime.now().isoformat(),
            })
        return "_BRANCH_STOPPED" if disable_mode == "stop" else None

    try:
        # Extract timeout configuration
        raw_params = step.get("params", {})
        timeout_val = params.get("timeout_seconds", raw_params.get("timeout_seconds", 0))
        timeout_seconds = int(timeout_val) if str(timeout_val).isdigit() else 0
        
        on_timeout_cont = params.get("on_timeout_continue", raw_params.get("on_timeout_continue", False))
        on_timeout_continue = str(on_timeout_cont).lower() in ["true", "1", "yes"]

        def _run_action():
            # Native logic handlers
            if action in _LOGIC_HANDLERS:
                handler = _LOGIC_HANDLERS[action]
                sig_args = handler.__code__.co_varnames[:handler.__code__.co_argcount]
                kwargs = {"step": step, "context": context}
                if "run_id" in sig_args: kwargs["run_id"] = run_id
                if "emit"   in sig_args: kwargs["emit"]   = emit
                return handler(**kwargs)
            else:
                from .registry import execute_action
                import time
                # Strip execution-level parameters before passing to the registry
                clean_params = {k: v for k, v in params.items() if k not in ["timeout_seconds", "on_timeout_continue"]}
                clean_params["_run_id"] = run_id
                clean_params["_timeout_seconds"] = timeout_seconds
                clean_params["_start_time"] = time.time()
                return execute_action(action, clean_params, context)

        if timeout_seconds > 0:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_run_action)
                try:
                    result = future.result(timeout=timeout_seconds)
                except concurrent.futures.TimeoutError:
                    log.warning(f"[Flows.Engine] Step '{step['id']}' timed out after {timeout_seconds}s.")
                    if on_timeout_continue:
                        log.info(f"[Flows.Engine] on_timeout_continue is True. Proceeding gracefully.")
                        result = "[Timeout]"
                    else:
                        raise TimeoutError(f"Step '{step['id']}' timed out after {timeout_seconds} seconds.")
        else:
            result = _run_action()

        if output_as and result is not None:
            context[output_as] = result

        emit(run_id, {
            "type":    "step_ok",
            "run_id":  run_id,
            "step_id": step["id"],
            "action":  action,
            "output":  str(result)[:512] if result is not None else None,
            "ts":      datetime.datetime.now().isoformat(),
        })
        return result

    except Exception as e:
        err_msg = str(e)
        log.error(f"[Flows.Engine] Step '{step['id']}' ({action}) failed: {err_msg}")
        emit(run_id, {
            "type":    "step_error",
            "run_id":  run_id,
            "step_id": step["id"],
            "action":  action,
            "error":   err_msg,
            "ts":      datetime.datetime.now().isoformat(),
        })
        raise


# ── Flow runner ────────────────────────────────────────────────────────────────

def run_flow(flow_data: Dict[str, Any], run_id: Optional[str] = None) -> str:
    """
    Execute a flow dictionary synchronously (blocking).
    Emits SSE events to the bus.

    Returns:
        run_id (str) — unique identifier for this execution run.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())[:8]

    flow_id   = flow_data.get("id", "unknown")
    pipeline  = flow_data.get("pipeline", [])
    variables = dict(flow_data.get("variables", {}))

    emit = _bus.emit

    _register_active_run(flow_id, run_id)

    emit(run_id, {
        "type":    "flow_start",
        "run_id":  run_id,
        "flow_id": flow_id,
        "ts":      datetime.datetime.now().isoformat(),
    })

    log.info(f"[Flows.Engine] ▶ Starting flow '{flow_id}' (run={run_id})")

    context = dict(variables)
    context["_run_id"]  = run_id
    context["_flow_id"] = flow_id
    context["_branch_results"] = {}

    try:
        # Pre-sort to put higher priority start nodes first
        pipeline.sort(key=lambda x: int(x.get("params", {}).get("priority", 0)) if x.get("action") == "CONTROL__start" else 999)
        sorted_steps = _topological_sort(pipeline)
        skipped_nodes = set()
        
        has_start_nodes = any(s.get("action") == "CONTROL__start" for s in sorted_steps)
        
        if not has_start_nodes and len(sorted_steps) > 0:
            emit(run_id, {
                "type":    "toast",
                "level":   "warning",
                "message": "Start node is missing. Floating nodes will be ignored."
            })

        for step in sorted_steps:
            # Cooperative abort check is now the FALLBACK;
            # primary kill path is ctypes exception injection in abort_run()
            if is_run_aborted(run_id):
                log.info(f"[Flows.Engine] ⛔ Flow '{flow_id}' aborted (run={run_id})")
                emit(run_id, {
                    "type":    "flow_aborted",
                    "run_id":  run_id,
                    "flow_id": flow_id,
                    "ts":      datetime.datetime.now().isoformat(),
                })
                return run_id

            step_id = step["id"]
            should_skip = False
            
            # Isolate and skip any node that has no dependencies AND is not a start node itself.
            # This enforces that ALL execution must originate from a CONTROL__start node.
            if not step.get("depends_on") and step.get("action") != "CONTROL__start":
                should_skip = True
            
            # Check dependencies to see if we should skip this step
            for dep in step.get("depends_on", []):
                if isinstance(dep, str):
                    if dep in skipped_nodes:
                        should_skip = True
                        break
                elif isinstance(dep, dict):
                    parent_id = dep.get("node")
                    req_branch = dep.get("branch")
                    if parent_id in skipped_nodes:
                        should_skip = True
                        break
                    
                    # Skip if parent took a different branch
                    actual_branch = context["_branch_results"].get(parent_id)
                    if actual_branch and req_branch and actual_branch != req_branch:
                        should_skip = True
                        break

            if should_skip:
                skipped_nodes.add(step_id)
                emit(run_id, {
                    "type":    "step_skipped",
                    "run_id":  run_id,
                    "step_id": step_id,
                    "action":  step.get("action", ""),
                    "ts":      datetime.datetime.now().isoformat(),
                })
                continue

            res = _execute_step(step, context, run_id, emit)
            
            if res == "_BRANCH_STOPPED":
                skipped_nodes.add(step_id)

        emit(run_id, {
            "type":    "flow_done",
            "run_id":  run_id,
            "flow_id": flow_id,
            "ts":      datetime.datetime.now().isoformat(),
        })
        log.info(f"[Flows.Engine] ✅ Flow '{flow_id}' completed (run={run_id})")

        # Update last_run metadata
        try:
            from .storage import update_flow_field
            update_flow_field(flow_id, "_meta.last_run", datetime.datetime.now().isoformat())
        except Exception:
            pass

    except FlowAbortException:
        log.info(f"[Flows.Engine] ☠️ Flow '{flow_id}' killed immediately (run={run_id})")
        emit(run_id, {
            "type":    "flow_aborted",
            "run_id":  run_id,
            "flow_id": flow_id,
            "ts":      datetime.datetime.now().isoformat(),
        })

    except Exception as e:
        emit(run_id, {
            "type":    "flow_error",
            "run_id":  run_id,
            "flow_id": flow_id,
            "error":   str(e),
            "ts":      datetime.datetime.now().isoformat(),
        })
        log.error(f"[Flows.Engine] ❌ Flow '{flow_id}' failed: {e}")

    finally:
        _unregister_active_run(flow_id, run_id)
        # Signal end-of-stream
        emit(run_id, {"type": "stream_end", "run_id": run_id})

    return run_id


def run_flow_async(flow_data: Dict[str, Any]) -> str:
    """Starts a flow in a background daemon thread. Returns the run_id immediately."""
    run_id = str(uuid.uuid4())[:8]
    t = threading.Thread(
        target=run_flow,
        args=(flow_data, run_id),
        daemon=True,
        name=f"HecosFlow-{run_id}",
    )
    t.start()
    return run_id


# ── APScheduler integration ────────────────────────────────────────────────────

_scheduler = None
_scheduler_lock = threading.Lock()


def _get_scheduler():
    global _scheduler
    with _scheduler_lock:
        if _scheduler is None:
            try:
                from apscheduler.schedulers.background import BackgroundScheduler
                
                # Fetch timezone from config if possible
                try:
                    from hecos.app.config import ConfigManager
                    cfg_mgr = ConfigManager()
                    tz = cfg_mgr.config.get("plugins", {}).get("FLOWS", {}).get("scheduler_timezone", "local")
                except:
                    tz = "local"
                    
                kwargs = {}
                if tz and tz != "local":
                    kwargs["timezone"] = tz
                    
                _scheduler = BackgroundScheduler(**kwargs)
                _scheduler.start()
                log.info("[Flows.Engine] APScheduler started.")
            except ImportError:
                log.warning("[Flows.Engine] APScheduler not installed. Cron/interval triggers disabled.")
        return _scheduler


def schedule_flow(flow_data: Dict[str, Any]) -> bool:
    """
    Register the flow's trigger with APScheduler.
    Call this when a flow is saved or enabled.
    Returns True on success.
    """
    scheduler = _get_scheduler()
    if scheduler is None:
        return False

    flow_id = flow_data.get("id", "")
    trigger  = flow_data.get("trigger", {})
    t_type   = trigger.get("type", "manual")

    # Remove existing job if any
    unschedule_flow(flow_id)

    if not flow_data.get("enabled", True):
        return False

    if t_type == "manual":
        return True  # No automatic scheduling needed

    def _job():
        from .storage import get_flow
        fresh = get_flow(flow_id)
        if fresh and fresh.get("enabled", True):
            run_flow_async(fresh)

    try:
        if t_type == "cron":
            expr = trigger.get("expression", "")
            parts = expr.strip().split()
            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts
                scheduler.add_job(
                    _job,
                    "cron",
                    id=f"flow_{flow_id}",
                    minute=minute, hour=hour, day=day,
                    month=month, day_of_week=day_of_week,
                    replace_existing=True,
                )
                log.info(f"[Flows.Engine] Scheduled '{flow_id}' as cron: {expr}")

        elif t_type == "interval":
            every = int(trigger.get("every", 60))
            unit  = trigger.get("unit", "seconds")
            kwargs = {unit: every}
            scheduler.add_job(
                _job, "interval", id=f"flow_{flow_id}",
                replace_existing=True, **kwargs
            )
            log.info(f"[Flows.Engine] Scheduled '{flow_id}' as interval: {every} {unit}")

        return True
    except Exception as e:
        log.error(f"[Flows.Engine] Could not schedule flow '{flow_id}': {e}")
        return False


def unschedule_flow(flow_id: str):
    """Remove a flow's scheduled job from APScheduler."""
    scheduler = _get_scheduler()
    if scheduler:
        try:
            scheduler.remove_job(f"flow_{flow_id}")
        except Exception:
            pass


def load_all_schedules():
    """Called at startup to re-register all enabled flows with their triggers."""
    try:
        from .storage import list_flows, get_flow
        for flow_summary in list_flows():
            if flow_summary.get("enabled", True) and flow_summary.get("trigger_type") != "manual":
                flow_data = get_flow(flow_summary["id"])
                if flow_data:
                    schedule_flow(flow_data)
        log.info("[Flows.Engine] All persisted schedules loaded.")
    except Exception as e:
        log.warning(f"[Flows.Engine] Could not load schedules: {e}")
