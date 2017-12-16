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
    author_id = db.Column(db.Integer, ForeignKey('users.id'))

    def __init__(self, title, qlambda, target, fwhma, fwhmb, inventory):
        self.title = title
        self.qlambda = qlambda
        self.target = target
        self.fwhma = fwhma
        self.fwhmb = fwhmb
        self.inventory = inventory

    def __repr__(self):
        return '<Title %r>' % (self.title)


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

    def __repr__(self):
        return '<name {}'.format(self.name)
