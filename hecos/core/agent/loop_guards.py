"""
hecos/core/agent/loop_guards.py
Backward-compatibility facade re-exporting guard, stagnation-breaker, vision,
and response-finalization helpers split into focused modules under `hecos.core.agent`.
"""
# ruff: noqa: F401

from hecos.core.agent.stagnation_breaker import (
    _DYNAMIC_TRACE_NOISE_RE,
    _LOOP_FAIL_MARKERS,
    _LOOP_SUCCESS_MARKERS,
    classify_tool_result_for_loop,
    build_iteration_stagnation_signature,
    LoopStagnationTracker,
)
from hecos.core.agent.hallucination_guards import (
    _IMAGE_GEN_INTENT_RE,
    _WEB_SEARCH_EXCLUSION_RE,
    _NETSEARCH_REQUEST_RE,
    _FILE_CLAIM_RE,
    _NEGATIVE_FILE_CLAIM_RE,
    _WRITE_EXECUTOR_ACTIONS,
    is_uninstalled_image_gen_request,
    emit_missing_image_gen_warning,
    are_netsearch_tools_enabled,
    detect_unexecuted_netsearch_request,
    get_netsearch_unexecuted_guard_message,
    extract_verified_files_from_results,
    are_executor_write_tools_enabled,
    is_executor_anti_hallucination_enabled,
    _has_nonexistent_file_uri,
    detect_unexecuted_file_claim,
    append_verified_file_links,
    evaluate_plain_text_guards,
)
from hecos.core.agent.response_finalizer import (
    _DOC_INTENT_RE,
    _NETSEARCH_SYNTHESIS_INTENT_RE,
    resolve_short_model_label,
    LoopWatchdog,
    process_initial_vision,
    eval_early_termination,
    finalize_response,
    sync_assistant_history,
)

__all__ = [
    "LoopWatchdog",
    "LoopStagnationTracker",
    "resolve_short_model_label",
    "process_initial_vision",
    "eval_early_termination",
    "finalize_response",
    "sync_assistant_history",
    "is_uninstalled_image_gen_request",
    "emit_missing_image_gen_warning",
    "are_netsearch_tools_enabled",
    "detect_unexecuted_netsearch_request",
    "get_netsearch_unexecuted_guard_message",
    "extract_verified_files_from_results",
    "are_executor_write_tools_enabled",
    "is_executor_anti_hallucination_enabled",
    "detect_unexecuted_file_claim",
    "append_verified_file_links",
    "evaluate_plain_text_guards",
    "classify_tool_result_for_loop",
    "build_iteration_stagnation_signature",
]
