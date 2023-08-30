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
    filter_commitments,
    export_commitments_to_excel,
)
from commitment_invoices import (
    get_ebuilder_unpaid_commitment_invoices,
    get_updated_invoices_from_munis,
    update_ebuilder_invoices,
    export_invoices_to_excel,
)

# Logging setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)

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


# Functions for authentication
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


def main():
    if CONFIG["COMMITMENT_INVOICES_ENABLED"]:
        logger.info("Running commitment invoices API integration")
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
        export_invoices_to_excel(
            invoice_exceptions, "CommitmentInvoicesExceptions.xlsx"
        )

    if CONFIG["COMMITMENTS_ENABLED"]:
        token = get_ebuilder_token()
        unfiltered_invoices = get_ebuilder_commitments(token)
        filtered_invoices = filter_commitments(token, unfiltered_invoices)
        #x = [print(i) for i in filtered_invoices]
        fake_commitment = [{
            "projectID": "fa4552de-1fd6-48a1-8c82-105925ffcd6e",
            "commitmentNumber": "22300470",
            "currentCommitmentValue": 29740.0,

        }]

        updated_commitments = get_approved_commitments_from_munis(
            token, fake_commitment
        )
        print(updated_commitments)
        #export_commitments_to_excel(updated_commitments, "CommitmentsUpdate.xlsx")
        # print(filtered_invoices)
        # print(get_ebuilder_project_from_id(token, '2e6d7b04-e966-4e7d-89f3-d926b4b8594f'))


if __name__ == "__main__":
    main()
