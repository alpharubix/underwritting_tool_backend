import logging
from datetime import datetime
from io import BytesIO
from typing import Optional, Any
import pandas as pd
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

from controller.bsa_summary_drcr_monthwise import (
    bsa_summary_of_debit_credit_monthwise,
)
from controller.cashflow_controller import build_cashflow_report
from controller.overview_month_wise import bank_statement_report_consolidated

logger = logging.getLogger(__name__)

ALLOWED_ROLES = ("USER")

# ============================================================
# EXCEL EXPORT SERVICE
# ============================================================

def export_bsa(
    summary_data: dict,
    cashflow_data: dict,
    monthly_overview_data: dict,
) -> BytesIO:
    """
    Creates a single BSA Excel workbook containing exactly 3 sheets:

    1. Summary of Debit and Credit
    2. CashFlow
    3. Monthly Overview

    The function only transforms already-generated analysis responses
    into Excel. It does not perform BSA calculations.
    """

    output = BytesIO()
    
    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        # ------------------------------------------------------------
        # SHEET 1: SUMMARY OF DEBIT AND CREDIT
        # ------------------------------------------------------------

        _build_summary_debit_credit_sheet(
            writer=writer,
            summary_data=summary_data,
        )

        # ------------------------------------------------------------
        # SHEET 2: CASHFLOW
        # ------------------------------------------------------------

        _build_cashflow_sheet(
            writer=writer,
            cashflow_data=cashflow_data,
        )

        # ------------------------------------------------------------
        # SHEET 3: MONTHLY OVERVIEW
        # ------------------------------------------------------------

        _build_monthly_overview_sheet(
            writer=writer,
            monthly_overview_data=monthly_overview_data,
        )

    output.seek(0)

    return output


# ============================================================
# SHEET 1
# ============================================================

def _build_summary_debit_credit_sheet(
    writer: pd.ExcelWriter,
    summary_data: dict,
) -> None:

    account_details = summary_data.get("account_details", {})
    monthly_breakdown = summary_data.get("monthly_breakdown", [])
    total = summary_data.get("total", {})

    workbook = writer.book
    worksheet = workbook.create_sheet("Summary of Debit and Credit")

    # Remove default sheet created by ExcelWriter
    if "Sheet1" in workbook.sheetnames:
        del workbook["Sheet1"]

    # ------------------------------------------------------------
    # STYLES
    # ------------------------------------------------------------

    title_fill = PatternFill(
        fill_type="solid",
        fgColor="1F4E78",
    )

    section_fill = PatternFill(
        fill_type="solid",
        fgColor="D9EAF7",
    )

    header_fill = PatternFill(
        fill_type="solid",
        fgColor="5B9BD5",
    )

    white_font = Font(
        color="FFFFFF",
        bold=True,
        size=14,
    )

    section_font = Font(
        bold=True,
        size=11,
    )

    header_font = Font(
        color="FFFFFF",
        bold=True,
    )

    thin_side = Side(
        style="thin",
        color="B7B7B7",
    )

    thin_border = Border(
        left=thin_side,
        right=thin_side,
        top=thin_side,
        bottom=thin_side,
    )

    # ------------------------------------------------------------
    # TITLE
    # ------------------------------------------------------------

    worksheet.merge_cells("A1:E1")
    worksheet["A1"] = "BSA - Summary of Debit and Credit"
    worksheet["A1"].fill = title_fill
    worksheet["A1"].font = white_font
    worksheet["A1"].alignment = Alignment(
        horizontal="center",
        vertical="center",
    )

    worksheet.row_dimensions[1].height = 25

    current_row = 3

    # ------------------------------------------------------------
    # ACCOUNT DETAILS
    # ------------------------------------------------------------

    worksheet.merge_cells(
        start_row=current_row,
        start_column=1,
        end_row=current_row,
        end_column=4,
    )

    worksheet.cell(
        current_row,
        1,
        "Account Details",
    )

    worksheet.cell(
        current_row,
        1,
    ).fill = section_fill

    worksheet.cell(
        current_row,
        1,
    ).font = section_font

    current_row += 1

    account_rows = [
        ("Bank Name", account_details.get("Bank Name", "")),
        ("Company Name", account_details.get("Company Name", "")),
        ("Account Number", account_details.get("Account Number", "")),
        ("Period", account_details.get("Period", "")),
        ("No Of Months", account_details.get("No Of Months", "")),
        ("Account Type", account_details.get("Account Type", "")),
        ("CC/OD Limit", account_details.get("CC/OD Limit", "")),
        ("Currency", account_details.get("Currency", "")),
        ("Opening Balance", account_details.get("Opening Balance", "")),
        ("Closing Balance", account_details.get("Closing Balance", "")),
    ]

    account_df = pd.DataFrame(
        account_rows,
        columns=["Field", "Value"],
    )

    account_df.to_excel(
        writer,
        sheet_name="Summary of Debit and Credit",
        startrow=current_row - 1,
        startcol=0,
        index=False,
    )

    # Re-fetch because worksheet was already manually obtained.
    for cell in worksheet[current_row]:
        if cell.value is not None:
            cell.fill = header_fill
            cell.font = header_font
            cell.border = thin_border

    current_row += len(account_df) + 2

    # ------------------------------------------------------------
    # TOTAL INFLOWS / OUTFLOWS
    # ------------------------------------------------------------

    worksheet.merge_cells(
        start_row=current_row,
        start_column=1,
        end_row=current_row,
        end_column=4,
    )

    worksheet.cell(
        current_row,
        1,
        "Total Debit and Credit",
    )

    worksheet.cell(
        current_row,
        1,
    ).fill = section_fill

    worksheet.cell(
        current_row,
        1,
    ).font = section_font

    current_row += 1

    summary_rows = [
        {
            "Category": "Inflows",
            "Transaction Type": "Cash Deposit",
            "Amount": total.get("inflows_value_breakdown", {}).get(
                "cash_deposit",
                0,
            ),
            "No. of Transactions": total.get("inflows_no_breakdown", {}).get(
                "cash_deposit",
                0,
            ),
        },
        {
            "Category": "Inflows",
            "Transaction Type": "Cheque Receipt",
            "Amount": total.get("inflows_value_breakdown", {}).get(
                "cheque_receipt",
                0,
            ),
            "No. of Transactions": total.get("inflows_no_breakdown", {}).get(
                "cheque_receipt",
                0,
            ),
        },
        {
            "Category": "Inflows",
            "Transaction Type": "Online Receipt",
            "Amount": total.get("inflows_value_breakdown", {}).get(
                "online_receipt",
                0,
            ),
            "No. of Transactions": total.get("inflows_no_breakdown", {}).get(
                "online_receipt",
                0,
            ),
        },
        {
            "Category": "Inflows",
            "Transaction Type": "Other Receipt",
            "Amount": total.get("inflows_value_breakdown", {}).get(
                "other_receipt",
                0,
            ),
            "No. of Transactions": total.get("inflows_no_breakdown", {}).get(
                "other_receipt",
                0,
            ),
        },
        {
            "Category": "Inflows",
            "Transaction Type": "Inhouse Receipt",
            "Amount": total.get("inflows_value_breakdown", {}).get(
                "inhouse_receipt",
                0,
            ),
            "No. of Transactions": total.get("inflows_no_breakdown", {}).get(
                "inhouse_receipt",
                0,
            ),
        },
        {
            "Category": "Inflows",
            "Transaction Type": "Total Receipt Inflows",
            "Amount": total.get(
                "total_receipt_inflows_value",
                0,
            ),
            "No. of Transactions": total.get(
                "total_receipt_inflows_no",
                0,
            ),
        },
        {
            "Category": "Outflows",
            "Transaction Type": "Cash Withdrawal",
            "Amount": total.get("outflows_value_breakdown", {}).get(
                "cash_withdrawal",
                0,
            ),
            "No. of Transactions": total.get("outflows_no_breakdown", {}).get(
                "cash_withdrawal_no",
                0,
            ),
        },
        {
            "Category": "Outflows",
            "Transaction Type": "Cheque Payment",
            "Amount": total.get("outflows_value_breakdown", {}).get(
                "cheque_payment",
                0,
            ),
            "No. of Transactions": total.get("outflows_no_breakdown", {}).get(
                "cheque_payment_no",
                0,
            ),
        },
        {
            "Category": "Outflows",
            "Transaction Type": "Online Payment",
            "Amount": total.get("outflows_value_breakdown", {}).get(
                "online_payment",
                0,
            ),
            "No. of Transactions": total.get("outflows_no_breakdown", {}).get(
                "online_payment_no",
                0,
            ),
        },
        {
            "Category": "Outflows",
            "Transaction Type": "Other Payment",
            "Amount": total.get("outflows_value_breakdown", {}).get(
                "other_payment",
                0,
            ),
            "No. of Transactions": total.get("outflows_no_breakdown", {}).get(
                "other_payment_no",
                0,
            ),
        },
        {
            "Category": "Outflows",
            "Transaction Type": "Inhouse Payment",
            "Amount": total.get("outflows_value_breakdown", {}).get(
                "inhouse_payment",
                0,
            ),
            "No. of Transactions": total.get("outflows_no_breakdown", {}).get(
                "inhouse_payment_no",
                0,
            ),
        },
        {
            "Category": "Outflows",
            "Transaction Type": "Total Payment Outflows",
            "Amount": total.get(
                "total_payments_outflows_value",
                0,
            ),
            "No. of Transactions": total.get(
                "total_payments_outflows_no",
                0,
            ),
        },
    ]

    summary_df = pd.DataFrame(summary_rows)

    summary_df.to_excel(
        writer,
        sheet_name="Summary of Debit and Credit",
        startrow=current_row - 1,
        startcol=0,
        index=False,
    )

    for cell in worksheet[current_row]:
        if cell.value is not None:
            cell.fill = header_fill
            cell.font = header_font
            cell.border = thin_border

    current_row += len(summary_df) + 2

    # ------------------------------------------------------------
    # MONTHLY BREAKDOWN
    # ------------------------------------------------------------

    worksheet.merge_cells(
        start_row=current_row,
        start_column=1,
        end_row=current_row,
        end_column=9,
    )

    worksheet.cell(
        current_row,
        1,
        "Monthly Breakdown",
    )

    worksheet.cell(
        current_row,
        1,
    ).fill = section_fill

    worksheet.cell(
        current_row,
        1,
    ).font = section_font

    current_row += 1

    monthly_rows = []

    for row in monthly_breakdown:

        inflow_value = row.get(
            "inflows_value",
            {},
        ).get(
            "inflows_value_breakdown",
            {},
        )

        inflow_no = row.get(
            "inflows_no",
            {},
        ).get(
            "inflows_no_breakdown",
            {},
        )

        outflow_value = row.get(
            "outflows_value",
            {},
        ).get(
            "outflows_value_breakdown",
            {},
        )

        outflow_no = row.get(
            "outflows_no",
            {},
        ).get(
            "outflows_no_breakdown",
            {},
        )

        monthly_rows.append(
            {
                "Month": row.get("month", ""),
                "Cash Deposit": inflow_value.get("cash_deposit", 0),
                "Cheque Receipt": inflow_value.get("cheque_receipt", 0),
                "Online Receipt": inflow_value.get("online_receipt", 0),
                "Other Receipt": inflow_value.get("other_receipt", 0),
                "Inhouse Receipt": inflow_value.get("inhouse_receipt", 0),
                "Total Inflows": row.get(
                    "inflows_value",
                    {},
                ).get(
                    "total_receipt_inflows_value",
                    0,
                ),
                "Cash Deposit No": inflow_no.get("cash_deposit_no", 0),
                "Cheque Receipt No": inflow_no.get("cheque_receipt_no", 0),
                "Online Receipt No": inflow_no.get("online_receipt_no", 0),
                "Other Receipt No": inflow_no.get("other_receipt_no", 0),
                "Inhouse Receipt No": inflow_no.get("inhouse_receipt_no", 0),
                "Total Inflows No": row.get(
                    "inflows_no",
                    {},
                ).get(
                    "total_receipt_inflows_no",
                    0,
                ),
                "Cash Withdrawal": outflow_value.get(
                    "cash_withdrawal",
                    0,
                ),
                "Cheque Payment": outflow_value.get(
                    "cheque_payment",
                    0,
                ),
                "Online Payment": outflow_value.get(
                    "online_payment",
                    0,
                ),
                "Other Payment": outflow_value.get(
                    "other_payment",
                    0,
                ),
                "Inhouse Payment": outflow_value.get(
                    "inhouse_payment",
                    0,
                ),
                "Total Outflows": row.get(
                    "outflows_value",
                    {},
                ).get(
                    "total_payments_outflows_value",
                    0,
                ),
                "Cash Withdrawal No": outflow_no.get(
                    "cash_withdrawal_no",
                    0,
                ),
                "Cheque Payment No": outflow_no.get(
                    "cheque_payment_no",
                    0,
                ),
                "Online Payment No": outflow_no.get(
                    "online_payment_no",
                    0,
                ),
                "Other Payment No": outflow_no.get(
                    "other_payment_no",
                    0,
                ),
                "Inhouse Payment No": outflow_no.get(
                    "inhouse_payment_no",
                    0,
                ),
                "Total Outflows No": row.get(
                    "outflows_no",
                    {},
                ).get(
                    "total_payments_outflows_no",
                    0,
                ),
            }
        )

    monthly_df = pd.DataFrame(monthly_rows)

    monthly_df.to_excel(
        writer,
        sheet_name="Summary of Debit and Credit",
        startrow=current_row - 1,
        startcol=0,
        index=False,
    )

    _format_worksheet(
        worksheet,
        freeze_cell="A2",
    )


# ============================================================
# SHEET 2
# ============================================================

def _build_cashflow_sheet(
    writer: pd.ExcelWriter,
    cashflow_data: dict,
) -> None:

    data = cashflow_data.get("data", {})

    summary = data.get("summary", {})
    monthly_breakdown = data.get("monthly_breakdown", [])

    workbook = writer.book

    worksheet = workbook.create_sheet("CashFlow")

    # ------------------------------------------------------------
    # STYLES
    # ------------------------------------------------------------

    title_fill = PatternFill(
        fill_type="solid",
        fgColor="548235",
    )

    section_fill = PatternFill(
        fill_type="solid",
        fgColor="E2F0D9",
    )

    header_fill = PatternFill(
        fill_type="solid",
        fgColor="70AD47",
    )

    title_font = Font(
        color="FFFFFF",
        bold=True,
        size=14,
    )

    section_font = Font(
        bold=True,
    )

    header_font = Font(
        color="FFFFFF",
        bold=True,
    )

    thin_side = Side(
        style="thin",
        color="B7B7B7",
    )

    thin_border = Border(
        left=thin_side,
        right=thin_side,
        top=thin_side,
        bottom=thin_side,
    )

    # ------------------------------------------------------------
    # TITLE
    # ------------------------------------------------------------

    worksheet.merge_cells("A1:D1")

    worksheet["A1"] = "BSA - CashFlow"

    worksheet["A1"].fill = title_fill
    worksheet["A1"].font = title_font
    worksheet["A1"].alignment = Alignment(
        horizontal="center",
        vertical="center",
    )

    worksheet.row_dimensions[1].height = 25

    current_row = 3

    # ------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------

    worksheet.merge_cells(
        start_row=current_row,
        start_column=1,
        end_row=current_row,
        end_column=4,
    )

    worksheet.cell(
        current_row,
        1,
        "CashFlow Summary",
    )

    worksheet.cell(
        current_row,
        1,
    ).fill = section_fill

    worksheet.cell(
        current_row,
        1,
    ).font = section_font

    current_row += 1

    summary_rows = [
        ("Total Inflows %", summary.get("total_inflows_percent", 0)),
        ("Inflows / Revenue", summary.get("inflows_revenue_a", 0)),
        ("Cash Deposit", summary.get("cash_deposit", 0)),
        ("Cheque Receipt", summary.get("cheque_receipt", 0)),
        ("Online Receipt", summary.get("online_receipt", 0)),
        ("Other Receipt", summary.get("other_receipt", 0)),
        ("Total Outflows %", summary.get("total_outflows_percent", 0)),
        ("Outflows / Expenses", summary.get("outflows_expenses_b", 0)),
        ("Cash Withdrawal", summary.get("cash_withdrawal", 0)),
        ("Cheque Payment", summary.get("cheque_payment", 0)),
        ("Online Payment", summary.get("online_payment", 0)),
        ("Other Payment", summary.get("other_payment", 0)),
        ("Gross Inflow Profit", summary.get("gross_inflow_profit_c", 0)),
        ("Indirect Expenses", summary.get("indirect_expenses_d", 0)),
        ("Salary Payment", summary.get("salary_payment", 0)),
        ("Insurance Payment", summary.get("insurance_payment", 0)),
        ("Rent Payment", summary.get("rent_payment", 0)),
        ("Company Expense", summary.get("company_expense", 0)),
        ("Bank Charge", summary.get("bank_charge", 0)),
        ("Utility Expense", summary.get("utility_expense", 0)),
        ("Tax Paid", summary.get("tax_paid", 0)),
        ("Interest Paid", summary.get("interest_paid", 0)),
        ("Refund Payment", summary.get("refund_payment", 0)),
        ("Credit Card Payment", summary.get("credit_card_payment", 0)),
        ("Forex Payment", summary.get("forex_payment", 0)),
        ("Indirect Income", summary.get("indirect_income_e", 0)),
        ("Interest Received", summary.get("interest_received", 0)),
        ("Tax Refund", summary.get("tax_refund", 0)),
        ("Rent Receipt", summary.get("rent_receipt", 0)),
        ("Net Inflow Profit", summary.get("net_inflow_profit_f", 0)),
        ("Total Payables", summary.get("total_payables", 0)),
        ("Loan Payment", summary.get("loan_payment", 0)),
        ("Work Capital Payment", summary.get("work_capital_payment", 0)),
        ("Investment Payment", summary.get("investment_payment", 0)),
        ("Contra Payment", summary.get("contra_payment", 0)),
        ("FI Payment", summary.get("fi_payment", 0)),
        ("Sweep Out", summary.get("sweep_out", 0)),
        (
            "Bank Instrument Payment",
            summary.get("bank_instrument_payment", 0),
        ),
        ("Total Receivables", summary.get("total_receivables_g", 0)),
        ("Loan Receipt", summary.get("loan_receipt", 0)),
        ("Work Capital Receipt", summary.get("work_capital_receipt", 0)),
        ("Investment Receipt", summary.get("investment_receipt", 0)),
        ("Insurance Receipt", summary.get("insurance_receipt", 0)),
        ("Contra Receipt", summary.get("contra_receipt", 0)),
        ("FI Receipt", summary.get("fi_receipt", 0)),
        ("Sweep In", summary.get("sweep_in", 0)),
        ("Bank Accruals", summary.get("bank_accruals", 0)),
        ("Opening Balance", summary.get("opening_balance", 0)),
        ("Closing Balance", summary.get("closing_balance", 0)),
        ("Net Cashflow", summary.get("net_cashflow", 0)),
    ]

    summary_df = pd.DataFrame(
        summary_rows,
        columns=["Metric", "Value"],
    )

    summary_df.to_excel(
        writer,
        sheet_name="CashFlow",
        startrow=current_row - 1,
        startcol=0,
        index=False,
    )

    for cell in worksheet[current_row]:
        if cell.value is not None:
            cell.fill = header_fill
            cell.font = header_font
            cell.border = thin_border

    current_row += len(summary_df) + 2

    # ------------------------------------------------------------
    # MONTHLY BREAKDOWN
    # ------------------------------------------------------------

    worksheet.merge_cells(
        start_row=current_row,
        start_column=1,
        end_row=current_row,
        end_column=20,
    )

    worksheet.cell(
        current_row,
        1,
        "Monthly Breakdown",
    )

    worksheet.cell(
        current_row,
        1,
    ).fill = section_fill

    worksheet.cell(
        current_row,
        1,
    ).font = section_font

    current_row += 1

    if monthly_breakdown:
        monthly_df = pd.DataFrame(monthly_breakdown)

        # Remove technical field from exported Excel.
        if "parsedMonthDate" in monthly_df.columns:
            monthly_df = monthly_df.drop(
                columns=["parsedMonthDate"]
            )

        # More readable column names.
        monthly_df = monthly_df.rename(
            columns={
                "MonthYear": "Month",
                "TotalInflowPercentage": "Total Inflow %",
                "Inflow": "Inflow",
                "CashDeposit": "Cash Deposit",
                "ChequeReceipt": "Cheque Receipt",
                "OnlineReceipt": "Online Receipt",
                "OtherReceipt": "Other Receipt",
                "TotalOutflowPercentage": "Total Outflow %",
                "OutFlow": "Outflow",
                "CashWithdraw": "Cash Withdrawal",
                "ChequePayment": "Cheque Payment",
                "OnlinePayment": "Online Payment",
                "OtherPayment": "Other Payment",
                "GrossInflow": "Gross Inflow",
                "IndirectExpense": "Indirect Expense",
                "SalaryPayment": "Salary Payment",
                "InsurancePayment": "Insurance Payment",
                "RentPayment": "Rent Payment",
                "CompanyExpense": "Company Expense",
                "BankCharge": "Bank Charge",
                "UtilityExpense": "Utility Expense",
                "TaxPaid": "Tax Paid",
                "InterestPaid": "Interest Paid",
                "RefundPayment": "Refund Payment",
                "CreditCardPayment": "Credit Card Payment",
                "ForexPayment": "Forex Payment",
                "IndirectIncome": "Indirect Income",
                "InterestReceived": "Interest Received",
                "TaxRefund": "Tax Refund",
                "RentReceipt": "Rent Receipt",
                "NetInflow": "Net Inflow",
                "Payable": "Payable",
                "LoanPayment": "Loan Payment",
                "workCapitalPayment": "Work Capital Payment",
                "InvestmentPayment": "Investment Payment",
                "ContraPayment": "Contra Payment",
                "FiPayment": "FI Payment",
                "SweepOut": "Sweep Out",
                "BankInstrumentPayment": "Bank Instrument Payment",
                "Receiveble": "Receivable",
                "LoanReceipt": "Loan Receipt",
                "WorkCapitalReceipt": "Work Capital Receipt",
                "InvestmentReceipt": "Investment Receipt",
                "InsuranceReceipt": "Insurance Receipt",
                "ContraReceipt": "Contra Receipt",
                "FiReceipt": "FI Receipt",
                "SweepIn": "Sweep In",
                "BankAccural": "Bank Accrual",
                "OpeningBalance": "Opening Balance",
                "ClosingBalance": "Closing Balance",
            }
        )

        monthly_df.to_excel(
            writer,
            sheet_name="CashFlow",
            startrow=current_row - 1,
            startcol=0,
            index=False,
        )

        for cell in worksheet[current_row]:
            if cell.value is not None:
                cell.fill = header_fill
                cell.font = header_font
                cell.border = thin_border

    _format_worksheet(
        worksheet,
        freeze_cell="A2",
    )


# ============================================================
# SHEET 3
# ============================================================

def _build_monthly_overview_sheet(
    writer: pd.ExcelWriter,
    monthly_overview_data: dict,
) -> None:

    consolidated_report = monthly_overview_data.get(
        "consolidated_overall_report",
        {},
    )

    monthly_breakdown = monthly_overview_data.get(
        "monthly_breakdown",
        [],
    )

    workbook = writer.book

    worksheet = workbook.create_sheet("Monthly Overview")

    # ------------------------------------------------------------
    # STYLES
    # ------------------------------------------------------------

    title_fill = PatternFill(fill_type="solid", fgColor="002060")

    section_fill = PatternFill(
        fill_type="solid",
        fgColor="E4DFEC",
    )

    header_fill = PatternFill(fill_type="solid", fgColor="002060")

    title_font = Font(
        color="FFFFFF",
        bold=True,
        size=14,
    )

    section_font = Font(
        bold=True,
    )

    header_font = Font(
        color="FFFFFF",
        bold=True,
    )

    thin_side = Side(
        style="thin",
        color="B7B7B7",
    )

    thin_border = Border(
        left=thin_side,
        right=thin_side,
        top=thin_side,
        bottom=thin_side,
    )

    # ------------------------------------------------------------
    # TITLE
    # ------------------------------------------------------------

    worksheet.merge_cells("A1:D1")

    worksheet["A1"] = "BSA - Monthly Overview"

    worksheet["A1"].fill = title_fill
    worksheet["A1"].font = title_font
    worksheet["A1"].alignment = Alignment(
        horizontal="center",
        vertical="center",
    )

    worksheet.row_dimensions[1].height = 25

    current_row = 3

    # ------------------------------------------------------------
    # CONSOLIDATED REPORT
    # ------------------------------------------------------------

    sections = [
        (
            "Overview",
            consolidated_report.get(
                "overview",
                {},
            ),
        ),
        (
            "Cash Inflow",
            consolidated_report.get(
                "cash_inflow",
                {},
            ),
        ),
        (
            "Cash Outflow",
            consolidated_report.get(
                "cash_outflow",
                {},
            ),
        ),
        (
            "Returns",
            consolidated_report.get(
                "returns",
                {},
            ),
        ),
        (
            "Other Calculations",
            consolidated_report.get(
                "other_calculations",
                {},
            ),
        ),
    ]

    for section_name, section_data in sections:

        worksheet.merge_cells(
            start_row=current_row,
            start_column=1,
            end_row=current_row,
            end_column=4,
        )

        worksheet.cell(
            current_row,
            1,
            section_name,
        )

        worksheet.cell(
            current_row,
            1,
        ).fill = section_fill

        worksheet.cell(
            current_row,
            1,
        ).font = section_font

        current_row += 1

        section_rows = []

        for key, value in section_data.items():

            readable_key = _make_readable_label(key)

            section_rows.append(
                {
                    "Metric": readable_key,
                    "Value": value,
                }
            )

        section_df = pd.DataFrame(section_rows)

        section_df.to_excel(
            writer,
            sheet_name="Monthly Overview",
            startrow=current_row - 1,
            startcol=0,
            index=False,
        )

        for cell in worksheet[current_row]:
            if cell.value is not None:
                cell.fill = header_fill
                cell.font = header_font
                cell.border = thin_border

        current_row += len(section_df) + 2

    # ------------------------------------------------------------
    # MONTHLY BREAKDOWN
    # ------------------------------------------------------------

    worksheet.merge_cells(
        start_row=current_row,
        start_column=1,
        end_row=current_row,
        end_column=15,
    )

    worksheet.cell(
        current_row,
        1,
        "Monthly Breakdown",
    )

    worksheet.cell(
        current_row,
        1,
    ).fill = section_fill

    worksheet.cell(
        current_row,
        1,
    ).font = section_font

    current_row += 1

    if monthly_breakdown:
        monthly_labels = [
            _make_readable_label(str(row.get("Month", "")))
            for row in monthly_breakdown
        ]

        metric_names = [
            key for key in monthly_breakdown[0]
            if key not in {"Month", "parsedMonthDate"}
        ]

        metric_labels = {
                "Month": "Month",
                "AverageCreditTranx": "Average Credit Transaction",
                "TotalCreditNo": "Total Credit No",
                "AverageDebitTranx": "Average Debit Transaction",
                "TotalDebitNo": "Total Debit No",
                "TotalCredit": "Total Credit",
                "OutwardChequeReturn": "Outward Cheque Return",
                "ReversalOfInwardChequeReturn": "Reversal Of Inward Cheque Return",
                "ReversalOfOnlineReturn": "Reversal Of Online Return",
                "GrossCredits": "Gross Credits",
                "Contra": "Contra",
                "LoanReceived": "Loan Received",
                "NetCredits": "Net Credits",
                "InhouseCredit": "Inhouse Credit",
                "NetCashInflow": "Net Cash Inflow",
                "TotalDebit": "Total Debit",
                "InwardChequeReturn": "Inward Cheque Return",
                "ReversalOfOutwardChequeReturn": "Reversal Of Outward Cheque Return",
                "OnlineReturn": "Online Return",
                "GrossDebit": "Gross Debit",
                "ContraDebit": "Contra Debit",
                "NetDebit": "Net Debit",
                "InhouseDebit": "Inhouse Debit",
                "NetCashOutFlow": "Net Cash Outflow",
                "InwardChequeReturnNos": "Inward Cheque Return No",
                "InwardChequeReturnToTotalChequeReceivedInPercent": "Inward Cheque Return %",
                "OutwardChequeReturnNo": "Outward Cheque Return No",
                "OutwardChequeReturnToTotalChequePaidInPercent": "Outward Cheque Return %",
                "InwardOnlineReturnNo": "Inward Online Return No",
                "InwardOnlineReturnTototalOnlineCreditInPercent": "Inward Online Return %",
                "OutwardOnlineReturnNo": "Outward Online Return No",
                "OutwardOnlineReturnToTotalOnlineDebitInPercent": "Outward Online Return %",
                "EcsReturnNo": "ECS Return No",
                "EcsReturnToTotalEcsPaymentInPercent": "ECS Return %",
                "InhouseCreditNos": "Inhouse Credit No",
                "InhouseCreditToTotalCreditInPercent": "Inhouse Credit %",
                "InhouseDebitNos": "Inhouse Debit No",
                "InhouseDebitToTotalDebitInPercent": "Inhouse Debit %",
                "AverageEod": "Average EOD",
                "odccLimit": "OD/CC Limit",
                "odccDrawingLimit": "OD/CC Drawing Limit",
                "AverageOdAndCCLimitUtilizationInPercent": "Average OD/CC Utilization %",
                "NoOfdaysLimitOverDrawn": "No. of Days Limit Overdrawn",
                "NoOfTimesLimitOverDrawn": "No. of Times Limit Overdrawn",
                "OverDrawnAnountInRsMn": "Overdrawn Amount (Rs Mn)",
                "OverDrawnAverageinRsMn": "Average Overdrawn (Rs Mn)",
                "OverDrawnAverageAsPercentOfOdCCLimit": "Average Overdrawn %",
                "PeakOverDrawingAmount": "Peak Overdrawing Amount",
                "PeakOverDrawingDate": "Peak Overdrawing Date",
                "LoanRepaid": "Loan Repaid",
                "EcsPayment": "ECS Payment",
                "NoOfUniqueEcs": "No. of Unique ECS",
                "InterestPaid": "Interest Paid",
        }

        header_row = current_row
        worksheet.cell(header_row, 1, "Particulars")
        for column, month in enumerate(monthly_labels, start=2):
            worksheet.cell(header_row, column, month)

        for column in range(1, len(monthly_labels) + 2):
            cell = worksheet.cell(header_row, column)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="left")

        current_row += 1

        for metric_index, metric_name in enumerate(metric_names):
            label = metric_labels.get(metric_name, _make_readable_label(metric_name))
            worksheet.cell(current_row, 1, label)

            for column, monthly_data in enumerate(monthly_breakdown, start=2):
                worksheet.cell(current_row, column, monthly_data.get(metric_name, ""))

            for column in range(1, len(monthly_labels) + 2):
                cell = worksheet.cell(current_row, column)
                cell.border = Border(bottom=thin_side)
                cell.alignment = Alignment(horizontal="left")

            if metric_index == 4:
                for column in range(1, len(monthly_labels) + 2):
                    worksheet.cell(current_row, column).border = Border(
                        top=Side(style="medium", color="002060"),
                        bottom=thin_side,
                    )

            current_row += 1

        worksheet.column_dimensions["A"].width = 42
        for column in range(2, len(monthly_labels) + 2):
            worksheet.column_dimensions[get_column_letter(column)].width = 20

    _format_worksheet(
        worksheet,
        freeze_cell="A2",
    )


# ============================================================
# COMMON EXCEL HELPERS
# ============================================================

def _format_worksheet(
    worksheet,
    freeze_cell: str = "A1",
) -> None:

    worksheet.freeze_panes = freeze_cell

    # ------------------------------------------------------------
    # Borders + alignment
    # ------------------------------------------------------------

    thin_side = Side(
        style="thin",
        color="D9D9D9",
    )

    thin_border = Border(
        left=thin_side,
        right=thin_side,
        top=thin_side,
        bottom=thin_side,
    )

    for row in worksheet.iter_rows():

        for cell in row:

            if cell.value is None:
                continue

            cell.border = thin_border

            cell.alignment = Alignment(
                vertical="center",
                wrap_text=True,
            )

    # ------------------------------------------------------------
    # Number formatting
    # ------------------------------------------------------------

    for row in worksheet.iter_rows():

        for cell in row:

            if isinstance(cell.value, (int, float)):

                cell.number_format = '#,##0.00'

    # ------------------------------------------------------------
    # Column width
    # ------------------------------------------------------------

    for column_cells in worksheet.columns:

        max_length = 0

        column_letter = get_column_letter(
            column_cells[0].column
        )

        for cell in column_cells:

            try:
                value_length = len(
                    str(cell.value)
                    if cell.value is not None
                    else ""
                )

                max_length = max(
                    max_length,
                    value_length,
                )

            except Exception:
                continue

        width = min(
            max(max_length + 2, 12),
            35,
        )

        worksheet.column_dimensions[
            column_letter
        ].width = width


def _make_readable_label(
    key: str,
) -> str:

    if not key:
        return ""

    key = key.replace("_", " ")

    key = key.replace("/", " / ")

    key = key.replace("-", " - ")

    key = " ".join(key.split())

    return key.title()


# ============================================================
# EXPORT CONTROLLER
# ============================================================

async def export_bsa_report(
    db,
    user_id: str,
    from_date: str,
    to_date: str,
    requester_role: str,
    cust_id: Optional[str] = None,
):
    """
    Orchestrates all three BSA analysis functions and generates
    one Excel workbook.

    Frontend sends:
        from_date = YYYY-MM-DD
        to_date   = YYYY-MM-DD

    CashFlow internally receives:
        from_month = YYYY-MM
        to_month   = YYYY-MM
    """

    logger.info(
        "export_bsa_report.start | user_id=%s | from_date=%s | to_date=%s",
        user_id,
        from_date,
        to_date,
    )

    # ------------------------------------------------------------
    # USER VALIDATION
    # ------------------------------------------------------------

    if not user_id or not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid user_id",
            },
        )

    # ------------------------------------------------------------
    # ROLE / CUSTOMER HANDLING
    # ------------------------------------------------------------

    if requester_role in ALLOWED_ROLES:

        if not cust_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Since the role is accessing on behalf of the user, cust_id is required",
                },
            )

        user_id = str(cust_id)

    # ------------------------------------------------------------
    # DATE VALIDATION
    # ------------------------------------------------------------

    if not from_date or not to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "from_date and to_date are required query parameters",
            },
        )

    try:

        from_dt = datetime.strptime(
            from_date,
            "%Y-%m-%d",
        )

        to_dt = datetime.strptime(
            to_date,
            "%Y-%m-%d",
        ).replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )

    except ValueError:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid date format. Use YYYY-MM-DD",
            },
        )

    if from_dt > to_dt:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "from_date must be earlier than or equal to to_date",
            },
        )

    delta = to_dt - from_dt

    if delta.days > 730:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Date range cannot exceed 2 years",
            },
        )

    try:

        # --------------------------------------------------------
        # 1. SUMMARY OF DEBIT AND CREDIT
        # --------------------------------------------------------

        summary_data = await bsa_summary_of_debit_credit_monthwise(
            db=db,
            user_id=user_id,
            from_date=from_dt,
            to_date=to_dt,
        )

        # --------------------------------------------------------
        # 2. CASHFLOW
        # --------------------------------------------------------

        from_month = from_dt.strftime(
            "%Y-%m"
        )

        to_month = to_dt.strftime(
            "%Y-%m"
        )

        cashflow_data = await build_cashflow_report(
            db=db,
            user_id=user_id,
            from_month=from_month,
            to_month=to_month,
        )

        # --------------------------------------------------------
        # 3. MONTHLY OVERVIEW
        # --------------------------------------------------------

        monthly_overview_data = await bank_statement_report_consolidated(
            db=db,
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
        )

        logger.info(
            "export_bsa_report.analysis_completed | user_id=%s | from_date=%s | to_date=%s",
            user_id,
            from_date,
            to_date,
        )

        # --------------------------------------------------------
        # 4. CREATE EXCEL
        # --------------------------------------------------------

        excel_file = export_bsa(
            summary_data=summary_data,
            cashflow_data=cashflow_data,
            monthly_overview_data=monthly_overview_data,
        )

        filename = (
            f"BSA_Report_{from_date}_to_{to_date}.xlsx"
        )

        logger.info(
            "export_bsa_report.success | user_id=%s | filename=%s",
            user_id,
            filename,
        )

        # --------------------------------------------------------
        # 5. RETURN DOWNLOAD RESPONSE
        # --------------------------------------------------------

        return StreamingResponse(
            excel_file,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                ),
            },
        )

    except HTTPException:
        raise

    except Exception as e:

        logger.error(
            "export_bsa_report.failed | user_id=%s | "
            "from_date=%s | to_date=%s | error=%s",
            user_id,
            from_date,
            to_date,
            str(e),
            exc_info=True,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to generate BSA export",
            },
        )
