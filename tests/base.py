from flask_testing import TestCase

from application import app, db
from application.models import User, Mode
from application.phaselist import pigmentPhases


class BaseTestCase(TestCase):
    """A base test case."""

    def create_app(self):
        app.config.from_object('config.TestConfig')
        return app

    def setUp(self):
        db.create_all()
        db.session.add(Mode("Diffractometer", 0.0, 'Co',
                            0.0, 0.0, "pigment", sorted(pigmentPhases), 1))
        db.session.add(User("user1", "ad1@min.com", "user1"))
        db.session.add(User("user2", "ad2@min.com", "user2"))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
