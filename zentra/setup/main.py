from .i18n import UI_LANG, set_ui_lang
from .utils import get_current_system_lang

def main():
    # Sync initial language
    initial_lang = get_current_system_lang()
    set_ui_lang(initial_lang)
    
    import sys
    if "--web" in sys.argv:
        from .web_ui import start_web_setup
        start_web_setup()
    else:
        from .cli_ui import start_cli_wizard
        start_cli_wizard()

if __name__ == "__main__":
    main()
