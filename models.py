from app import db


class Mode(db.Model):
    __tablename__ = "modes"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True)
    qlambda = db.Column(db.Float)
    qtarget = db.Column(db.String(64), unique=True)
    fwhma = db.Column(db.Float)
    fwhmb = db.Column(db.Float)
    inventory = db.Column(db.String(64), unique=True)

    def __init__(self, title, qlambda, target, fwhma, fwhmb, inventory):
        self.title = title
        self.qlambda = qlambda
        self.target = target
        self.fwhma = fwhma
        self.fwhmb = fwhmb
        self.inventory = inventory

    def __repr__(self):
        return '<User %r>' % (self.title)
