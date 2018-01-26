# Logging levels:
# Text logging level for the message ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').


import os


# default config
class BaseConfig:
    DEBUG = False
    SECRET_KEY = 'n)\xaa~\t\xd3\xc4\xbfr\x1bn\x9e\x19\\\xad\x9d\x9e\xe9\xf9\x17Onw\t'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    print SQLALCHEMY_DATABASE_URI

    @staticmethod
    def init_app(app):
        pass


class TestConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class StagingConfig(BaseConfig):
    @classmethod
    def init_app(cls, app):
        BaseConfig.init_app(app)

        # log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


class ProductionConfig(BaseConfig):
    @classmethod
    def init_app(cls, app):
        BaseConfig.init_app(app)

        # log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestConfig,
    'production': ProductionConfig,
    'staging': StagingConfig,

    'default': DevelopmentConfig
}
