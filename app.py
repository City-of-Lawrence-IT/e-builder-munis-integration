from cmath import log
from urllib.error import HTTPError
from dotenv import load_dotenv
from os import environ
import sys, pyodbc, logging, requests, json
from datetime import timedelta, date
from logging.handlers import SMTPHandler

import pandas as pd


load_dotenv()
#global variables for requrests
user_email_address = environ.get("EMAIL")
email_password = environ.get("EMAILPASSWORD")
api_username = environ.get("APIUSERNAME")
password = environ.get("PASSWORD")
token = ""
#setting up logger
logger = logging.getLogger('ebuilder-munis-logger')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
file_logger = logging.FileHandler('test.log')
file_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d %(message)s')
ch.setFormatter(formatter)
file_logger.setFormatter(formatter)
logger.addHandler(ch)
logger.addHandler(file_logger)

def error_handler(error_type, error_value, trace_back):
    print(trace_back)
    logger.exception('Uncaught exception: {}'.format(str(error_value)))


sys.excepthook = error_handler

#token refresh function
def refresh_token():
    try:
        url = "https://api2.e-builder.net/api/v2/Authenticate"
        payload='grant_type=password&username='+api_username+'&password='+password
        payload = payload.replace("@", "%40")
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        json_body = response.text
        json_body = json.loads(json_body)
        new_token = json_body["access_token"]
        global token
        token = new_token
        
    except HTTPError as e:
        logger.exception(e)

#functions to get Munis Data to send to e-builder
def get_commitment_invoice_by_id():
    pass

#functions to get e-builder data to send to Munis