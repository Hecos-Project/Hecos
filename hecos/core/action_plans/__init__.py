"""
hecos/core/action_plans/__init__.py
Autonomous Core subsystem for shared Action Plans and Flow execution checkpoints.
"""

from hecos.core.action_plans.approval_gate import (
    await_plan_approval,
    cancel_pending_approval,
    has_pending_approval,
    submit_approval_decision,
)
from hecos.core.action_plans.config import (
    DEFAULT_ACTION_PLANS_CONFIG,
    get_action_plans_config,
    normalize_action_plans_config,
    save_action_plans_config,
)
from hecos.core.action_plans.flow_checkpoints import (
    RESUMABLE_FLOW_STATUSES,
    cleanup_expired_flow_checkpoints,
    delete_flow_checkpoint,
    list_flow_checkpoints,
    load_flow_checkpoint,
    mark_flow_checkpoint_status,
    save_flow_checkpoint,
)
from hecos.core.action_plans.manager import ActionPlanManager, get_action_plan_manager
from hecos.core.action_plans.models import (
    ACTIVE_PLAN_STATUSES,
    PLAN_MODES,
    PLAN_STATUSES,
    STEP_STATUSES,
    build_plan_markdown_document,
    compute_plan_progress,
)
from hecos.core.action_plans.store import (
    cleanup_expired_plans,
    delete_plan,
    find_latest_plan_for_source,
    list_plans,
    load_plan,
    save_plan,
)

__all__ = [
    "ACTIVE_PLAN_STATUSES",
    "PLAN_MODES",
    "PLAN_STATUSES",
    "STEP_STATUSES",
    "DEFAULT_ACTION_PLANS_CONFIG",
    "RESUMABLE_FLOW_STATUSES",
    "ActionPlanManager",
    "get_action_plan_manager",
    "build_plan_markdown_document",
    "compute_plan_progress",
    "get_action_plans_config",
    "normalize_action_plans_config",
    "save_action_plans_config",
    "save_plan",
    "load_plan",
    "list_plans",
    "find_latest_plan_for_source",
    "delete_plan",
    "cleanup_expired_plans",
    "await_plan_approval",
    "cancel_pending_approval",
    "has_pending_approval",
    "submit_approval_decision",
    "save_flow_checkpoint",
    "load_flow_checkpoint",
    "list_flow_checkpoints",
    "mark_flow_checkpoint_status",
    "delete_flow_checkpoint",
    "cleanup_expired_flow_checkpoints",
]
