import app


def test_get_project_details():
    token = app.get_munis_PL_token()
    assert app.get_project_details(1, token) == "Project 1"
    assert True

