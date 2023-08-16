from config import CONFIG
import logging
import datetime
import pyodbc
import requests
import pandas as pd

from helpers import get_ebuilder_token

logger = logging.getLogger(__name__)
print(logger)


def get_ebuilder_unpaid_commitment_invoices(token) -> list:
    """get a list of all commitments from e-builder"""
    logger.info("Getting invoices from e-builder")
    response = requests.get(
        f"{CONFIG['EB_API_BASE_URL']}/CommitmentInvoices",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 500, "offset": 0, "dateModified": "2023-05-17T09:41:55.992Z"},
    )
    if response.status_code != 200:
        logger.error("Error getting master invoices")
        raise ConnectionError

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
