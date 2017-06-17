from datetime import datetime, timedelta
from decimal import Decimal

import braintree
import markdown
from braintree import Transaction, TransactionSearch
from flask import (
    Blueprint, abort, current_app, jsonify, render_template, request, session
)
from sqlalchemy.orm import exc
from werkzeug.exceptions import HTTPException

from limits.api.models import User, db


api = Blueprint('api', __name__, template_folder='templates',
                static_folder='static')


@api.route('/tokens/', methods=['POST'])
def generate_token():
    """
    This endpoint generates a Braintree token that can be used by the client
    """
    user = get_user()

    ensure_customer_created(user)

    client_token = braintree.ClientToken.generate({
        'customer_id': user.customer_id
    })

    return jsonify({'client_token': client_token})


@api.route('/cards/<card_id>/load/', methods=['POST'])
def load_card(card_id):
    """
    This endpoint allows to load a Card with money
    """
    nonce, amount = parse_load_card_input()
    amount = Decimal(amount)

    user = get_user()
    card = user.cards.filter_by(id=card_id).one()  # TODO 404

    ensure_customer_created(user, nonce=nonce)

    errors = check_limits(user, card, amount)
    if errors:
        return jsonify({'status': 'error', 'errors': errors}), 400

    result = make_transaction(user, amount, nonce)
    errors = check_transaction(result)

    if not errors:
        card.balance += amount
        db.session.commit()

    status_code = 200 if not errors else 400
    status = 'ok' if not errors else 'error'
    return jsonify({'status': status, 'errors': errors}), status_code


def check_limits(user, card, amount):
    """
    We need to check that the load does not exceed some compliance limits:

        - maximum £500 worth of loads per day
        - maximum £800 worth of loads per 30 days
        - maximum £2000 worth of loads per 365 days
        - maximum balance at any time £1000
    """
    pass  # TODO


def get_user():
    """
    Retrieve the User from the session
    """
    return User.query.filter_by(id=session['user']).one()


def ensure_customer_created(user, *, nonce=None):
    """
    Create a Customer in Braintree.
    Idempotent operation: if the Customer already exists, nothing will change.
    """
    payload = {'id': user.customer_id}

    if nonce is not None:
        payload['payment_method_nonce'] = nonce

    braintree.Customer.create(payload)


def parse_load_card_input():
    """
    Try to parse using standard form format first, if it fails, use json.
    """
    try:
        nonce = request.form['nonce']
        amount = request.form['amount']
    except HTTPException:
        request_body = request.get_json(force=True)
        nonce = request_body['nonce']
        amount = request_body['amount']

    return nonce, amount


def make_transaction(user, amount, nonce):
    """
    Execure a Transaction on Braintree
    """
    return braintree.Transaction.sale({
        'amount': amount,
        'payment_method_nonce': nonce,
        'customer_id': user.customer_id,
        'options': {
            'submit_for_settlement': True
        }
    })
