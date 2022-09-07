# Generic/Built-in
from datetime import date, timedelta
# Other Libs
import pyodbc
import pandas as pd
# Owned

from get_innoprise_data import *

__author__ = "ngodfrey"
__copyright__ = "Copyright 2020"

"""
"""

# Change These
START_DATE = date(2021, 7, 29)
END_DATE = date(2021, 7, 31)


number_of_days = END_DATE - START_DATE
vendor_df = pd.DataFrame()
general_invoices_df = pd.DataFrame()
commitment_df = pd.DataFrame()
commitment_invoice_df = pd.DataFrame()

# plus one to get the first and last day of range
for offset in range(number_of_days.days + 1):
    query_date = END_DATE - timedelta(days=offset)
    print(query_date)
    changed_records = get_updated_rows(query_date)
    for row in changed_records:
        print(row)
    # print(changed_records)
    if len(changed_records) > 0:
        for row in changed_records:

            if row.table_name == 'requisition':
                if row.new_value == 'ISSUED' or row.new_value == 'CANCELLED':  # these should be the only values
                    commitment_df = commitment_df.append(get_requisition_by_id(row.value_id), ignore_index=True)
                else:
                    print('Trigger Debug: The commitment is not issued or canceled, invoice id: {}'
                                 .format(row.value_id))
            elif row.table_name == 'generalInvoice':
                if row.new_value == 'PAID':
                    # this extra check is probably not needed.
                    general_invoices_df = general_invoices_df.append(get_general_invoice_by_id(row.value_id),
                                                                     ignore_index=True)
                else:
                    print('Trigger Debug: The invoice is not paid, invoice id: {}'.format(row.value_id))
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
                print('This should never run row: {}'.format(row))

    yesterday = END_DATE - timedelta(days=offset)
    # general_invoices_df = general_invoices_df.append(get_yesterday_general_invoices(yesterday),
    #                                                  ignore_index=True, sort=False)
    # print(get_yesterday_general_invoices(yesterday))
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

# for row in general_invoices_df.iteritems():
#    print(row)
print(commitment_df)
general_invoices_df.to_excel('temp/GeneralInvoicesCreate.xlsx', index=False)
commitment_df.to_excel('temp/CommitmentsUpdate.xlsx', index=False)
commitment_invoice_df.to_excel('temp/CommitmentInvoicesUpdate.xlsx', index=False)
vendor_df.to_excel('temp/CompaniesCreate.xlsx', index=False)
