from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Mode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True)
    qlambda = db.Column(db.Float)
    qtarget = db.Column(db.String(64), unique=True)
    fwhma = db.Column(db.Float)
    fwhmb = db.Column(db.Float)
    inventory = db.Column(db.String(64), unique=True)

    def __init__(self, title):
        self.title = title
    
    def __repr__(self):
        return '<User %r>' % (self.nickname)
