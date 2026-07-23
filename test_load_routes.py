import sys, os
sys.path.insert(0, r'c:\Hecos')

import importlib.util

abs_route_path = r'c:\Hecos\hecos\modules\mcp_bridge\web\routes.py'
spec = importlib.util.spec_from_file_location(f"plugin_routes_mcp_bridge", abs_route_path)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    print("Module loaded successfully.")
    
    # mock app and others
    class MockApp:
        def route(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    
    app = MockApp()
    
    mod.init_plugin_routes(app, None, r'c:\Hecos', None)
    print("Routes initialized successfully.")
except Exception as e:
    import traceback
    traceback.print_exc()

