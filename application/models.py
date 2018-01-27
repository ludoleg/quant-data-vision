from application import db
from application import bcrypt

from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship


class Mode(db.Model):

    __tablename__ = "modes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    qlambda = db.Column(db.Float)
    qtarget = db.Column(db.String(64))
    fwhma = db.Column(db.Float)
    fwhmb = db.Column(db.Float)
    inventory = db.Column(db.String(64), nullable=False)
    initial = db.Column(db.PickleType)
    author_id = db.Column(db.Integer, ForeignKey('users.id'))

    def __init__(self, title, qlambda, target, fwhma, fwhmb, inventory, initial, author_id):
        self.title = title
        self.qlambda = qlambda
        self.qtarget = target
        self.fwhma = fwhma
        self.fwhmb = fwhmb
        self.inventory = inventory
        self.initial = initial
        self.author_id = author_id

    def __repr__(self):
        return "<Mode(title='%s', qlambda='%.2f', qtarget='%s', fwhma='%.2f', fwhmb='%.2f', inventory='%s,'id='%s')>" % (self.title, self.qlambda, self.qtarget, self.fwhma, self.fwhmb, self.inventory, self.author_id)


class User(db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    modes = relationship("Mode", backref="author")

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = bcrypt.generate_password_hash(password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<name {} id {}>'.format(self.name, self.id)
