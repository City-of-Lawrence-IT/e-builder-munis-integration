from dotenv import load_dotenv
from os import environ


load_dotenv()
USER_EMAIL_ADDRESS = environ.get("EMAIL")
EMAIL_PASSWORD = environ.get("EMAILPASSWORD")
USERNAME = environ.get("USERNAME")
PASSWORD = environ.get("PASSWORD")