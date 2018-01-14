#################
#### imports ####
#################

from flask import Flask
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
CORS(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
app.config.from_object(os.environ['APP_SETTINGS'])
db = SQLAlchemy(app)
# Need to de-register the default handler since I have to enable the other handler for Heroku, otherwise entries are duplicated
# Needed for Heroku
app.logger.addHandler(logging.StreamHandler(sys.stdout))
# app.logger.setLevel(logging.DEBUG)
app.logger.setLevel(logging.INFO)
# app.logger.setLevel(logging.WARNING)
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
