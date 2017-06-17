import pytest

from limits import create_app
from limits.api.models import db, init_db, populate_db_with_fake_state
from limits.config import TestConfig


def pytest_itemcollected(item):
    """
    Show the first line of the docstring (if available) as the test descroption
    """
    if hasattr(item, 'obj'):
        node = item.obj
        description = node.__doc__.strip() if node.__doc__ else node.__name__
        if description:
            item._nodeid = description.split('\n')[0]


@pytest.fixture
def app():
    app = create_app(TestConfig)
    app.testing = True
    return app


@pytest.fixture
def database(app):
    with app.app_context():
        init_db()
        populate_db_with_fake_state()

    yield

    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app, database):
    client = app.test_client()

    with app.test_request_context():
        yield client
