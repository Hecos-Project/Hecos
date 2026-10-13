import os
import sys

sys.path.insert(0, r"c:\Hecos")

from hecos.core.llm.prompt_builder import PromptBuilder
from hecos.modules.playbooks.playbooks.simulation import start_simulation, swap_roles, stop_simulation

chat_id = "test_prompt_builder_chat"
start_simulation(chat_id=chat_id, playbook_id="dio-serpente-meccanico")

config = {
    "ai": {
        "active_personality": "Urania_9800.yaml"
    },
    "cognition": {
        "include_identity_context": False,
        "include_self_awareness": False
    }
}

user_text = "ma tu chi sei? e chi è il dio serpente?"

prompt = PromptBuilder.build_system_prompt(
    config=config,
    user_text=user_text,
    images=[],
    backend_config={},
    session_id=chat_id,
    user_id="admin"
)

print("=== SYSTEM PROMPT START (Unswapped, Chat plays Passante) ===")
print(prompt[:1800])
print("\n... TOTAL LENGTH:", len(prompt))

swap_roles(chat_id=chat_id)

prompt_swapped = PromptBuilder.build_system_prompt(
    config=config,
    user_text=user_text,
    images=[],
    backend_config={},
    session_id=chat_id,
    user_id="admin"
)

print("\n=== SYSTEM PROMPT START (Swapped, Chat plays Predicatore) ===")
print(prompt_swapped[:1800])
print("\n... TOTAL LENGTH:", len(prompt_swapped))

stop_simulation(chat_id=chat_id)
print("\nSimulation stopped.")
