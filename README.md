# Limits

This project provides a basic API to submit payments to Braintree (a standard
payment processor) and load the charged amount into prepaid cards that are
stored in a database.

## Setup

To build and install the python package:

```bash
virtualenv .venv
. .venv/bin/activate
pip install -e .
```

All the dependences are installed automatically, but you can also install them
from the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

To configure the environment to run the application:

```bash
export FLASK_APP=limits
export FLASK_DEBUG=true
```

The `DEBUG` mode may be useful during development.

(On Windows you need to use set instead of export).

If you want to override the settings:

```bash
export LIMITS_SETTINGS=/path/to/settings
```

For example, you could replace the Braintree credentials:

```bash
echo "
BRAINTREE_MERCHANT_ID = '...'
BRAINTREE_PUBLIC_KEY = '...'
BRAINTREE_PRIVATE_KEY = '...'
" >> customconfig.py

export LIMITS_SETTINGS='customconfig.py'
```

To initialize the database and populate it with some fake data:

```bash
flask initdb
flask fake-data
```

## Usage

To run the application:

```bash
flask run
```

The development server will be running on
[http://127.0.0.1:5000/](http://127.0.0.1:5000/). You can navigate to the main
page which will display these instructions.

## API

The API defines the following endpoints:

- Client token generation
- Load a card

### Client token generation

The server is responsible for generating a client token, which contains all
authorization and configuration information the client will need to initialize
the client SDK to communicate with Braintree.

URL: `/tokens/`

Method: POST

#### Query parameters

None.

#### HTTP request body parameters

None.

#### Curl

```bash
curl 'http://127.0.0.1:5000/tokens/' -H 'Content-type: application/json' -d '{}'
```

#### Example response

Status code: 200

```json
{
    "client_token": "U29tZSByYW5kb20gYmFzZTY0IDopCg=="
}
```

### Load a card

In order to load a Card we need the client to provide the server with a nonce:
once the client successfully obtains a customer payment method, it receives
a `payment_method_nonce` representing the customer payment authorization.

URL: `/cards/{:id}/load/`

Method: POST

#### Query parameters

- id: The id of the card that we want to load.

#### HTTP request body parameters

- nonce: The nonce received on the client side from Braintree.
- amount: The amount of money that we want to load. *String*. E.g.: '10.00'.

#### Curl

```bash
curl 'http://127.0.0.1:5000/cards/1/load/' -H 'Content-type: application/json' -d '{"nonce": "fake-valid-visa-nonce", "amount": "10.00"}'
```

#### Example response

Status code: 200

```json
{
    "status": "ok",
    "errors": []
}
```

#### Example error response

An error response due to compliance errors.

`Status code`: 400

```json
{
    "status": "error",
    "errors": [
        {
            "code": "compliance-1-day",
            "message": "495.00 + 10.00 > 500 (1 day)"
        }
    ]
}
```

An error response due to a declined authorization. The error codes and messages
are taken from Braintree error specifications:
https://articles.braintreepayments.com/control-panel/transactions/declines#authorization-decline-codes

`Status code`: 400

```json
{
    "status": "error",
    "errors": [
        {
            "code": "2000",
            "message": "Do Not Honor"
        }
    ]
}
```

An error response due to a malformed input

`Status code`: 400

```json
{
  "status": "error",
  "errors": [
    {
        "code": "http-400",
        "message": "Failed to decode JSON object: Expecting ':' delimiter: line 1 column 11 (char 10)"
    }
  ]
}
```


An error response due to a nonexistent Card id.

`Status code`: 404

```json
{
    "status": "error",
    "errors": [
        {
            "code": "http-404",
            "message": "The requested URL was not found on the server.  If you entered the URL manually please check your spelling and try again."
        }
    ]
}
```


## Testing

To run run the tests:

```bash
python setup.py test
```

You could also call `pytest` directly:

## Compatibility

- Tested on GNU/Linux.
- Tested on Python 3.4.3.

## Known issues

- Instead of implementing an authentication system, a User is injected in every
  session using an `@app.before_request` decorator.
- The session is stored on the client side with a cookie, that means that the
  user could easily be tampered.
- The Sandbox mode is hardcoded in the Braintree initialization, the mode
  should depend on a configuration value from the application configuration.
- The project is configured to use Sqlite by default, which is unsuitable for
  a production environment.
- SQLAlchemy raises a warning when we try to use a `Decimal` object to set the
  value of a `Numeric` column because Sqlite only implements a floating point
  data type.
