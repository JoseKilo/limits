import braintree
from flask import Flask, session

from limits.api import api
from limits.api.models import User, db, init_db, populate_db_with_fake_state
from limits.config import PROJECT_NAME


def create_app(config):
    """
    Factory function that instantiates the Flask application
    """
    app = Flask(PROJECT_NAME, static_folder=None)

    app.config.from_object(config)
    app.config.from_envvar('LIMITS_SETTINGS', silent=True)

    db.init_app(app)

    app.register_blueprint(api)

    configure_hooks(app)
    configure_cli(app)

    return app


def configure_cli(app):
    """
    Setup some commands to run from the command line
    """

    @app.cli.command('initdb')
    def initdb_command():
        init_db()
        app.logger.info('Done')

    @app.cli.command('fake-data')
    def populate_db_with_fake_state_command():
        populate_db_with_fake_state()
        app.logger.info('Done')


def configure_hooks(app):
    """
    Setup some hooks on the application workflow:
        - Initialize Braintree on the first request
        - Inject an User object in every session
    """

    @app.before_first_request
    def configure_braintree():
        braintree.Configuration.configure(
            braintree.Environment.Sandbox,
            merchant_id=app.config['BRAINTREE_MERCHANT_ID'],
            public_key=app.config['BRAINTREE_PUBLIC_KEY'],
            private_key=app.config['BRAINTREE_PRIVATE_KEY'],
        )

    @app.before_request
    def force_user():
        session['user'] = User.query.one().id
