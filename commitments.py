from config import CONFIG
import logging
import datetime
import pyodbc
import requests
import pandas as pd

logger = logging.getLogger(__name__)


def get_ebuilder_commitments(token) -> list:
    """Gets commitments from eBuilder"""
    logger.info("Getting commitments from eBuilder")
    try:
        url = f"{CONFIG['EB_API_BASE_URL']}/commitments"
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "limit": 1000,
                "offset": 0,
                "dateModified": (
                    datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=180)
                )
                .isoformat()
                .replace("+00:00", "Z"),
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


def get_ebuilder_project_from_id(token, project_id: str) -> str:
    """Gets project from eBuilder"""
    try:
        url = f"{CONFIG['EB_API_BASE_URL']}/projects/{project_id}/customfields"
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        for item in response.json()["details"]:
            if item["name"] == "Project Number":
                return item["value"]
        return ""
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


def filter_commitments(token, commitments):
    """Filters commitments to only include those that are not approved"""
    logger.info("Filtering commitments")
    filtered_commitments = []
    for commitment in commitments["records"]:
        if commitment["status"] != "Approved":
            filtered_commitments.append(commitment)
    return filtered_commitments


def calculate_commitment_total(commitments):
    """Calculates the total of a commitment"""
    totaled_commitments = []
    # set the current commitment to the first commitment
    current_commitment = commitments[0]
    total = 0
    for commitment in commitments:
        if commitment[0] != current_commitment[0]:
            # new commitment
            totaled_commitments.append(
                (
                    commitment[0],
                    commitment[1],
                    total,
                )
            )
            current_commitment = commitment[0]
            total = commitment[3] * commitment[4]
        else:
            total += commitment[3] * commitment[4]

    totaled_commitments.append(
        (
            commitment[0],
            commitment[1],
            total,
        )
    )
    return totaled_commitments


def get_approved_commitments_from_munis(token, commitments):
    """Gets approved commitments from Munis"""
    commitment_list = []
    for commitment in commitments:
        # check if commitment number is an int
        if not commitment["commitmentNumber"].isdigit():
            continue

        commitment_list.append(
            (
                get_ebuilder_project_from_id(token, commitment["projectID"]),
                commitment["commitmentNumber"].strip(),
                "",
                commitment["currentCommitmentValue"],
                commitment["commitmentNumber"].strip(),
            )
        )
    print(f"Comitment list: {commitment_list}")
    commitment_numbers = ",".join([str(c[1]) for c in commitment_list])

    updated_commitments: list = []
    conn = pyodbc.connect(
        "Driver={ODBC Driver 11 for SQL Server};Server=CITYSQLDWH;Database=mun4907prod;",
        Trusted_Connection="yes",
    )
    cursor = conn.cursor()
    logger.info("Checking contracts in Munis")
    # print(commitment_list)
    query = f"""
        SELECT
            max(Description),
            max(ApprovedDate),
            max(ContractNumber),
            max(Status),
            SUM(CAL.revisedAmount) AS CommitmentAmount
        FROM [mun4907prod].[dbo].[Contracts]
        left join ContractAmountLines CAL on Contracts.Id = CAL.ContractId
        WHERE ContractNumber IN ({commitment_numbers})
        GROUP BY ContractNumber
    """
    cursor.execute(query)
    results = cursor.fetchall()
    for row in results:
        for commitment in commitment_list:
            if row[2].strip() == commitment[1]:
                if row[3].strip() == "8":
                    logger.info("Found an updated commitment")
                    updated_commitments.append(
                        (
                            commitment[0],
                            commitment[1],
                            "Approved",
                            row[4],
                            0,
                        )
                    )
                else:
                    if row[3] == "0":
                        # untested
                        logger.info("Found a rejected commitment")
                        updated_commitments.append(
                            (
                                commitment[0],
                                commitment[1],
                                "Void",
                                row[4],
                                0,
                            )
                        )

    logger.info("Checking Purchase Orders in Munis")
    query = f"""
                SELECT 
              p.[PurchaseOrderNumber]
              ,[Status]
              ,r.TotalAmount
              ,poi.UnitPrice
              ,poi.Quantity
          FROM [mun4907prod].[dbo].[PurchaseOrders] p
          LEFT JOIN Requisitions r ON r.PurchaseOrderNumber = p.PurchaseOrderNumber
          LEFT JOIN PurchaseOrderItems poi ON poi.PurchaseOrderId = p.id
        WHERE p.PurchaseOrderNumber IN ({commitment_numbers})
    """
    cursor.execute(query)
    logger.debug(f"query: {query}")
    results = cursor.fetchall()
    # print(cursor.fetchall())

    if results:
        totaled_commitments = calculate_commitment_total(results)
    else:
        totaled_commitments = []

    for row in totaled_commitments:
        for commitment in commitment_list:
            if str(row[0]) == commitment[1]:
                if row[1] == "8":
                    logger.info("Found an updated commitment")
                    updated_commitments.append(
                        (
                            commitment[0],
                            commitment[1],
                            "Approved",
                            row[2],
                            0,
                        )
                    )
                else:
                    if row[3] == "0":
                        # untested
                        logger.info("Found a rejected commitment")
                        updated_commitments.append(
                            (
                                commitment[0],
                                commitment[1],
                                "Void",
                                row[4],
                                0,
                            )
                        )

    return updated_commitments


def export_commitments_to_excel(commitments: list, filename: str) -> None:
    """Exports commitments to excel"""
    logger.info("Exporting commitments to excel")
    df = pd.DataFrame(
        (tuple(c) for c in commitments),
        columns=[
            "Project Number",
            "Commitment Number",
            "Action",
            "Financials Amount",
            "PO Number",
        ],
    )
    df.to_excel(filename, index=False)
