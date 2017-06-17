PROJECT_NAME = 'Limits'


class BaseConfig(object):

    SECRET_KEY = (b'#\xf1\x8a\x02\x8d\x95c;\x7f\xb6'
                  b'\xf2\xc1m/\xb3y@\xe59cd\x85\xb5>')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # We need to check that the load does not exceed some compliance limits:
    #
    #     - maximum £500 worth of loads per day
    #     - maximum £800 worth of loads per 30 days
    #     - maximum £2000 worth of loads per 365 days
    #     - maximum balance at any time £1000

    LIMIT_DAY = 500
    LIMIT_MONTH = 800
    LIMIT_YEAR = 2000
    LIMIT_BALANCE = 1000


class BraintreeSandBoxMixin(object):

    BRAINTREE_MERCHANT_ID = 'd2jq67hwxwd274qt'
    BRAINTREE_PUBLIC_KEY = '2f6ppzzkvt7cgpd5'
    BRAINTREE_PRIVATE_KEY = 'f817c2cf7bc3f8d2ed7d14a9afb38852'


class DevConfig(BraintreeSandBoxMixin, BaseConfig):

    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/limits-dev.db'


class TestConfig(BraintreeSandBoxMixin, BaseConfig):

    SQLALCHEMY_DATABASE_URI = 'sqlite://'

    # In some tests we want to be able to load bigger amounts so that we get
    # fake errors back from the Sandbox.
    # More info:
    # https://developers.braintreepayments.com/reference/general/testing/python#test-amounts
    LIMIT_DAY = 500 * 10
    LIMIT_MONTH = 800 * 10
    LIMIT_YEAR = 2000 * 10
    LIMIT_BALANCE = 1000 * 10
