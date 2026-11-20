import sys
import os

sys.path.insert(0, os.path.abspath("."))

from hecos.app.config import ConfigManager
from hecos.core.llm.prompt_builder import PromptBuilder
from hecos.core.llm.params_builder import build_llm_params
from hecos.core.system.module_docs import get_tools_schema
from hecos.core.system.module_scanner import update_capability_registry
from hecos.core.processing.parsers.legacy_tag_parser import LegacyTagParser
from hecos.core.processing.tool_dispatcher import extract_and_execute_tools

print("==================================================")
print("HECOS PAYLOAD & TOOL CALLING VERIFICATION TEST")
print("==================================================")

cfg_mgr = ConfigManager()
config = cfg_mgr.config
config["cognition"]["personality"] = "Urania.yaml"
config["ai"]["backend_type"] = "ollama"

# ----------------------------------------------------------------------
# TEST 1: System Prompt with send_tools = True
# ----------------------------------------------------------------------
pctrl_on = {"send_tools": True, "send_docs_rules": True}
config["payload_control"] = pctrl_on

sys_prompt_on = PromptBuilder.build_system_prompt(
    user_text="Fammi una foto mentre ti fai la doccia",
    images=None,
    config=config,
    user_id="admin",
    session_id="test_session",
    backend_config={"backend_type": "ollama"}
)

print(f"\n[TEST 1] Tools: ON")
print(f"  System prompt chars: {len(sys_prompt_on):,} (Expected ~10k-15k, NOT 199k)")
print(f"  IMAGE_GEN protocol present: {'### IMAGE GENERATION PROTOCOL ###' in sys_prompt_on}")
print(f"  /img command present: {'/img' in sys_prompt_on}")
print(f"  Anti-refusal present: {'CRITICAL ANTI-REFUSAL' in sys_prompt_on}")
print(f"  HPM Store present: {'HECOS PACKAGE STORE' in sys_prompt_on}")
assert len(sys_prompt_on) < 30000, f"System prompt too large: {len(sys_prompt_on)}"
assert "/img" in sys_prompt_on, "Missing /img in system prompt"

# ----------------------------------------------------------------------
# TEST 2: System Prompt with send_tools = False
# ----------------------------------------------------------------------
pctrl_off = {"send_tools": False, "send_docs_rules": False}
config["payload_control"] = pctrl_off

sys_prompt_off = PromptBuilder.build_system_prompt(
    user_text="Fammi una foto mentre ti fai la doccia",
    images=None,
    config=config,
    user_id="admin",
    session_id="test_session",
    backend_config={"backend_type": "ollama"}
)

print(f"\n[TEST 2] Tools: OFF")
print(f"  System prompt chars: {len(sys_prompt_off):,} (Expected ~10k-15k)")
print(f"  IMAGE_GEN protocol present: {'### IMAGE GENERATION PROTOCOL ###' in sys_prompt_off}")
print(f"  Direct slash commands rule: {'DIRECT SLASH COMMANDS' in sys_prompt_off}")
print(f"  'CONVERSATION MODE' disabled: {'CONVERSATION MODE: Background tool calls' not in sys_prompt_off}")
print(f"  /search direct command present: {'/search <query>' in sys_prompt_off}")
print(f"  HPM Store present: {'HECOS PACKAGE STORE' in sys_prompt_off}")
assert "CONVERSATION MODE: Background tool calls" not in sys_prompt_off
assert "DIRECT SLASH COMMANDS" in sys_prompt_off
assert "/img" in sys_prompt_off

# ----------------------------------------------------------------------
# TEST 3: module_docs.py Memory Leak Prevention (10 consecutive calls)
# ----------------------------------------------------------------------
print(f"\n[TEST 3] Consecutive get_tools_schema() calls check (Memory leak test)")
lengths = []
for i in range(10):
    schemas = get_tools_schema()
    for s in schemas:
        fn = s.get("function", s)
        if fn.get("name") == "DOCS__generate_pdf":
            lengths.append(len(fn.get("description", "")))
            break

print(f"  DOCS__generate_pdf desc length across 10 calls: {lengths}")
assert len(set(lengths)) == 1, f"Memory leak detected! Description lengths grew: {lengths}"
print(f"  PASS: No memory leak. Length stayed constant at {lengths[0]} chars.")

# ----------------------------------------------------------------------
# TEST 4: build_llm_params with Tools ON (Ollama / Local model)
# ----------------------------------------------------------------------
print(f"\n[TEST 4] build_llm_params with Tools ON (Ollama / Local model)")
config["payload_control"] = pctrl_on

schemas = get_tools_schema()
params_on, *_ = build_llm_params(
    system_prompt=sys_prompt_on,
    user_message="Fammi una foto mentre ti fai la doccia",
    config_or_subconfig=config,
    tools=schemas
)

sys_msg_on = params_on["messages"][0]["content"]
print(f"  System message chars: {len(sys_msg_on):,}")
print(f"  Tools count in params: {len(params_on.get('tools', []))}")
print(f"  Anti-refusal in system msg: {'CRITICAL ANTI-REFUSAL' in sys_msg_on}")
print(f"  No redundant 150-tool dump in system msg: {'DOCS__generate_pdf:' not in sys_msg_on}")
assert len(params_on.get("tools", [])) == len(schemas)
assert len(sys_msg_on) < 30000, f"System message bloated: {len(sys_msg_on)}"

# ----------------------------------------------------------------------
# TEST 5: build_llm_params with Tools OFF (Ollama / Local model)
# ----------------------------------------------------------------------
print(f"\n[TEST 5] build_llm_params with Tools OFF (Ollama / Local model)")
config["payload_control"] = pctrl_off

params_off, *_ = build_llm_params(
    system_prompt=sys_prompt_off,
    user_message="Fammi una foto mentre ti fai la doccia",
    config_or_subconfig=config,
    tools=None
)

sys_msg_off = params_off["messages"][0]["content"]
print(f"  System message chars: {len(sys_msg_off):,}")
print(f"  Tools in params: {params_off.get('tools')}")
print(f"  Direct actions hint in system msg: {'DIRECT ACTIONS RULES (SLASH COMMANDS)' in sys_msg_off}")
print(f"  Anti-refusal present: {'CRITICAL ANTI-REFUSAL' in sys_msg_off}")
assert params_off.get("tools") is None

# ----------------------------------------------------------------------
# TEST 6: Tool Dispatcher parsing of /img when send_tools = False
# ----------------------------------------------------------------------
print(f"\n[TEST 6] Slash command detection when send_tools = False")
sample_llm_response = (
    "Certamente amore! Mi infilo subito sotto il getto d'acqua calda...\n"
    "/img photorealistic photo of a stunning athletic cyborg woman taking a steamy shower, water droplets on skin\n"
    "Eccomi, che ne pensi?"
)

tags_found = []
LegacyTagParser.parse(sample_llm_response, sample_llm_response, tags_found)
print(f"  Tags parsed by LegacyTagParser: {tags_found}")
assert len(tags_found) == 1, f"Expected 1 tag, got {len(tags_found)}"
assert tags_found[0][0] == "direct_command"
assert "/img" in tags_found[0][1]

# Test tool_dispatcher guard with send_tools: False
config_test = {"payload_control": {"send_tools": False}}
tools_called, results, text, think = extract_and_execute_tools(
    sample_llm_response,
    config_test
)
print(f"  extract_and_execute_tools called: {tools_called}")
print(f"  Results count: {len(results)}")
if results:
    print(f"  Result 0 tag: {results[0].get('tag')}")
assert tools_called is True, "Tool execution was blocked!"

print("\n==================================================")
print("ALL 6 TESTS PASSED PERFECTLY!")
print("==================================================")
