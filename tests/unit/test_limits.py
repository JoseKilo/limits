import os
from decimal import Decimal
from unittest.mock import MagicMock, call, patch

import pytest
from flask import json
from werkzeug.exceptions import BadRequest, NotFound

from limits.api.models import User
from limits.api.views import (
    check_limits, get_card_or_404, handler_unknown_error
)


def test_setup(app, database, client):
    """
    Ensure that our test setup works as expected
    """
    assert app is not None
    assert database is None
    assert client is not None


@patch.dict(os.environ, {'FLASK_APP': 'limits'})
@patch('click.core.Context.exit', MagicMock())
def test_initdb_command(app):
    """
    We can execute the command to initialize the database
    """
    init_db_command = app.cli.commands['initdb']

    with patch('limits.limits.init_db') as init_db_mock:
        init_db_command(args=())

    assert init_db_mock.call_count == 1


@patch.dict(os.environ, {'FLASK_APP': 'limits'})
@patch('click.core.Context.exit', MagicMock())
def test_fake_data_command(app):
    """
    We can execute the command to populate the database with fake data
    """
    populate_db_with_fake_state_command = app.cli.commands['fake-data']

    with patch('limits.limits.populate_db_with_fake_state') as populate_mock:
        populate_db_with_fake_state_command(args=())

    assert populate_mock.call_count == 1


def test_before_first_request(app):
    """
    The Braintree SDK is initialized before the first request
    """
    with patch('limits.limits.braintree') as braintree_mock:
        app.try_trigger_before_first_request_functions()

    assert braintree_mock.Configuration.configure.call_args_list == [
        call(
            braintree_mock.Environment.Sandbox,
            merchant_id=app.config['BRAINTREE_MERCHANT_ID'],
            public_key=app.config['BRAINTREE_PUBLIC_KEY'],
            private_key=app.config['BRAINTREE_PRIVATE_KEY'],
        )
    ]


def test_handler_unknown_error_400(client):
    """
    We get a 400 response as expected in case of a BadRequest exception
    """
    response, status_code = handler_unknown_error(BadRequest)

    assert status_code == 400
    assert json.loads(response.data)['errors'][0]['code'] == 'http-400'


def test_handler_unknown_error_500(client):
    """
    We get a 500 response as expected in case of a SyntaxError
    """
    response, status_code = handler_unknown_error(SyntaxError)

    assert status_code == 500
    assert json.loads(response.data)['errors'][0]['code'] == 'http-500'


def test_get_card_or_404(client):
    """
    If a Card if doesn't exist, we get a NotFound exception that becomes a 404
    """
    user = User.query.one()

    with pytest.raises(NotFound):
        get_card_or_404(user, 42)


def test_check_limits_balance(app, client):
    """
    Any Card can not exceed a balance limit
    """
    amount = Decimal(1)
    card = MagicMock(balance=Decimal(app.config['LIMIT_BALANCE']))
    user = MagicMock(customer_id=1111)
    user.cards.filter_by.one.return_value = card

    with patch('limits.api.views.braintree') as braintree_mock:
        errors = check_limits(user, card, amount)

    assert braintree_mock.Transaction.search.call_count == 1
    assert errors == [
        {'code': 'compliance-balance',
         'message': 'ComplianceError: 0 + 1 > 10000 (balance)'}
    ]
