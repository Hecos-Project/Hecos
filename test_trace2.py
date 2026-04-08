import sys, traceback, os
with open("C:\\Zentra-Core\\test_trace.txt", "w") as f:
    try:
        sys.path.insert(0, '.')
        from plugins.web_ui.server import start_if_needed
        import app.config as config
        f.write("Imports successful.\n")
        f.flush()
        
        cfg = config.ConfigManager()
        from flask import Flask
        flask_app = Flask("test")
        f.write("Flask app created.\n")
        
        # Test Drive's Routes module
        from plugins.drive.routes import init_drive_routes
        init_drive_routes(flask_app, None)
        
        f.write("init_drive_routes completed.\n")
        
        bps = flask_app.blueprints.keys()
        f.write(f"Registered Blueprints: {list(bps)}\n")
        
        rules = [str(r) for r in flask_app.url_map.iter_rules()]
        f.write(f"Rules containing 'editor': {[r for r in rules if 'editor' in r]}\n")
        
    except Exception as e:
        f.write("ERROR OCCURRED:\n")
        f.write(traceback.format_exc())
