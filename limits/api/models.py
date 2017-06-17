from decimal import Decimal
from uuid import uuid1

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    """
    A User is linked to a Customer entity in Braintree via its 'customer_id'
    """

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, unique=True)
    email = db.Column(db.Text, unique=True)
    customer_id = db.Column(db.Text, unique=True)

    def __init__(self, username, email):
        self.username = username
        self.email = email

        # The Customer id must be 36 characters maximum. UUIDs are always 36
        # chars Ussing UUIDs version 1 we ensure that we get unique IDs for
        # each User even if they are generated on different servers. It also
        # ensures that we get different IDs on every test run, so that previous
        # transactions from the Sandbox don't affect the tests result.
        self.customer_id = str(uuid1())


class Card(db.Model):
    """
    A Card keeps a balance and it's associated to a User
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('cards', lazy='dynamic'))
    balance = db.Column(db.Numeric)

    def __init__(self, user, name):
        self.user = user
        self.name = name
        self.balance = Decimal(0)


def init_db():
    """
    Create all the database tables using SQLAlchemy
    """
    db.create_all()


def populate_db_with_fake_state():
    """
    Populate the database with a fake User and Card
    """
    user = User('guest', 'guest@example.com')
    card = Card(user, 'Card-1')

    if User.query.filter_by(username=user.username).count() == 0:
        db.session.add(user)
        db.session.add(card)
        db.session.commit()
