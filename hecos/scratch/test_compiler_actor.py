import os
import sys

# Add project root to sys.path
sys.path.insert(0, r"c:\Hecos")

from hecos.modules.playbooks.playbooks.compiler import get_chat_playbook_context, get_presenter_playbook_context
from hecos.modules.playbooks.playbooks.simulation import start_simulation, swap_roles, stop_simulation

chat_id = "test_actor_sim"
print("--- Starting simulation ---")
res = start_simulation(chat_id=chat_id, playbook_id="dio-serpente-meccanico")
print("Start result:", res)

print("\n=== CHAT CONTEXT (Unswapped, Urania) ===")
chat_ctx = get_chat_playbook_context(chat_id=chat_id, personality_name="Urania_9800")
print(chat_ctx[:1800])
print("...\nTotal length:", len(chat_ctx))

print("\n--- Swapping roles ---")
swap_res = swap_roles(chat_id=chat_id)
print("Swap result:", swap_res)

print("\n=== PRESENTER CONTEXT (Swapped) ===")
pres_ctx = get_presenter_playbook_context(chat_id=chat_id)
print(pres_ctx[:1200])

stop_simulation(chat_id=chat_id)
print("\nSimulation stopped.")
