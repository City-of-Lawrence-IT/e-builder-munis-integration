from urllib.error import HTTPError
from dotenv import load_dotenv
from os import environ
import sys, pyodbc, logging, requests, json, pprint
from datetime import datetime, timedelta, date
import pyodbc
from logging.handlers import SMTPHandler
from dateutil import parser
import pandas as pd

load_dotenv()
# global variables for requrests
USER_EMAIL_ADDRESS = environ.get("EMAIL")
email_password = environ.get("EMAILPASSWORD")
EB_API_BASE_URL = environ.get("EB_API_BASE_URL")
EB_API_USERNAME = environ.get("EB_API_USERNAME")
EB_API_PASSWORD = environ.get("EB_API_PASSWORD")
MUNIS_API_TOKEN_URL = environ.get("MUNIS_API_TOKEN_URL")
MUNIS_API_CLIENT_ID = environ.get("MUNIS_API_CLIENT_ID")
MUNIS_API_CLIENT_SECRET = environ.get("MUNIS_API_CLIENT_SECRET")
MUNIS_API_SCOPES = environ.get("MUNIS_API_SCOPES")
MUNIS_API_BASE_URL = environ.get("MUNIS_API_BASE_URL")
# email log errors
bot_email = environ.get("EMAIL")
bot_password = environ.get("PASSWORD")
munis_endpoint = environ.get("MUNIS_ENDPOINT")

# Apply format to the log messages
formatter = "[{asctime}] [{name}] [{levelname}] - {message}"
logging.basicConfig(filename="logs/app.log", format=formatter, style="{")
logger = logging.getLogger()

# SMTP Mail handler settup
# mail_handler = SMTPHandler(
#     mailhost=("smtp.office365.com", 587),
#     fromaddr=bot_email,
#     toaddrs="dansmith@lawrenceks.org",
#     subject="eBuilder export error",
#     credentials=(bot_email, bot_password),
#     secure=(),
# )
# mail_handler.setFormatter(
#     logging.Formatter(
#         """
#     Message type:       %(levelname)s
#     Location:           %(pathname)s:%(lineno)d
#     Module:             %(module)s
#     Function:           %(funcName)s
#     Time:               %(asctime)s
#
#     Message:
#
#     %(message)s
#     """
#     )
# )
# mail_handler.setLevel(logging.ERROR)
# logger.addHandler(mail_handler)


# setting up logger
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


def get_project_details(project_code, token) -> str:
    """Get project details from Munis API"""
    proj_url = f"{munis_endpoint}munisopenapi/hosts/PL/odata/PL/v1/projectStrings?$filter=projectCode eq '{project_code}'"
    proj_payload = {}
    proj_headers = {"Accept": "application/json", "Authorization": "Bearer " + token}
    response = requests.request(
        "GET", proj_url, headers=proj_headers, data=proj_payload
    )
    response_body = json.loads(response.text)
    value = response_body["value"]
    return value["id"]


def get_updated_invoices_from_munis(invoices: list) -> list:
    """Checks munis for updated invoices"""
    invoice_numbers = [invoice['invoiceNumber'] for invoice in invoices]
    conn = pyodbc.connect(
        "Driver={ODBC Driver 11 for SQL Server};Server=CITYSQLDWH;Database=mun4907prod;",
        Trusted_Connection="yes",
    )
    cursor = conn.cursor()
    placeholders = ", ".join(["?"] * len(invoice_numbers))  # creates a list of '?' for each invoice number

    cursor.execute(
        f"""
    select
        invoices.id,
        Projects.Title,
        number,
        document,
        invoices.[status],
        invoices.InvoiceTotal,
        c.ContractNumber
    from Invoices
        left join Contracts c on c.id = Invoices.ContractId
        left join Projects on Projects.id = c.ProjectId
    where Document IN ({placeholders})
    """, invoice_numbers
    )

    return cursor.fetchall()


def update_ebuilder_invoices(ebuilder_invoices, munis_invoices) -> list:
    """Updates e-builder invoices"""
    for ebuilder_invoice in ebuilder_invoices:
        for munis_invoice in munis_invoices:
            if ebuilder_invoice["invoiceNumber"] == munis_invoice.document:
                if munis_invoice.status == "P":
                    # ebuilder_invoice["Status"] = "Paid"
                    print("Found a paid invoice")


def get_invoice_data(proj_id):
    """Get invoices for a project from Munis API"""
    inv_url = (
        munis_endpoint
        + "munisopenapi/hosts/PL/odata/PL/v1/projectStrings?$filter=projectCode eq '"
        + project_code
        + "'"
    )
    inv_payload = {}
    inv_headers = {"Accept": "application/json", "Authorization": "Bearer " + token}
    response = requests.request("GET", inv_url, headers=inv_headers, data=inv_payload)
    response_body = json.loads(response.text)
    invoices = response_body["value"]
    return invoices


# e-builder token refresh function
def get_ebuilder_token() -> str:
    url = f"{EB_API_BASE_URL}/Authenticate"
    payload = (
        f"grant_type=password&username={EB_API_USERNAME}&password={EB_API_PASSWORD}"
    )
    payload = payload.replace("@", "%40")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    if response.status_code != 200:
        logger.error("Error refreshing token")
        sys.exit(1)
    return json.loads(response.text)["access_token"]


def get_ebuilder_unpaid_commitment_invoices(token) -> list:
    """get a list of all commitments from e-builder"""
    response = requests.get(
        f"{EB_API_BASE_URL}/CommitmentInvoices",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 50, "offset": 0, "dateModified": "2023-05-17T09:41:55.992Z"},
    )
    if response.status_code != 200:
        logger.error("Error getting master invoices")
        sys.exit(1)

    invoices = []

    for invoice in response.json().get("records"):
        if invoice["status"] != "Paid":
            invoices.append(
                {
                    "invoiceStatus": invoice["status"],
                    "invoiceNumber": invoice["invoiceNumber"],
                    "lastModifiedDate": invoice["lastModifiedDate"],
                    "invoiceAmount": invoice["invoiceAmount"],
                }
            )

    return invoices


def get_munis_token():
    """Get Munis project ledger token"""
    response = requests.post(
        MUNIS_API_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "scope": MUNIS_API_SCOPES,
            "client_id": MUNIS_API_CLIENT_ID,
            "client_secret": MUNIS_API_CLIENT_SECRET,
        },
    )

    # raise error on non 200 responses
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("there was an error ", e)

    return response.json().get("access_token")


def get_train_token() -> str:
    url = "https://cityoflawrenceksforms-train.tylerhost.net/4907train/devportal/portal/api/clientCredential"
    payload = "grant_type=client_credentials&scope=munisOpenApiPOToolkit%20munisOpenApiPLToolkit%20tylerOpenApiServiceAccess"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://cityoflawrenceksforms-train.tylerhost.net/4907train/devportal/portal/open-api/collection",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "X-OpenApiDeveloperPortal-TokenEnpoint": "https://tyler-cityoflawrenceks.okta.com/oauth2/ausfis4bi0hkah3ES357/v1/token",
        "X-OpenApiDeveloperPortal-Client": munis_cred,
        "Origin": "https://cityoflawrenceksforms-train.tylerhost.net",
        "DNT": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-GPC": "1",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    # print(response)
    return response.json()["access_token"]


# functions to get Munis Data to send to e-builder


# Do I need to get the PO data or the project list string? Probably PO data?
# data probably need to connect back to a specific project
# set PO == contractNumber field in get request
def get_commitment_invoice_by_id(token):
    try:
        yesterday = date.today() - timedelta(days=1)
        response = requests.get(
            MUNIS_API_BASE_URL + "/PO/api/PO/v1/purchaseOrders",
            headers={"Accept": "application/json", "Authorization": "Bearer " + token},
            params={
                "$filter": "projectCode eq 'UT-1985 '",
            },
        )
        if response.status_code == 401:
            raise Exception("Unauthorized")

        print(response.status_code)
        print(response.text)
        # response = response.text

        column_names = {
            "Project Number": [],  # tied to contract
            "Invoice Number": [],  # Document number
            "Action": [],  # should be paid if it's coming through here, ask what other options there are
            "Date Paid": [],  # need to tie in disbursment info
            "Financials Amount": [],
            "Check Number": [],
            "Check Date": [],
            "Check Amount": [],
            "Vendor Invoice Number": [],  # Invoice number in Munis
        }
        df = pd.DataFrame(data=column_names)
        data = response.json()
        for record in data:
            """with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=4)"""
            # print(record.get("lastModifiedDate"))
            last_mod = record.get("lastModifiedDate")
            created = record.get("entryDate")
            # print(created)
            entry_date = parser.parse(created)
            # last modified date should still be checked incase there are updates to the project
            if last_mod != None:
                last_mod_date = parser.parse(last_mod)
                last_mod_date = last_mod_date.strftime("%Y-%m-%d")
                print(last_mod_date, yesterday)
                if last_mod_date == yesterday:
                    approval_date = ""
                    account_code = ""
                    if record["isApproved"]:
                        # get project string
                        purchaseOrderNum = record["purchaseOrderNumber"]
                        items = record["items"]
                        this_item = items[0]
                        allocations = this_item["allocations"]
                        lineNumber = this_item["lineNumber"]
                        this_allocation = allocations[0]
                        projectCode = this_allocation["projectCode"]
                        fullAccount = this_allocation["fullAccount"]
                        project_id = get_project_details(projectCode)
                        invoices = get_invoice_data(project_id)
                        # get approval date
                        # approval_date = projectString.approvalDate
                        tempdf = {
                            "Project Number": projectCode,
                            "Invoice Number": record["purchaseOrderNumber"],
                            # this should be the document number in Munis? Where is that?
                            "Action": record["status"],
                            "Date Paid": "",
                            # Need to find purchase order for each invoice, cannot locate foreign key to PO
                            "Financials Amount": this_item[
                                "total"
                            ],  # Is this the total amount?
                            "Check Number": "",
                            "Check Date": "",
                            "Check Amount": this_allocation["amount"],
                            "Vendor Invoice Number": "",  # Invoice number in Munis
                        }
                    new_df = pd.DataFrame([tempdf])
                    df = pd.concat([df, new_df], ignore_index=True)
            elif (
                entry_date.day == yesterday.day
            ):  # should be set to yesterday, checking to see if changes were made the day before
                approval_date = ""
                account_code = ""
                if record["isApproved"]:
                    # get project string
                    pprint.pprint(record)
                    purchaseOrderNum = record["purchaseOrderNumber"]
                    items = record["items"]
                    this_item = items[0]
                    allocations = this_item["allocations"]
                    lineNumber = this_item["lineNumber"]
                    this_allocation = allocations[0]
                    projectCode = this_allocation["projectCode"]
                    projectID = get_project_details(projectCode)
                    # get approval date
                    approval_date = ""

                    tempdf = {
                        "Project Number": projectCode,
                        "Invoice Number": purchaseOrderNum,
                        "Action": record["status"],  # second call to get details?
                        "Date Paid": "",  # if closed, get the receipt recieved date
                        "Financials Amount": this_item[
                            "total"
                        ],  # Is this the total amount?
                        "Check Number": "",
                        "Check Date": "",
                        "Check Amount": this_allocation["amount"],
                        "Vendor Invoice Number": "",  # Invoice number in Munis
                    }
                new_df = pd.DataFrame([tempdf])
                df = pd.concat([df, new_df], ignore_index=True)
                pprint.pprint(df)
        return df
    except Exception as e:
        raise e


"""
Order of operations:
- get list of purchase orders
- filter by changes made in last 24 hours
- get change order status 
value ID, old value, new value, changed

    "lastModifiedDate": "2022-10-25T20:14:59.056Z",
"""
# functions to get e-builder data to send to Munis

if __name__ == "__main__":
    ebuilder_token = get_ebuilder_token()
    print(ebuilder_token)
    ebuilder_invoices = get_ebuilder_unpaid_commitment_invoices(ebuilder_token)
    filtered_munis_invoices = get_updated_invoices_from_munis(ebuilder_invoices)
    updated_ebuilder_invoices = update_ebuilder_invoices(ebuilder_invoices, filtered_munis_invoices)
    print(updated_ebuilder_invoices)

    # munis_token = get_munis_token()
    # print(munis_token)
    # print(get_commitment_invoice_by_id(munis_token))
    # commitment_invoices = get_commitment_invoice_by_id(munis_token)
    # commitment_invoices.to_csv("CommitmentInvoicesUpdate.csv", index=False)
