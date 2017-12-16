import os


# default config
class BaseConfig(object):
    DEBUG = False
    SECRET_KEY = 'n)\xaa~\t\xd3\xc4\xbfr\x1bn\x9e\x19\\\xad\x9d\x9e\xe9\xf9\x17Onw\t'
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    print SQLALCHEMY_DATABASE_URI


class TestConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False
