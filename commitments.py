from config import CONFIG
import logging
import datetime
import pyodbc
import requests

from helpers import get_ebuilder_token
logger = logging.getLogger(__name__)


def get_ebuilder_commitments(token) -> list:
    """Gets commitments from eBuilder"""
    try:
        url = f"{CONFIG['EB_API_BASE_URL']}/commitments"
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 1000,
                    "offset": 0,
                    "dateModified": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=180)).isoformat().replace("+00:00", "Z")
                    },

        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        logger.error(err)
        raise SystemExit(err)
    except requests.exceptions.ConnectionError as err:
        logger.error(err)
        raise SystemExit(err)
    except requests.exceptions.Timeout as err:
        logger.error(err)
        raise SystemExit(err)
    except requests.exceptions.RequestException as err:
        logger.error(err)
        raise SystemExit(err)


def filter_commitments(commitments):
    """Filters commitments to only include those that are not approved"""
    filtered_commitments = []
    for commitment in commitments['records']:
        if commitment['status'] != 'Approved':
            filtered_commitments.append(commitment)
    return filtered_commitments


def get_approved_commitments_from_munis(commitments):
    """Gets approved commitments from Munis"""
    invoice_numbers: list = [invoice["invoiceNumber"] for invoice in invoices]
    conn = pyodbc.connect(
        "Driver={ODBC Driver 11 for SQL Server};Server=CITYSQLDWH;Database=mun4907prod;",
        Trusted_Connection="yes",
    )
    cursor = conn.cursor()
    query = f"""
        SELECT
            [Project Number]
            ,[Invoice Number]
            ,[Vendor Invoice Number]
            ,[Action]
            ,[Financials Amount]
            ,[Check Number]
            ,[Check Date]
            ,[Check Amount]
            ,[Date Paid]
            ,[Company Number]
        FROM [Munis].[dbo].[vwAPInvoices]
        WHERE [Project Number] IN ({','.join(commitments)})
    """
    cursor.execute(query)
    return cursor.fetchall()


if __name__ == "__main__":
    token = get_ebuilder_token()
    unfiltered_invoices = get_ebuilder_commitments(token)
    filtered_invoices = filter_commitments(unfiltered_invoices)
    x = [print(i["commitmentNumber"]) for i in filtered_invoices]