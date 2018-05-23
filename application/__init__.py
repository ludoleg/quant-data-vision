
#### imports ####
#################

from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_cors import CORS
import os
import logging
import sys

from raven.contrib.flask import Sentry

################
#### config ####
################

app = Flask(__name__)
bootstrap = Bootstrap(app)
CORS(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
app.config.from_object(os.environ['APP_SETTINGS'])
db = SQLAlchemy(app)
ma = Marshmallow(app)

sentry = Sentry(app, dsn='https://167cd95842c04c86b0fce09ea3ee0346:415837e90c364637bf7f05f1c03570e2@sentry.io/1211570')
# xsentry.captureMessage('Sentry started')

app.logger.info('Welcome to Qanalyze')

app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

# import logging
# stream_handler = logging.StreamHandler()
# app.logger.addHandler(stream_handler)
# app.logger.setLevel(logging.INFO)
#app.logger.info('=== Qanalyze Startup ----')
logging.info('=== Qanalyze Startup ----')

from users.views import users_blueprint
from views import *
from models import User

# register our blueprints
app.register_blueprint(users_blueprint)

login_manager.login_view = "users.login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter(User.id == int(user_id)).first()


from application import errors
