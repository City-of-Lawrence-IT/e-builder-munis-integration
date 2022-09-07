from get_innoprise_data import get_general_invoice_by_id

get_general_invoice_by_id(17157854).to_excel('GeneralInvoicesCreate.xlsx', index=False)

# old general invoice query
# SELECT
#                 p.projectno AS 'Project Number',
#                 i.invoice_no AS 'Invoice Number',
#                 REPLACE(i.longdescription,char(13) + char(10),',') as Description,
#                 vendor.vendornumber AS 'Company Number',
#                 i.status AS Action,
#                 CAST(i.duedate AS DATE) AS 'Date Approved',
#                 CAST(i.duedate AS DATE) AS 'Date Paid',
#                 lineitemallocation.amount AS 'Invoice Item Amount',
#                 -- l.storedtotal AS 'Invoice Item Amount',
#                 j.journalno AS 'Item Description',
#                 storedinvoicetotal AS 'Financials Amount',
#                 cheque.checkno AS 'Check Number',
#                 cheque.checkdate AS 'Check Date',
#                 cheque.amount AS 'Check Amount',
#                 '000-0000' AS 'Account Code',
#                 l.linenumber AS 'Item Number',
#                 i.vendorinvoiceno AS 'Vendor Invoice Number',
#                 g.seg4
#                 FROM [invoice] AS i
#                 JOIN vendor ON vendor.vendor_id = i.vendor_id
#                 LEFT JOIN cheque on i.check_id = cheque.check_id
#                 JOIN invoicelineitem l on l.invoice_id = i.invoice_id
#                 JOIN invoicelilialink on invoicelilialink.invoicelineitem_id = l.invoicelineitem_id
#                 JOIN lineitemallocation on lineitemallocation.lineitemallocation_id = invoicelilialink.lineitemalloc_id
#                 left join project AS p on lineitemallocation.projectno = p.projectno
#                 left join purchaseorder po on po.purchaseorder_id = i.purchaseorder_id
#                 left join (select top 1 * from gltx order by gltx_id desc) g on g.projectno = p.projectno
#                 left join journal j on j.journal_id = g.journal_id
#                 WHERE i.invoice_id = ?