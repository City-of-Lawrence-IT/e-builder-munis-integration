from dotenv import load_dotenv
import json
import logging
import pprint
import requests
import sys
from datetime import timedelta, date
from os import environ

import pandas as pd
import pyodbc
from dateutil import parser
from dotenv import load_dotenv

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


def get_updated_invoices_from_munis(invoices: list) -> list:
    """Checks munis for updated invoices"""
    invoice_numbers: list = [invoice["invoiceNumber"] for invoice in invoices]
    conn = pyodbc.connect(
        "Driver={ODBC Driver 11 for SQL Server};Server=CITYSQLDWH;Database=mun4907prod;",
        Trusted_Connection="yes",
    )
    cursor = conn.cursor()
    placeholders = ", ".join(
        ["?"] * len(invoice_numbers)
    )  # creates a list of '?' for each invoice number

    cursor.execute(
        f"""
    SELECT
        -- invoices.id,
        Projects.ProjectCode AS 'Project Number',
        document AS 'Invoice Number',
        invoices.[status],
        invoices.InvoiceTotal AS 'Financials Amount',
        -- c.ContractNumber,
        Invoices.CheckNumber AS 'Check Number',
        Checks.CheckDate AS 'Check Date',
        Checks.CheckAmount AS 'Check Amount',
        Checks.CheckDate AS 'Date Paid'
        -- Checks.IsCleared AS 'IsCleared'
    FROM Invoices
        LEFT JOIN Contracts c ON c.id = Invoices.ContractId
        LEFT JOIN Projects ON Projects.id = c.ProjectId
        LEFT JOIN Checks on Checks.CheckNumber = Invoices.CheckNumber
    WHERE Document IN ({placeholders})
    AND Invoices.CheckNumber != 0
    """,
        invoice_numbers,
    )

    return cursor.fetchall()


def update_ebuilder_invoices(eb_invoices: list, munis_invoices: list) -> list:
    """Updates e-builder invoices"""
    updated_invoices: list[dict] = []
    for ebuilder_invoice in eb_invoices:
        for munis_invoice in munis_invoices:
            if ebuilder_invoice["invoiceNumber"] == munis_invoice[1]:
                munis_invoice.status = 'Paid'
                updated_invoices.append(munis_invoice)
    return updated_invoices


def export_invoices_to_excel(invoices: list) -> None:
    """Exports updated invoices list to excel using pandas"""
    df = pd.DataFrame(
        (tuple(invoice) for invoice in invoices),
        columns=[
            "Project Number",
            "Invoice Number",
            "Action",
            "Financials Amount",
            "Check Number",
            "Check Date",
            "Check Amount",
            "Date Paid",
        ],
    )
    df.to_excel("updated_invoices.xlsx", index=False)



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
        params={"limit": 500, "offset": 0, "dateModified": "2023-05-17T09:41:55.992Z"},
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
                    "datePaid": invoice["datePaid"],
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



# functions to get Munis Data to send to e-builder


# Do I need to get the PO data or the project list string? Probably PO data?
# data probably need to connect back to a specific project
# set PO == contractNumber field in get request

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
    # print(ebuilder_token)
    ebuilder_invoices = get_ebuilder_unpaid_commitment_invoices(ebuilder_token)
    # print(ebuilder_invoices)
    filtered_munis_invoices = get_updated_invoices_from_munis(ebuilder_invoices)
    print(filtered_munis_invoices)
    updated_ebuilder_invoices = update_ebuilder_invoices(
        ebuilder_invoices, filtered_munis_invoices
    )
    print(updated_ebuilder_invoices)
    export_invoices_to_excel(updated_ebuilder_invoices)


    # munis_token = get_munis_token()
    # print(munis_token)
    # print(get_commitment_invoice_by_id(munis_token))
    # commitment_invoices = get_commitment_invoice_by_id(munis_token)
    # commitment_invoices.to_csv("CommitmentInvoicesUpdate.csv", index=False)
