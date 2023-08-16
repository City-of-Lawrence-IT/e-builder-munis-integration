import json
import logging
from logging.handlers import SMTPHandler
import requests

from config import CONFIG
from helpers import get_ebuilder_token
from commitments import (
    get_ebuilder_commitments,
    get_ebuilder_project_from_id,
    get_approved_commitments_from_munis,
)
from commitment_invoices import (
    get_ebuilder_unpaid_commitment_invoices,
    get_updated_invoices_from_munis,
    update_ebuilder_invoices,
    export_invoices_to_excel,
)

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
