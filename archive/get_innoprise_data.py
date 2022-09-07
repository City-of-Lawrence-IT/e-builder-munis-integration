import sys
import pyodbc
from datetime import timedelta, date
import logging
from logging.handlers import SMTPHandler

import pandas as pd

# setup logging
logger = logging.getLogger('ebuilder_integration_logger')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

file_logger = logging.FileHandler('test.log')
file_logger.setLevel(logging.DEBUG)

# error_logger = SMTPHandler('10.1.1.25', 'ngodfrey@lawrenceks.org', 'ngodfrey@lawrenceks.org', 'Error')
# error_logger.setLevel(logging.ERROR)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d %(message)s')
ch.setFormatter(formatter)
file_logger.setFormatter(formatter)
# error_logger.setFormatter(formatter)

logger.addHandler(ch)
logger.addHandler(file_logger)

# logger.addHandler(error_logger)


# noinspection PyUnusedLocal
def error_handler(error_type, error_value, trace_back):
    print(trace_back)
    logger.exception('Uncaught exception: {}'.format(str(error_value)))


sys.excepthook = error_handler


# noinspection SqlResolve
def get_updated_rows(day):
    """
    gets yesterdays updated ebuilder data from innoprise audit table
    :param day: end date of query
    :return: list of rows
    """
    yesterday = day - timedelta(days=1)
    conn = pyodbc.connect(r'DRIVER={SQL Server Native Client 11.0};SERVER=INDB;DATABASE=col;',
                          trusted_connection='yes')
    cursor = conn.cursor()
    cursor.execute(""" SELECT [table_name]
                                  ,[value_id]
                                  ,[old_value]
                                  ,[new_value]
                                  ,[changed]
                              FROM finchangelog
                              WHERE changed between ? and ? """, [yesterday, day])

    return cursor.fetchall()


def get_commitment_invoice_by_id(c_invoice_id: int):
    conn = pyodbc.connect(r'DRIVER={SQL Server Native Client 11.0};SERVER=INDB;DATABASE=innofin;',
                          trusted_connection='yes')
    df = pd.read_sql("""
        SELECT project.projectno AS 'Project Number', 
        i.[invoice_no] AS 'Invoice Number',
        i.[status], 
        CAST(posteddate AS DATE) AS 'Date Paid',
        storedinvoicetotal AS 'Financials Amount',
        cheque.checkno AS 'Check Number',
        cheque.checkdate AS 'Check Date',
        cheque.amount AS 'Check Amount',
        i.vendorinvoiceno AS 'Vendor Invoice Number'
          FROM [invoice] AS i
          INNER JOIN invoicelineitem on invoicelineitem.invoice_id = i.invoice_id
          INNER JOIN invoicelilialink on invoicelilialink.invoicelineitem_id = invoicelineitem.invoicelineitem_id
          INNER JOIN lineitemallocation on invoicelilialink.lineitemalloc_id = lineitemallocation.lineitemallocation_id
          INNER JOIN project on project.projectno = lineitemallocation.projectno
          LEFT JOIN cheque on i.check_id = cheque.check_id
          WHERE i.invoice_id = ?""",
                     conn, params=[c_invoice_id])
    df.insert(2, 'Action', ['Paid' if _ == 'PAID' else 'Void' for _ in df['status']])
    del df['status']
    return df


def get_yesterday_general_invoices(day):
    """This will only get Adjustments"""
    end_day = day + timedelta(days=1)
    conn = pyodbc.connect(r'DRIVER={SQL Server Native Client 11.0};SERVER=INDB;DATABASE=innofin;',
                          trusted_connection='yes')
    df = pd.read_sql("""  
        SELECT  
        p.projectno AS 'Project Number',
        CASE WHEN gltx.debit = 0 then '-' + CONVERT(varchar, CONVERT(money, gltx.amount), 1) 
            ELSE CONVERT(varchar, CONVERT(money, gltx.amount), 1) END AS 'Invoice Item Amount',
        j.journalno AS 'Item Description'
        FROM JOURNAL J
        JOIN GLTX on GLTX.journal_id = j.journal_id
        JOIN project P on p.projectno = gltx.projectno
        JOIN glaccount ga on ga.account_id = gltx.account_id
        LEFT OUTER JOIN invoice i on i.invoice_id = gltx.invoice_id
        LEFT JOIN vendor ON i.vendor_id = vendor.vendor_id
        LEFT OUTER JOIN purchaseorder po on po.purchaseorder_id = gltx.purchaseorder_id
        JOIN projectattributelink on projectattributelink.project_id = p.project_id
        JOIN attributeinstance on attributeinstance.attributeinstance_id = projectattributelink.attribute_id
        WHERE attributeinstance.attribute_id = 15759781
        and j.journaltype = 'ACT'
        AND j.timestamp between ? AND ?
        AND i.status is NULL
        and ga.seg2 <> 0
        and po.purchaseordernumber is null
        AND gltx.seg4 not between 8100 and 8199
        AND gltx.seg4 <> 7700
        AND j.posted = 1
        and amount != 0
        ORDER BY j.journalno
        """, conn, params=[day, end_day])
    date_text = day.strftime("%Y-%m-%d")
    # create list of invoice numbers with the following format INV{YYYY}{MM}{DD}.{n}
    invoice_list = ['INV' + day.strftime("%Y%m%d") + '.' + str(x + 1) for x, _ in enumerate(range(len(df)))]
    df.insert(1, 'Invoice Number', invoice_list)  # add invoice number to all general Invoices
    df.insert(2, 'Description', invoice_list)  # add invoice number to all general Invoices
    df.insert(3, 'Company Number', ['000000' for _ in range(len(df))])  # add company number to all general Invoices
    df.insert(4, 'Action', ['Paid' for _ in range(len(df))])  # add Paid to all general Invoices
    df.insert(5, 'Date Approved', [date_text for _ in range(len(df))])  # add DateReceived number to all g Invoices
    df.insert(6, 'Date Paid', [date_text for _ in range(len(df))])  # add DateDue number to all general Invoices
    df.insert(8, 'Account Code', ['000-0000' for _ in range(len(df))])  # add Account Code number to all g Invoices
    df.insert(9, 'Item Number', ['1' for _ in range(len(df))])  # add ItemNumber number to all general Invoices

    return df


def get_general_invoice_by_id(gi_id):
    conn = pyodbc.connect(r'DRIVER={SQL Server Native Client 11.0};SERVER=INDB;DATABASE=innofin;',
                          trusted_connection='yes')
    df = pd.read_sql("""SELECT * FROM (
                SELECT		
                --i.invoice_id,
                max(p.projectno) AS 'Project Number',
                max(i.invoice_no) AS 'Invoice Number',
                max(REPLACE(i.longdescription,char(13) + char(10),',')) as Description,
                max(vendor.vendornumber) AS 'Company Number',
                max(i.status) AS Action,
                max(CAST(i.duedate AS DATE)) AS 'Date Approved',
                max(CAST(i.duedate AS DATE)) AS 'Date Paid',
                max(lineitemallocation.amount) AS 'Invoice Item Amount',
                -- l.storedtotal AS 'Invoice Item Amount',
                --j.journalno AS 'Item Description',
                max(storedinvoicetotal) AS 'Financials Amount',
                max(cheque.checkno) AS 'Check Number',
                max(cheque.checkdate) AS 'Check Date',
                max(cheque.amount) AS 'Check Amount',
                '000-0000' AS 'Account Code',
                max(l.linenumber) AS 'Item Number',
                max(i.vendorinvoiceno) AS 'Vendor Invoice Number',
                max(g.seg4) as seg4
                FROM [invoice] AS i
                JOIN vendor ON vendor.vendor_id = i.vendor_id
                LEFT JOIN cheque on i.check_id = cheque.check_id
                JOIN invoicelineitem l on l.invoice_id = i.invoice_id
                JOIN invoicelilialink on invoicelilialink.invoicelineitem_id = l.invoicelineitem_id
                JOIN lineitemallocation on lineitemallocation.lineitemallocation_id = invoicelilialink.lineitemalloc_id
                left join project AS p on lineitemallocation.projectno = p.projectno
                left join purchaseorder po on po.purchaseorder_id = i.purchaseorder_id
                left join gltx g on g.invoice_id = i.invoice_id
                left join journal j on j.journal_id = g.journal_id
                WHERE i.invoice_id = ?
                group by lineitemallocation.amount) as x 
                WHERE x.seg4 not between '8100' AND '8199'
                 """, conn, params=[gi_id])

    return df


def get_vendor_by_id(vendor_id):
    conn = pyodbc.connect(r'DRIVER={SQL Server Native Client 11.0};SERVER=INDB;DATABASE=innofin;',
                          trusted_connection='yes')
    df = pd.read_sql("""
                SELECT vendor.vendornumber AS 'Company Number', 
                vendor.[name] AS 'Company Name', 
                addr1 AS Address,
                City, [State], Zip
                FROM [address]
                JOIN vendor on vendor.address_id = address.address_id
                WHERE vendor.vendor_id = ?
                """, conn, params=[vendor_id])
    df.insert(2, 'Country', ['' for _ in range(len(df))])  # add Country to all vendors
    df.insert(7, 'Active', ['' for _ in range(len(df))])  # add Active to all vendors
    df.insert(8, 'MasterCompany Name', ['' for _ in range(len(df))])  # add MC name to all vendors
    return df


def get_vendor_by_address_id(address_id):
    conn = pyodbc.connect(r'DRIVER={SQL Server Native Client 11.0};SERVER=INDB;DATABASE=innofin;',
                          trusted_connection='yes')
    df = pd.read_sql("""
                SELECT vendor.vendornumber AS 'Company Number', 
                vendor.[name] AS 'Company Name', 
                addr1 AS Address,
                City, [State], Zip
                FROM [address]
                JOIN vendor on vendor.address_id = address.address_id
                where address.address_id = ?
                """, conn, params=[address_id])
    df.insert(2, 'Country', ['' for _ in range(len(df))])  # add Country to all vendors
    df.insert(7, 'Active', [1 for _ in range(len(df))])  # add Active to all vendors
    df.insert(8, 'MasterCompany Name', ['' for _ in range(len(df))])  # add MC name to all vendors
    return df


def get_requisition_by_id(requisition_id):
    conn = pyodbc.connect(r'DRIVER={SQL Server Native Client 11.0};SERVER=INDB;DATABASE=innofin;',
                          trusted_connection='yes')
    df = pd.read_sql("""
            SELECT  
            project.projectno AS 'Project Number',
            r.requisitionno AS 'Commitment Number', 
            r.approvalstatus,
            storedpototal AS 'Financials Amount',
            -- state.description AS StateDesc,
            p.purchaseordernumber AS 'PO Number'
            FROM requisition AS r
            INNER JOIN requisitionlineitem ON r.requisition_id = requisitionlineitem.requisition_id 
            INNER JOIN reqlilialink ON requisitionlineitem.requisitionlineitem_id = reqlilialink.reqlineitem_id 
            INNER JOIN lineitemallocation ON reqlilialink.lineitemalloc_id = lineitemallocation.lineitemallocation_id 
            INNER JOIN project ON lineitemallocation.projectno = project.projectno
            LEFT JOIN purchaseorder AS p on p.requisition_id = r.requisition_id
            INNER JOIN state ON r.state_id = state.state_id 
            WHERE r.requisition_id = ?""", conn, params=[requisition_id])
    conn.close()

    # add DateDue number to all general Invoices ↓
    df.insert(2, 'Action', ['Approved' if _ == 'ISSUED' else 'Void' for _ in df['approvalstatus']])
    del df['approvalstatus']
    return df


def main():
    # create the empty df's
    vendor_df = pd.DataFrame()
    general_invoices_df = pd.DataFrame()
    commitment_df = pd.DataFrame()
    commitment_invoice_df = pd.DataFrame()

    # query new changes
    try:
        # query_date = date(2019, 9, 18)
        query_date = date.today()
        changed_records = get_updated_rows(query_date)
        # print(changed_records)
    except pyodbc.OperationalError as e:
        logger.exception(e)
        changed_records = []

    for row in changed_records:

        if row.table_name == 'requisition':
            if row.new_value == 'ISSUED' or row.new_value == 'CANCELLED':  # these should be the only values
                commitment_df = commitment_df.append(get_requisition_by_id(row.value_id), ignore_index=True)
            else:
                logger.debug('Trigger Debug: The commitment is not issued or canceled, invoice id: {}'
                             .format(row.value_id))
        elif row.table_name == 'generalInvoice':
            if row.new_value == 'PAID':
                # this extra check is probably not needed.
                general_invoices_df = general_invoices_df.append(get_general_invoice_by_id(row.value_id),
                                                                 ignore_index=True)
            else:
                logger.debug('Trigger Debug: The invoice is not paid, invoice id: {}'.format(row.value_id))
        elif row.table_name == 'VendorAddress':
            vendor_df = vendor_df.append(get_vendor_by_address_id(row.value_id), ignore_index=True)
        elif row.table_name == 'CommitmentInvoice':
            if row.new_value == 'PAID':
                # we only want paid
                commitment_invoice_df = commitment_invoice_df.append(get_commitment_invoice_by_id(row.value_id),
                                                                     ignore_index=True)
        elif row.table_name == 'Vendor':
            vendor_df = vendor_df.append(get_vendor_by_id(row.value_id), ignore_index=True)
        else:
            # this should never run
            logger.error('This should never run row: {}'.format(row))

    # add the adjustments from yesterday
    yesterday = date.today() - timedelta(days=1)
    general_invoices_df = general_invoices_df.append(get_yesterday_general_invoices(yesterday),
                                                     ignore_index=True, sort=False)

    # this will append a number to any duplicate invoice numbers in the general invoice df

    # first count the number of dupes and add that to a new temp df
    if not general_invoices_df.empty:
        c = general_invoices_df.groupby(["Invoice Number"]).cumcount()
    else:
        c = pd.DataFrame()

    # function that adds a dash to the values given it
    def add_dash(value):
        return '-' + str(value)

    # add dashes
    c = c.apply(add_dash)
    # delete zero dashes
    c = c.replace('-0', '').astype(str)
    # append dashes to invoice number
    if not general_invoices_df.empty:
        general_invoices_df["Invoice Number"] += c

    try:
        general_invoices_df.to_excel(
            f'//citydata/public/MSO_Engr/e-Builder Admin/Integration/GA/{date.today().strftime("%Y-%m-%d")}_GeneralInvoicesCreate.xlsx',
                                     index=False)
    except FileNotFoundError as e:
        logger.error('Error saving general invoices - {}'.format(e))
    except PermissionError as e:
        logger.error('I do not have permissions to write to that file, it may be opened by someone or locked - {}'
                     .format(e))

    try:
        vendor_df.to_excel('//citydata/FTP/outgoing/ebuilder/Companies/CompaniesCreate.xlsx', index=False)
    except FileNotFoundError as e:
        logger.error('Error saving vendors - {}'.format(e))
    except PermissionError as e:
        logger.error('I do not have permissions to write to that file, it may be opened by someone or locked - {}'
                     .format(e))

    try:
        commitment_df.to_excel('//citydata/FTP/outgoing/ebuilder/Commitments/CommitmentsUpdate.xlsx', index=False)
    except FileNotFoundError as e:
        logger.error('Error saving commitments - {}'.format(e))
    except PermissionError as e:
        logger.error('I do not have permissions to write to that file, it may be opened by someone or locked - {}'
                     .format(e))

    try:
        commitment_invoice_df.to_excel(
            '//citydata/FTP/outgoing/ebuilder/CommitmentInvoices/CommitmentInvoicesUpdate.xlsx',
            index=False)
    except FileNotFoundError as e:
        logger.error('Error saving commitment invoices - {}'.format(e))
    except PermissionError as e:
        logger.error('I do not have permissions to write to that file, it may be opened by someone or locked - {}'
                     .format(e))


if __name__ == '__main__':
    # print(get_commitment_invoice_by_id(19822329))
    main()
