from flask_testing import TestCase

from application import app, db
from application.models import User, Mode


class BaseTestCase(TestCase):
    """A base test case."""

    def create_app(self):
        app.config.from_object('config.TestConfig')
        return app

    def setUp(self):
        db.create_all()
        db.session.add(Mode("Diffractometer", 0.0,
                            'Co', 0.0, 0.0, "pigment", 1))
        db.session.add(User("admin", "ad@min.com", "admin"))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
