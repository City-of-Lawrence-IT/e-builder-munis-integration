import app


# create a test for get_ebuilder_commitments making sure the function returns the correct data type
def test_get_ebuilder_commitments():
    token = app.get_ebuilder_token()
    assert type(app.get_ebuilder_commitments(token)) == dict


# create a test for get_ebuilder_token making sure the function returns the correct token
def test_get_ebuilder_token():
    assert type(app.get_ebuilder_token()) == str
