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


@api.errorhandler(HTTPException)
@api.errorhandler(404)
@api.errorhandler(400)
@api.errorhandler(500)
def handler_unknown_error(error):
    """
    Control all possible errors: malformed inputs, nonexistent ids, code
    errors, etc.
    """

    if hasattr(error, 'code'):
        status_code = error.code
        errors = [serialize_error('http-{}'.format(error.code),
                                  error.description)]
    else:
        status_code = 500
        errors = [serialize_error('http-500', type(error).__name__)]

    return jsonify({'status': 'error', 'errors': errors}), status_code


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
    card = get_card_or_404(user, card_id)

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


@api.route('/index.html')
@api.route('/')
def home():
    """
    Provide some instructions on the main page
    """
    with current_app.open_resource('README.md') as readme_file:
        content = readme_file.read().decode('UTF-8')

    html = markdown.markdown(content,
                             extensions=['markdown.extensions.fenced_code'])

    return render_template('api/home.html', content=html)


def check_limits(user, card, amount):
    """
    We need to check that the load does not exceed some compliance limits:

        - maximum £500 worth of loads per day
        - maximum £800 worth of loads per 30 days
        - maximum £2000 worth of loads per 365 days
        - maximum balance at any time £1000
    """
    compliance_limits = (
        (current_app.config['LIMIT_DAY'], timedelta(days=1)),
        (current_app.config['LIMIT_MONTH'], timedelta(days=30)),
        (current_app.config['LIMIT_YEAR'], timedelta(days=365)),
    )

    transactions = get_customer_transactions(user)

    errors = []

    for limit, time_diff in compliance_limits:
        total_amount = calculate_total_amount_by_date(transactions, time_diff)
        if total_amount + amount > limit:
            time_diff_str = str(timedelta(days=1)).split(',')[0]
            errors.append(serialize_compliance_error(total_amount, amount,
                                                     limit, time_diff_str))

    limit = current_app.config['LIMIT_BALANCE']
    if card.balance + amount > limit:
        errors.append(serialize_compliance_error(total_amount, amount,
                                                 limit, 'balance'))

    return errors


def serialize_compliance_error(total_amount, amount, limit, code):
    """
    Produce a Complacence error in the format specified by the API (see README)
    """
    return serialize_error(
        'compliance-{}'.format(code),
        'ComplianceError: {} + {} > {} ({})'.format(
            total_amount, amount, limit, code))


def serialize_error(code, message):
    """
    Produce an error in the format that API specifies (see README)
    """
    return {'code': code, 'message': message}


def calculate_total_amount_by_date(transactions, time_diff):
    """
    Filter a collection of transactions by a timedelta
    """
    return sum((
        transaction.amount for transaction in transactions
        if transaction.created_at >= datetime.now() - time_diff
    ), Decimal(0))


def get_customer_transactions(user):
    """
    Fetch all the Transactions from a given User / Customer that have been
    Settled or could end up been Settled.
    """
    return braintree.Transaction.search(
        TransactionSearch.customer_id == user.customer_id,
        TransactionSearch.status.in_list([
            Transaction.Status.Authorizing,
            Transaction.Status.Authorized,
            Transaction.Status.SubmittedForSettlement,
            Transaction.Status.Settling,
            Transaction.Status.Settled,
        ]),
    ).items


def get_card_or_404(user, card_id):
    """
    Try to fetch a Card from the database, raise a 404 error if it is not there
    """
    try:
        return user.cards.filter_by(id=card_id).one()
    except (exc.NoResultFound, exc.MultipleResultsFound):
        abort(404)


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


def check_transaction(result):
    """
    The transaction may have been successful or it may have returned different
    types of errors.

    More info:
    https://developers.braintreepayments.com/reference/response/transaction/python
    """

    if result.is_success:
        errors = []

    elif result.errors.deep_errors:
        errors = [serialize_error(error.code, error.message)
                  for error in result.errors.deep_errors]

    elif result.transaction.processor_settlement_response_code:
        errors = [serialize_error(
            result.transaction.processor_settlement_response_code,
            result.transaction.processor_settlement_response_text,
        )]

    elif result.transaction.processor_response_code:
        errors = [serialize_error(
            result.transaction.processor_response_code,
            result.transaction.processor_response_text,
        )]

    elif result.transaction.gateway_rejection_reason:
        errors = [serialize_error(
            result.transaction.gateway_rejection_reason,
            '',
        )]

    else:
        message = 'An UNKNOWN transaction error occurred: %d'
        api.logger.error(message, result.transaction.id)
        errors = [serialize_error('UNKNOWN', 'UNKNOWN')]

    return errors
