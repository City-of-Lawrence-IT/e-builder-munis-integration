import json
import logging
from logging.handlers import SMTPHandler
import requests
import sys

import pandas as pd
import pyodbc

from config import CONFIG
from helpers import get_ebuilder_token

# Logging setup
logger = logging.getLogger(__name__)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("logs/app.log")
file_handler.setLevel(logging.ERROR)

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d %(message)s"
)
stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# SMTP Mail handler setup
mail_handler = logging.handlers.SMTPHandler(
    mailhost=("smtp.office365.com", 587),
    fromaddr=CONFIG["LOGGER_EMAIL"],
    toaddrs="ngodfrey@lawrenceks.org",
    subject="eBuilder export error",
    credentials=(CONFIG["LOGGER_EMAIL"], CONFIG["LOGGER_PASS"]),
    secure=(),
)
mail_handler.setFormatter(
    logging.Formatter(
        """
    Message type:       %(levelname)s
    Location:           %(pathname)s:%(lineno)d
    Module:             %(module)s
    Function:           %(funcName)s
    Time:               %(asctime)s

    Message:

    %(message)s
    """
    )
)
mail_handler.setLevel(logging.ERROR)


logger.addHandler(stream_handler)
logger.addHandler(file_handler)

if CONFIG["ENVIRONMENT"] == "PROD":
    logger.addHandler(mail_handler)

def get_updated_invoices_from_munis(invoices: list) -> list:
    """Checks munis for updated invoices"""
    logger.info("Checking Munis for updated invoices")
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
        Invoices.Number AS 'Vendor Invoice Number',
        invoices.[status],
        invoices.InvoiceTotal AS 'Financials Amount',
        -- c.ContractNumber,
        Invoices.CheckNumber AS 'Check Number',
        Checks.CheckDate AS 'Check Date',
        Checks.CheckAmount AS 'Check Amount',
        Checks.CheckDate AS 'Date Paid',
        Vendors.VendorNumber AS 'Company Number'
    FROM Invoices
        LEFT JOIN Contracts c ON c.id = Invoices.ContractId
        LEFT JOIN Projects ON Projects.id = c.ProjectId
        LEFT JOIN Checks on Checks.CheckNumber = Invoices.CheckNumber
        LEFT JOIN Vendors on Vendors.id = Invoices.VendorId
    WHERE Document IN ({placeholders})
    AND Invoices.CheckNumber != 0
    """,
        invoice_numbers,
    )

    return cursor.fetchall()


def update_ebuilder_invoices(eb_invoices: list, munis_invoices: list) -> (list, list):
    """Updates e-builder invoices"""
    logger.info("Updating e-builder invoices")
    updated_invoices: list[dict] = []
    inv_exceptions: list[dict] = []
    for ebuilder_invoice in eb_invoices:
        for munis_invoice in munis_invoices:
            if ebuilder_invoice["invoiceNumber"] == munis_invoice[1]:
                munis_invoice.status = "Paid"
                if munis_invoice[0] == None:
                    # no project number found in munis
                    inv_exceptions.append(munis_invoice)
                else:
                    updated_invoices.append(munis_invoice)
    return updated_invoices, inv_exceptions


def export_invoices_to_excel(invoices: list, filename: str) -> None:
    """Exports updated invoices list to excel using pandas"""
    logger.info("Exporting invoices to excel")
    df = pd.DataFrame(
        (tuple(invoice) for invoice in invoices),
        columns=[
            "Project Number",
            "Invoice Number",
            "Vendor Invoice Number",
            "Action",
            "Financials Amount",
            "Check Number",
            "Check Date",
            "Check Amount",
            "Date Paid",
            "Company Number",
        ],
    )
    df.to_excel(filename, index=False)


def get_ebuilder_unpaid_commitment_invoices(token) -> list:
    """get a list of all commitments from e-builder"""
    logger.info("Getting master invoices from e-builder")
    response = requests.get(
        f"{CONFIG['EB_API_BASE_URL']}/CommitmentInvoices",
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
        CONFIG["MUNIS_API_TOKEN_URL"],
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "scope": CONFIG["MUNIS_API_SCOPES"],
            "client_id": CONFIG["MUNIS_API_CLIENT_ID"],
            "client_secret": CONFIG["MUNIS_API_CLIENT_SECRET"],
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


def main():
    ebuilder_token = get_ebuilder_token()
    ebuilder_invoices = get_ebuilder_unpaid_commitment_invoices(ebuilder_token)
    print(ebuilder_invoices)
    filtered_munis_invoices = get_updated_invoices_from_munis(ebuilder_invoices)
    updated_ebuilder_invoices, invoice_exceptions = update_ebuilder_invoices(
        ebuilder_invoices, filtered_munis_invoices
    )
    print(updated_ebuilder_invoices)
    # this will go into the ftp folder to be picked up by e-builder
    # \\citydata\MFT\ebuilder\CommitmentInvoices
    export_invoices_to_excel(
        updated_ebuilder_invoices,
        "//citydata/MFT/ebuilder/CommitmentInvoices/CommitmentInvoicesUpdate.xlsx",
    )
    #  this will need to be emailed to the finance team
    export_invoices_to_excel(invoice_exceptions, "CommitmentInvoicesExceptions.xlsx")


if __name__ == "__main__":
    main()
    pass
