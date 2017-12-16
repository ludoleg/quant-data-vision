#################
#### imports ####
#################

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os

################
#### config ####
################

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config.from_object(os.environ['APP_SETTINGS'])
db = SQLAlchemy(app)

from users.views import users_blueprint
from views import *

# register our blueprints
app.register_blueprint(users_blueprint)

if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used for heroku
    app.run()
