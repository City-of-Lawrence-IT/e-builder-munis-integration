# e-builder-munis-integration

## integration goals from spreadsheet:
spreadsheet[https://lawrenceks.sharepoint.com/:x:/s/MUNISCoreTeam/EW7Qa0n8O3NHnjVznIryZgkBncnMtHHyw26pJBbY13Ub_g?rtime=z_bQBdGQ2kg]
(1) Parking Kiosk complete/tested
(2) Commitment approvals 
(3) Commitment invoices 
(4) Invoice payment status 
(5) General invoices 
(6) Vendors 
(7) Budget changes [if time permits]

(8) 9/6 per Dan ""Since the FTP server is being retired Tim and I are currently working on a replacement for that current integration. Basically I need to make sure the current setup still works before I can begin working on the Munis integration.


## Meeting notes from 7/22
Whiteboard e-Builder / MUNIS Touch Points
Whiteboard e-Builder / MUNIS Touch Points
Last edited: 7/22
Workflow BAC
Finance project number creation
BAH approval process in Munis
BAJ entery in innoprise is double entry process - needs E-builder to talk to Munis
Nevin has a few nightly scripts that update E-builder work flows - update scripts to pull from munis instead
 
We want changes to budget and actuals that are made in Munis to reflect in E-builder
 
upload original budge
BAJ(Budget adjustment)
actual costs
Initiate changes in Munis, use nightly update script to reflect changes in E-builder
 
Dan needs to figure out if the budget adjustments can be updated via E-builder API
 
CA Process

Commitment Approval
Requisition, purchase, contract
Manual entry of docusign download in to financials system 
Innoprise processing grants PO -we want Munis to send PDF of PO back to project manager
Possible via vendor self service?
we need to communicate the PO number generated in Munis back to E-builder
Process PEC 
send a notification that a CA has started for ones of $50K
 
General invoices and expenses on a project NEED to be updated on projects in e-Builder
what forms are being filled out on user end to update invoices?
CA process form - upload pdf of invoice and amounts - Dan
Advertise bid or proposal
PEC completion
CO with and without agreement
Do we want to allow for them to put in their own change orders?
 
Automate the process of adding notifications to tell PM that changes need to be made
power bi dashboard?
test

Notes

Munis status in DB for contracts
10 = closed
8 = Posted
0 = rejected

Munis status in DB for PO
0 = Closed
8 = Printed
9 = Carry Forward