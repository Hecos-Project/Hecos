import sys
import traceback
try:
    sys.path.insert(0, '.')
    import plugins.drive.extensions.editor.main as meditor
    print("Editor imported.")
    from flask import Flask
    app = Flask("test")
    meditor.init_routes(app)
    print("Routes registered.")
    print("Rules:", app.url_map)
except Exception as e:
    print("ERROR:")
    traceback.print_exc()
