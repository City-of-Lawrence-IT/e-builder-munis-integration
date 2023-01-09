from urllib.error import HTTPError
from dotenv import load_dotenv
from os import environ
import sys, pyodbc, logging, requests, json
from datetime import datetime, timedelta, date
from logging.handlers import SMTPHandler
from dateutil import parser
import pandas as pd


load_dotenv()
#email log errors
bot_email = environ.get("EMAIL")
bot_password = environ.get("PASSWORD")
# Apply format to the log messages
formatter = '[{asctime}] [{name}] [{levelname}] - {message}' 
logging.basicConfig(filename="logs/app.log", format=formatter, style="{")
logger = logging.getLogger()
#SMTP Mail handler settup
mail_handler = SMTPHandler(
    mailhost=("smtp.office365.com", 587),
    fromaddr= bot_email, 
    toaddrs="dansmith@lawrenceks.org",
    subject="eBuilder export error",
    credentials=(bot_email, bot_password),
    secure= () 

)
mail_handler.setFormatter(logging.Formatter(
    """
    Message type:       %(levelname)s
    Location:           %(pathname)s:%(lineno)d
    Module:             %(module)s
    Function:           %(funcName)s
    Time:               %(asctime)s

    Message:

    %(message)s
    """

))
mail_handler.setLevel(logging.ERROR)
logger.addHandler(mail_handler)

#global variables for requrests
user_email_address = environ.get("EMAIL")
email_password = environ.get("EMAILPASSWORD")
api_username = environ.get("APIUSERNAME")
password = environ.get("PASSWORD")
token = ""
munis_cred = environ.get("MUNIS_CREDENTIALS")
#setting up logger
""" logger = logging.getLogger('ebuilder-munis-logger')
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


sys.excepthook = error_handler """

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
    url = "https://cityoflawrenceksforms.tylerhost.net/4907prod/devportal/portal/api/clientCredential"

    payload='grant_type=client_credentials&scope=munisOpenApiPOToolkit%20munisOpenApiPLToolkit%20tylerOpenApiServiceAccess'
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://cityoflawrenceksforms-train.tylerhost.net/4907train/devportal/portal/open-api/collection',
    'Content-Type': 'application/x-www-form-urlencoded',
    'X-Requested-With': 'XMLHttpRequest',
    'X-OpenApiDeveloperPortal-TokenEnpoint': 'https://tyler-cityoflawrenceks.okta.com/oauth2/ausfis4bi0hkah3ES357/v1/token',
    'X-OpenApiDeveloperPortal-Client': munis_cred,
    'Origin': 'https://cityoflawrenceksforms-train.tylerhost.net',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-GPC': '1',
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
    try:
        print(environ.get("MUNIS_ENDPOINT")+"munisopenapi/hosts/PO/api/PO/v1/purchaseOrders")
        endpoint = environ.get("MUNIS_ENDPOINT")+"munisopenapi/hosts/PO/api/PO/v1/purchaseOrders"
        payload={}
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer '+token
        }
        yesterday = (date.today()- timedelta(days=1))

        response = requests.request("GET", endpoint, headers=headers, data=payload)
        #print(response.text)
        response = response.text

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
        data = json.loads(response)
        for record in data:
            print(record.get("lastModifiedDate"))
            last_mod = record.get("lastModifiedDate")
            created = record.get("entryDate")
            print(created)
            entry_date = parser.parse(created)
            if (last_mod != None):
                last_mod_date = parser.parse(last_mod)
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
            elif(entry_date.day == yesterday.day):
                print(record)
        return df
    except Exception as e:
        raise e



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