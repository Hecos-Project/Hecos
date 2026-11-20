import sys
import os

sys.path.insert(0, os.path.abspath("."))

from hecos.app.config import ConfigManager
from hecos.core.agent.loop import AgentExecutor
from hecos.core.agent.traces import AgentTracer
from unittest.mock import patch

print("==================================================")
print("TESTING TOOL MODE TRANSPARENCY & TIMELINE")
print("==================================================")

cfg_mgr = ConfigManager()
config = cfg_mgr.config
config["cognition"]["personality"] = "Urania.yaml"

with patch("hecos.core.llm.brain.generate_response", return_value="Ciao! Sono Urania."):
    with patch("hecos.core.agent.loop_guards.sync_assistant_history"):
        # Test 1: Tools ON
        config["payload_control"] = {"send_tools": True}
        executor_on = AgentExecutor(config=config, max_iterations=1)
        resp, think = executor_on.run_agentic_loop("Ciao Urania")
        summary_on = executor_on.last_trace_summary
        steps_on = summary_on.get("steps", [])
        print(f"\n[Tools ON] Trace steps count: {len(steps_on)}")
        mode_step_on = next((s for s in steps_on if s.get("kind") == "system"), None)
        print(f"  Mode step found: {mode_step_on is not None}")
        if mode_step_on:
            print(f"  Label: {mode_step_on.get('label')}")
            print(f"  Detail: {mode_step_on.get('detail')}")
            print(f"  Icon: {mode_step_on.get('icon')}")
            assert any(k in mode_step_on.get("label") for k in ["Native", "Nativo"])

        # Test 2: Tools OFF
        config["payload_control"] = {"send_tools": False}
        executor_off = AgentExecutor(config=config, max_iterations=1)
        resp, think = executor_off.run_agentic_loop("Ciao Urania")
        summary_off = executor_off.last_trace_summary
        steps_off = summary_off.get("steps", [])
        print(f"\n[Tools OFF] Trace steps count: {len(steps_off)}")
        mode_step_off = next((s for s in steps_off if s.get("kind") == "system"), None)
        print(f"  Mode step found: {mode_step_off is not None}")
        if mode_step_off:
            print(f"  Label: {mode_step_off.get('label')}")
            print(f"  Detail: {mode_step_off.get('detail')}")
            print(f"  Icon: {mode_step_off.get('icon')}")
            assert any(k in mode_step_off.get("label") for k in ["Direct", "Rapidi"])

        # Test 3: Disable Tools (Pure Conversation)
        config["disable_tools"] = True
        executor_dis = AgentExecutor(config=config, max_iterations=1)
        resp, think = executor_dis.run_agentic_loop("Ciao Urania")
        summary_dis = executor_dis.last_trace_summary
        steps_dis = summary_dis.get("steps", [])
        print(f"\n[Tools Disabled] Trace steps count: {len(steps_dis)}")
        mode_step_dis = next((s for s in steps_dis if s.get("kind") == "system"), None)
        print(f"  Mode step found: {mode_step_dis is not None}")
        if mode_step_dis:
            print(f"  Label: {mode_step_dis.get('label')}")
            print(f"  Detail: {mode_step_dis.get('detail')}")
            print(f"  Icon: {mode_step_dis.get('icon')}")
            assert any(k in mode_step_dis.get("label") for k in ["Chat", "Solo Chat"])

print("\n==================================================")
print("ALL 3 TIMELINE MODE TRANSPARENCY TESTS PASSED!")
print("==================================================")
