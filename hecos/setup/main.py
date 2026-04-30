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
    elif "--auto" in sys.argv:
        # Perform silent/auto health checks for process runner
        from .engine import check_python_version, check_dependencies
        import os
        # Temporarily suppress output to keep the console clean
        sys.stdout = open(os.devnull, 'w')
        try:
            py_ok = check_python_version()
            dep_ok = check_dependencies()
        finally:
            sys.stdout = sys.__stdout__
            
        sys.exit(0 if (py_ok and dep_ok) else 1)
    else:
        from .cli_ui import start_cli_wizard
        start_cli_wizard()

if __name__ == "__main__":
    main()
