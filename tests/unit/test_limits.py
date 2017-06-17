

def test_setup(app, database, client):
    """
    Ensure that our test setup works as expected
    """
    assert app is not None
    assert database is None
    assert client is not None
