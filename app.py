from cmath import log
from urllib.error import HTTPError
from dotenv import load_dotenv
from os import environ
import sys, pyodbc, logging, requests, json
from datetime import datetime, timedelta, date
from logging.handlers import SMTPHandler

import pandas as pd


load_dotenv()
#global variables for requrests
user_email_address = environ.get("EMAIL")
email_password = environ.get("EMAILPASSWORD")
api_username = environ.get("APIUSERNAME")
password = environ.get("PASSWORD")
token = ""
munis_cred = environ.get("MUNIS_CREDENTIALS")
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

#e-builder token refresh function
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
#Get Munis project ledger token
def get_munis_PL_token():
    url = "https://cityoflawrenceksforms-test.tylerhost.net/4907test/devportal/portal/api/clientCredential"

    payload='grant_type=client_credentials&scope=munisOpenApiPOToolkit%20munisOpenApiPLToolkit%20tylerOpenApiServiceAccess'
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://cityoflawrenceksforms-test.tylerhost.net/4907test/devportal/portal/help?encodedUri=https:%2F%2Fcityoflawrenceksmunisapp-test.tylerhost.net%2F4907test%2Fmunisopenapi%2Fhosts%2FPL%2Fswagger%2Fall-versions%2Fswagger.json',
    'Content-Type': 'application/x-www-form-urlencoded',
    'X-Requested-With': 'XMLHttpRequest',
    'X-TID-E-Url': 'https://tyler-cityoflawrenceks.okta.com/oauth2/ausfis4bi0hkah3ES357/v1/token',
    'X-Client': munis_cred,
    'Origin': 'https://cityoflawrenceksforms-test.tylerhost.net',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Cookie': 'ai_user=8O128|2022-07-15T13:51:30.842Z; ai_session=oqs4x|1657898155655|1657898167678',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-GPC': '1'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response_body = json.loads(response.text)
    return response_body["access_token"]

#functions to get Munis Data to send to e-builder
munis_token = get_munis_PL_token()
#Do I need to get the PO data or the project list string? Probably PO data?
#data probably need to connect back to a specific project
#set PO == contractNumber field in get request
def get_commitment_invoice_by_id(token):
    print(environ.get("MUNIS_ENDPOINT")+"munisopenapi/hosts/PO/api/PO/v1/purchaseOrders")
    endpoint = environ.get("MUNIS_ENDPOINT")+"munisopenapi/hosts/PO/api/PO/v1/purchaseOrders"
    payload={}
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer '+token
    }
    yesterday = (date.today()- timedelta(days=1))

    response = requests.request("GET", endpoint, headers=headers, data=payload)
    print(response.text)
    
    column_names = {
        "Invoice Number":[], 
        "Description":[],
        "Company Number":[],
        "Action":[],
        "Date Approved":[],
        "Date Paid":[],
        "Account Code":[],
        "Item Number":[]
    }
    df = pd.DataFrame(data=column_names)
    for record in response:
        last_mod_date = date(record.lastModifiedDate)
        if (last_mod_date.day == yesterday.day):
            approval_date = ""
            account_code = ""
            if (record.isApproved):
                #get project string

                allocations = record.allocations
                projectCode = allocations[0].projectCode
                url = environ.get("MUNIS_ENDPOINT")+"/munisopenapi/hosts/PL/odata/PL/v1/projectStrings?$filter=projectCode eq '"+projectCode+"'"
                payload={}
                headers = {
                'Accept': 'application/json',
                'Authorization': 'Bearer '+token
                }

                projectString = requests.request("GET", url, headers=headers, data=payload)
                #get approval date
                approval_date = projectString.approvalDate
                
            
            
            tempdf = {
            "Invoice Number":[record.purchaseOrderNumber], 
            "Description":[record.commodityCode],#second call to get details?
            "Company Number":[record.vendorNumber],
            "Action":[record.status],
            "Date Approved":[approval_date],#get project string, get approval date if approved
            "Date Paid":[record.x], # if closed, get the receipt recieved date
            "Account Code":[allocations.fullAccount],
            "Item Number":[record.items.lineNumber]
        }
            df.append()
    return df



commitment_invoices = get_commitment_invoice_by_id(munis_token)
commitment_invoices.to_csv('CommitmentInvoicesUpdate.csv', index=False)
"""
Order of operations:
- get list of purchase orders
- filter by changes made in last 24 hours
- get change order status 
value ID, old value, new value, changed

    "lastModifiedDate": "2022-10-25T20:14:59.056Z",
"""
#functions to get e-builder data to send to Munis