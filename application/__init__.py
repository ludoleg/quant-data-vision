#################
#### imports ####
#################

from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_cors import CORS
import os
import logging
import sys

################
#### config ####
################

app = Flask(__name__)
bootstrap = Bootstrap(app)
CORS(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
app.config.from_object(os.environ['APP_SETTINGS'])
db = SQLAlchemy(app)
app.logger.info('Welcome to Qanalyze')


from users.views import users_blueprint
from views import *
from models import User

# register our blueprints
app.register_blueprint(users_blueprint)

login_manager.login_view = "users.login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter(User.id == int(user_id)).first()
