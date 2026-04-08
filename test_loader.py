import sys, os, importlib.util, traceback
sys.path.insert(0, r"c:\Zentra-Core")
try:
    print("Test 1: Discover Extensions")
    from core.system.extension_loader import discover_extensions, load_extension_routes, _extension_registry, _extension_paths
    discover_extensions("DRIVE", r"C:\Zentra-Core\plugins\drive")
    print("Registry:", _extension_registry)
    print("Paths:", _extension_paths)

    from flask import Flask
    app = Flask('test')

    print("\nTest 2: Direct load code block")
    key = ("DRIVE", "editor")
    main_path = _extension_paths.get(key)
    print("main_path:", main_path)

    plugin_dir = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(main_path))))
    print("plugin_dir:", plugin_dir)
    module_name = f"plugins.{plugin_dir}.extensions.editor.main"
    print("module_name:", module_name)

    spec = importlib.util.spec_from_file_location(module_name, main_path)
    print("spec:", spec)

    module = importlib.util.module_from_spec(spec)
    print("module:", module)

    spec.loader.exec_module(module)
    print("exec_module finished")

    if hasattr(module, "init_routes"):
        module.init_routes(app)
        print("init_routes called successfully")
        print("Blueprints:", app.blueprints.keys())

except Exception as e:
    print("\nEXCEPTION:", e)
    traceback.print_exc()
