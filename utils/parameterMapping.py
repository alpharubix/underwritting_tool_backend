# utils/parameter_mapping.py

PARAMETER_MAPPING = {

    # ---------------------------
    # Transaction Summary
    # ---------------------------
    "Average Credit Tranx": "AverageCreditTranx",
    "Total Credit (Nos.)": "TotalCreditNo",
    "Average Debit Tranx": "AverageDebitTranx",
    "Total Debit (Nos.)": "TotalDebitNo",

    "Total Credits": "TotalCredit",
    "Outward Cheque Return": "OutwardChequeReturn",
    "Reversal of Inward Cheque Return": "ReversalOfInwardChequeReturn",
    "Reversal of Online Return": "ReversalOfOnlineReturn",
    "Gross Credits": "GrossCredits",
    "Contra": "Contra",
    "Loan Received": "LoanReceived",
    "Net Credits": "NetCredits",
    "Inhouse Credit": "InhouseCredit",
    "Net Cash Inflow": "NetCashInflow",

    "Total Debits": "TotalDebit",
    "Inward Cheque Return": "InwardChequeReturn",
    "Reversal of Outward Cheque Return": "ReversalOfOutwardChequeReturn",
    "Online Return": "OnlineReturn",
    "Gross Debits": "GrossDebits",
    "Net Debits": "NetDebits",
    "Inhouse Debit": "InhouseDebit",
    "Net Cash Outflow": "NetCashOutflow",

    # ---------------------------
    # Return Statistics
    # ---------------------------
    "Inward Cheque Return (Nos.)": "InwardChequeReturnNo",
    "Inward Cheque Return/Total Cheques Received (%)": "InwardChequeReturnPercentage",

    "Outward Cheque Return (Nos.)": "OutwardChequeReturnNo",
    "Outward Cheque Return/Total Cheques Paid (%)": "OutwardChequeReturnPercentage",

    "Inward Online Return (Nos.)": "InwardOnlineReturnNo",
    "Inward Online Return/Total Online Credits (%)": "InwardOnlineReturnPercentage",

    "Outward Online Return (Nos.)": "OutwardOnlineReturnNo",
    "Outward Online Return/Total Online Debits (%)": "OutwardOnlineReturnPercentage",

    "ECS Return (Credit Nos.)": "ECSReturnCreditNo",
    "ECS Return/Total ECS Payments (%)": "ECSReturnPercentage",

    "Inhouse Credit (Nos.)": "InhouseCreditNo",
    "Inhouse Credit/Total Credits (%)": "InhouseCreditPercentage",

    "Inhouse Debit (Nos.)": "InhouseDebitNo",
    "Inhouse Debit/Total Debits (%)": "InhouseDebitPercentage",

    # ---------------------------
    # OD / CC
    # ---------------------------
    "Average EOD": "AverageEOD",
    "OD/CC Sanction Limit": "ODCCSanctionLimit",
    "OD/CC Drawing Power Limit": "ODCCDrawingPowerLimit",
    "Average OD & CC Limit Utilization (%)": "AverageODCCLimitUtilization",

    "No. of days limit over-drawn": "NoOfDaysLimitOverdrawn",
    "No. of times limit over-drawn": "NoOfTimesLimitOverdrawn",
    "Overdrawn Amount in Rs. Mn. (for all days)": "OverdrawnAmount",
    "Overdrawn Average Amount in Rs. Mn.": "OverdrawnAverageAmount",
    "Overdrawn Average as a %age of OD/CC Limit": "OverdrawnAveragePercentage",

    "Peak overdrawing amount": "PeakOverdrawingAmount",
    "Peak overdrawing date": "PeakOverdrawingDate",

    # ---------------------------
    # Loans
    # ---------------------------
    "Loan Repaid": "LoanRepaid",
    "ECS Payment": "ECSPayment",
    "No. of Unique ECS/EMI's": "UniqueECSCount",
    "Interest Paid": "InterestPaid",

    # ---------------------------
    # Inflows
    # ---------------------------
    "Total Inflow (%)": "TotalInflowPercentage",
    "Cash Deposit": "CashDeposit",
    "Cheque Receipt": "ChequeReceipt",
    "Online Receipt": "OnlineReceipt",
    "Other Receipt": "OtherReceipt",

    # ---------------------------
    # Outflows
    # ---------------------------
    "Total Outflow (%)": "TotalOutflowPercentage",
    "Cash Withdrawal": "CashWithdrawal",
    "Cheque Payment": "ChequePayment",
    "Online Payment": "OnlinePayment",
    "Other Payment": "OtherPayment",

    # ---------------------------
    # Profitability
    # ---------------------------
    "Gross Inflow/Profit": "GrossInflowProfit",

    # ---------------------------
    # Expenses
    # ---------------------------
    "Salary Payment": "SalaryPayment",
    "Insurance": "Insurance",
    "Rent Payment": "RentPayment",
    "Company Expense": "CompanyExpense",
    "Bank Charges": "BankCharges",
    "Utility Payment": "UtilityPayment",
    "Tax Payment": "TaxPayment",
    "Refund/Reversal": "RefundReversal",
    "Credit Card Payment": "CreditCardPayment",
    "Forex": "Forex",

    # ---------------------------
    # Income
    # ---------------------------
    "Interest Received": "InterestReceived",
    "Tax Refund": "TaxRefund",
    "Rent Received": "RentReceived",

    # ---------------------------
    # Net Profit
    # ---------------------------
    "Net Inflow/Profit": "NetInflowProfit",

    # ---------------------------
    # Payables
    # ---------------------------
    "Loan": "Loan",
    "Working Capital": "WorkingCapital",
    "Investment": "Investment",
    "FI Transaction": "FITransaction",
    "Sweep-out": "SweepOut",
    "Bank Instrument": "BankInstrument",

    # ---------------------------
    # Receivables
    # ---------------------------
    "Sweep-In": "SweepIn",
    "Bank Accruals": "BankAccruals",

    # ---------------------------
    # Balances
    # ---------------------------
    "Opening Balance": "OpeningBalance",
    "Closing Balance": "ClosingBalance",

    # ---------------------------
    # Totals
    # ---------------------------
    "Total Receipt": "TotalReceipt",
    "Total Payments": "TotalPayments"
}