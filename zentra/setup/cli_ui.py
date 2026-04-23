import os
from . import i18n
from .i18n import T
from .utils import VOICE_MAP, get_current_system_lang
from .engine import (
    check_python_version, install_dependencies, auto_fix_piper_path, 
    manage_service, set_system_language, download_voice, check_dependencies
)

def voice_selection_menu():
    from .engine import fetch_piper_voices, download_voice
    voices = fetch_piper_voices()
    if not voices:
        print("[-] Could not fetch voices.")
        return

    # Group by language
    langs = sorted(list(set(v.get("language", {}).get("name_english", "Other") for v in voices.values())))
    
    print(T("select_lang"))
    for i, l in enumerate(langs):
        print(f" {i+1}) {l}")
    
    try:
        l_idx = int(input("\nSelect Language # --> ")) - 1
        if 0 <= l_idx < len(langs):
            selected_lang = langs[l_idx]
            v_in_lang = [(k, v) for k, v in voices.items() if v.get("language", {}).get("name_english") == selected_lang]
            
            print(f"\n--- {selected_lang} ---")
            for i, (k, v) in enumerate(v_in_lang):
                print(f" {i+1}) {v.get('name')} ({v.get('quality')}) [{k}]")
            
            v_idx = int(input("\nSelect Voice # --> ")) - 1
            if 0 <= v_idx < len(v_in_lang):
                download_voice(v_in_lang[v_idx][0])
    except (ValueError, IndexError):
        print(T("invalid_opt"))

def lang_selection_menu():
    print(T("select_lang"))
    print(f"({T('tip_lang_multilingual')})")
    print(" 1) English")
    print(" 2) Italiano")
    from .engine import set_system_language
    c = input("--> ")
    if c == '1': set_system_language("en")
    elif c == '2': set_system_language("it")

def guided_onboarding():
    from .engine import fetch_piper_voices, download_voice, unattended_onboarding
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 60)
    print(f"  {T('onboarding_header')}")
    print("=" * 60)
    print()
    
    # Step 1: Language Select
    print(f"[STEP 1: {T('step_lang')}]")
    lang_selection_menu()
    print()

    # Step 2: Voice Select (Bulk)
    print(f"[STEP 2: {T('step_voice')}]")
    voices = fetch_piper_voices()
    selected_voices = []
    
    if voices:
        # Group by language for selection
        langs = sorted(list(set(v.get("language", {}).get("name_english", "Other") for v in voices.values())))
        while True:
            print(f"\n--- {T('select_voice')} ({len(selected_voices)} Selected) ---")
            for i, l in enumerate(langs):
                print(f" {i+1}) {l}")
            print(f" 0) -> CONTINUE TO INSTALLATION <-")
            
            l_choice = input("\nSelect Language # (or 0) --> ")
            if l_choice == '0': break
            
            try:
                l_idx = int(l_choice) - 1
                if 0 <= l_idx < len(langs):
                    target_lang = langs[l_idx]
                    v_in_lang = [(k, v) for k, v in voices.items() if v.get("language", {}).get("name_english") == target_lang]
                    print(f"\n--- {target_lang} Voices ---")
                    for i, (k, v) in enumerate(v_in_lang):
                        status = "[X]" if k in selected_voices else "[ ]"
                        print(f" {i+1}) {status} {v.get('name')} ({v.get('quality')})")
                    
                    v_choice = input("\nToggle Voice # (or 0 to go back) --> ")
                    if v_choice != '0':
                        v_idx = int(v_choice) - 1
                        if 0 <= v_idx < len(v_in_lang):
                            v_key = v_in_lang[v_idx][0]
                            if v_key in selected_voices: selected_voices.remove(v_key)
                            else: selected_voices.append(v_key)
            except (ValueError, IndexError):
                pass

    # Step 3: Start Bulk Installation
    print(f"\n[STEP 3: {T('step_install').upper()}]")
    unattended_onboarding(target_voices=selected_voices)
    
    input(f"\n{T('press_enter')}")

def start_cli_wizard():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=" * 60)
        print(f"  {T('header')}")
        print("=" * 60)
        print(f"\n 1) {T('onboarding_header')} (RECOMMENDED)")
        print(f" 2) {T('menu_opt_1')}")
        print(f" 3) {T('menu_opt_2')}")
        print(f" 4) {T('menu_opt_3')}")
        print(f" 5) {T('menu_opt_4')}")
        print(f" 6) {T('menu_opt_5')}")
        print(f" 7) Manage System Service")
        print(f" 9) Start WEB Setup Wizard")
        print(f" 10) Toggle Setup Language (Current: {i18n.UI_LANG.upper()})")
        print(f" 0) Exit")
        
        choice = input("\n--> ")
        if choice == '1': guided_onboarding()
        elif choice == '2': check_python_version()
        elif choice == '3': auto_fix_piper_path()
        elif choice == '4': 
            check_python_version()
            check_dependencies()
            auto_fix_piper_path()
        elif choice == '5': lang_selection_menu()
        elif choice == '6': voice_selection_menu()
        elif choice == '7':
            print(" 1) Install Service\n 2) Uninstall Service")
            c = input("--> ")
            if c == '1': manage_service("install")
            elif c == '2': manage_service("uninstall")
        elif choice == '9': 
            from .web_ui import start_web_setup
            start_web_setup()
        elif choice == '10': 
            i18n.set_ui_lang("it" if i18n.UI_LANG == "en" else "en")
        elif choice == '0':
            print(T("exit_msg"))
            break
        else: print(T("invalid_opt"))
            
        input(f"\n{T('press_enter')}")
