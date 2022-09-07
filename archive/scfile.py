"""SELECT top 1
                p.projectno AS 'Project Number',
                i.invoice_no AS 'Invoice Number',
                REPLACE(i.longdescription,char(13) + char(10),',') as Description,
                vendor.vendornumber AS 'Company Number',
                i.status AS Action,
                CAST(i.duedate AS DATE) AS 'Date Approved',
                CAST(i.duedate AS DATE) AS 'Date Paid',
                i.storedinvoicetotal AS 'Invoice Item Amount',
                j.journalno AS 'Item Description',
                storedinvoicetotal AS 'Financials Amount',
                cheque.checkno AS 'Check Number',
                cheque.checkdate AS 'Check Date',
                cheque.amount AS 'Check Amount'
                FROM JOURNAL J
                JOIN GLTX on GLTX.journal_id = j.journal_id
                JOIN project P on p.projectno = gltx.projectno
                JOIN glaccount ga on ga.account_id = gltx.account_id
                LEFT OUTER JOIN invoice i on i.invoice_id = gltx.invoice_id
                LEFT JOIN cheque on i.check_id = cheque.check_id
                JOIN vendor ON vendor.vendor_id = i.vendor_id
                LEFT OUTER JOIN purchaseorder po on po.purchaseorder_id = gltx.purchaseorder_id
                WHERE i.invoice_id = ?"""
