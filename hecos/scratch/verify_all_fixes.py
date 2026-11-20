import sys, os
sys.path.insert(0, os.path.abspath('.'))

from hecos.core.llm.prompt_builder import PromptBuilder
from hecos.core.llm.params_builder import build_llm_params
from hecos.core.agent.media_interceptor import MediaInterceptor

print("--- 1. Testing PromptBuilder with Tools ON ---")
b_cfg = {'backend_type': 'ollama', 'model': 'masska129/gemma-4-abliterated:12b-qat'}
cfg_on = {
    'ai': {'active_personality': 'Urania_9800'},
    'payload_control': {'send_tools': True, 'send_personality': True, 'send_memory': True},
    'cognition': {'memory_enabled': True, 'episodic_memory': True}
}

p_on = PromptBuilder.build_system_prompt('ciao', [], cfg_on, 'admin', 'test_sess', b_cfg)
print(f"PROMPT TOOLS ON length: {len(p_on)} characters")
print("Has CORE section:", "### ACTIVE CORE SYSTEM PROTOCOLS ###" in p_on)
print("Has HPM section:", "### ACTIVE INSTALLED PACKAGES (HPM) ###" in p_on)
print("MESSENGER excluded:", "MESSENGER" not in p_on)
print("MEMORY excluded from capabilities:", "- MEMORY:" not in p_on)
print(f"History turns in b_cfg: {len(b_cfg.get('history_turns', []))}")

print("\n--- 2. Testing PromptBuilder with Tools OFF ---")
b_cfg_off = {'backend_type': 'ollama', 'model': 'masska129/gemma-4-abliterated:12b-qat'}
cfg_off = {
    'ai': {'active_personality': 'Urania_9800'},
    'payload_control': {'send_tools': False, 'send_personality': True, 'send_memory': True},
    'cognition': {'memory_enabled': True, 'episodic_memory': True}
}
p_off = PromptBuilder.build_system_prompt('ciao', [], cfg_off, 'admin', 'test_sess', b_cfg_off)
print(f"PROMPT TOOLS OFF length: {len(p_off)} characters")
print(f"Token savings (chars): {len(p_on) - len(p_off)} (~{(len(p_on) - len(p_off))//3.5:.0f} tokens)")
print("NetSearch omitted:", "NET SEARCH & WEB INTELLIGENCE PROTOCOL" not in p_off)
print("Plugin guidelines omitted:", "PLUGIN GUIDELINES" not in p_off)
print("Conversation mode rule:", "CONVERSATION MODE" in p_off)

print("\n--- 3. Testing params_builder Native Multi-Turn Messages ---")
b_cfg_turns = {
    'backend_type': 'ollama',
    'model': 'masska129/gemma-4-abliterated:12b-qat',
    'history_turns': [
        {'role': 'user', 'content': 'abbiamo preso una gattina'},
        {'role': 'assistant', 'content': 'Che meraviglia!'}
    ]
}
params, _, _, _, _ = build_llm_params('system prompt here', 'sta continuando a miagolare', b_cfg_turns)
msgs = params.get('messages', [])
print(f"Messages count: {len(msgs)}")
for i, m in enumerate(msgs):
    print(f"  [{i}] role={m.get('role')}, content={m.get('content')[:40]}...")

print("\n--- 4. Testing MediaInterceptor Semantic Prompt Retention ---")
tool_res = [{'tag': 'IMAGE_GEN', 'output': '🎨 Generated image for: a cute small kitten\n\n[[IMG:kitten_123.png]]'}]
ui_text = MediaInterceptor.append_ui_media_to_text('Ecco la foto!', tool_res)
print("MediaInterceptor result:\n" + ui_text)

