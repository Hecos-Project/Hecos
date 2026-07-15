
import sys, os
sys.path.insert(0, 'c:/Hecos')
from flask import Flask
from hecos.modules.web_ui.routes_config_core import init_config_core_routes
from hecos.app.config import ConfigManager
import logging
app = Flask(__name__, template_folder='c:/Hecos/hecos/modules/web_ui/templates')
app.secret_key = 'test'
class DummyUser:
    is_authenticated = True
    id = 'admin'
# Mock flask_login.current_user
import flask_login
flask_login.current_user = DummyUser()
cfg_mgr = ConfigManager()
logger = logging.getLogger('test')
init_config_core_routes(app, cfg_mgr, logger, get_sm=lambda: None)
with app.test_client() as c:
    r = c.get('/hecos/config/fragment/browser')
    print('STATUS:', r.status_code)
    print(r.data.decode('utf-8')[:200])

