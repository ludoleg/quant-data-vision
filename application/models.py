from application import db, bcrypt, login_manager, ma
from flask_login import UserMixin


class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password = db.Column(db.String(128))
    modes = db.relationship('Mode', backref='author')

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = bcrypt.generate_password_hash(password)

    def __repr__(self):
        return '<name {} id {}>'.format(self.name, self.id)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password)

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


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
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __init__(self, title, qlambda, qtarget, fwhma, fwhmb, inventory):
        self.title = title
        self.qlambda = qlambda
        self.qtarget = qtarget
        self.fwhma = fwhma
        self.fwhmb = fwhmb
        self.inventory = inventory

    def __repr__(self):
        return "<Mode(title='%s', qlambda='%.2f', qtarget='%s', fwhma='%.2f', fwhmb='%.2f', inventory='%s','id='%s')>" % (self.title, self.qlambda, self.qtarget, self.fwhma, self.fwhmb, self.inventory, self.author_id)


class ModeSchema(ma.ModelSchema):
    class Meta:
        model = Mode
        # fields = ('id', 'title', 'qlambda', 'fwhma',
        #           'fwhmb', 'qtarget', 'inventory')
