import app
https://cityoflawrenceksmunisapp-train.tylerhost.net/4907train/munisopenapi/hosts/PO

def test_get_project_details():
    token = app.get_munis_token()
    assert app.get_project_details(1, token) == "Project 1"
    assert True

