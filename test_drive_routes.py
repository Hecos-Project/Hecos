import sys, os
sys.path.insert(0, r"c:\Zentra-Core")
try:
    from flask import Flask
    app = Flask('test')
    
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("Test")
    
    print("Importing init_drive_routes...")
    from plugins.drive.routes import init_drive_routes
    
    print("Executing init_drive_routes...")
    init_drive_routes(app, logger)
    
    print("Registered Blueprints:", list(app.blueprints.keys()))
    
except Exception as e:
    import traceback
    traceback.print_exc()
    
