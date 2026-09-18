import logging
from datetime import datetime
from decimal import Decimal
from json import JSONDecodeError

from fastapi import HTTPException
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from controller.overview_month_wise import _compute_report, _safe_decimal

logger = logging.getLogger(__name__)

async def individual_overview_by_account(
    db,
    request: Request,
):
    try:
        input_body = await request.json()

        from_date = input_body.get("from_date")
        to_date = input_body.get("to_date")
        account_number = input_body.get("account_number")

        if not from_date or not to_date or not account_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "from_date, to_date, account_number is required"
                }
            )

        logger.info(
            "bank_statement_report.start | account_number=%s",
            account_number
        )


        # ---------------------------------------------------------
        # 1. Parse date filters
        # ---------------------------------------------------------
        from_dt = datetime.strptime(
            from_date,
            "%Y-%m-%d"
        ).replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        to_dt = datetime.strptime(
            to_date,
            "%Y-%m-%d"
        ).replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        # ---------------------------------------------------------
        # 2. Build monthly date filter
        # ---------------------------------------------------------
        filter_conditions = [
            {
                "$gte": [
                    "$$row.v.parsedMonthDate",
                    from_dt
                ]
            },
            {
                "$lte": [
                    "$$row.v.parsedMonthDate",
                    to_dt
                ]
            }
        ]

        filter_expression = {
            "$and": filter_conditions
        }

        # ---------------------------------------------------------
        # 3. Fetch Overview based on account number
        # ---------------------------------------------------------
        pipeline = [
            {
                "$match": {
                    "account_details.Account Number": str(account_number)
                }
            },

            {
                "$project": {
                    "_id": 0,
                    "account_number": "$account_details.Account Number",
                    "merged_reference_id": 1,

                    "OverView": {
                        "$ifNull": [
                            "$analysis_metadata.Data.OverView",
                            {}
                        ]
                    }
                }
            },

            # -----------------------------------------------------
            # Convert OverView object into array
            #
            # {
            #   "Jan 2026": {...},
            #   "Feb 2026": {...}
            # }
            #
            # becomes
            #
            # [
            #   {"k": "Jan 2026", "v": {...}},
            #   {"k": "Feb 2026", "v": {...}}
            # ]
            # -----------------------------------------------------
            {
                "$addFields": {
                    "OverViewArray": {
                        "$objectToArray": "$OverView"
                    }
                }
            },

            # -----------------------------------------------------
            # Count total available months and filter requested range
            # -----------------------------------------------------
            {
                "$addFields": {
                    "OverViewCount": {
                        "$size": "$OverViewArray"
                    },

                    "FilteredOverView": {
                        "$filter": {
                            "input": "$OverViewArray",
                            "as": "row",
                            "cond": filter_expression
                        }
                    }
                }
            },

            # -----------------------------------------------------
            # Convert filtered array back to actual monthly objects
            # -----------------------------------------------------
            {
                "$project": {
                    "_id": 0,
                    "account_number": 1,
                    "merged_reference_id": 1,
                    "OverViewCount": 1,

                    "OverView": {
                        "$map": {
                            "input": "$FilteredOverView",
                            "as": "row",
                            "in": "$$row.v"
                        }
                    }
                }
            }
        ]

        cursor = db.bsa_merged_bankstatements.aggregate(pipeline)

        results = await cursor.to_list(length=1)

        # ---------------------------------------------------------
        # 4. Validate account/report exists
        # ---------------------------------------------------------
        if not results:
            logger.warning(
                "bank_statement_report.not_found | account_number=%s",
                account_number
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Bank statement report not found "
                        "for this account number"
                    )
                }
            )

        doc = results[0]

        # ---------------------------------------------------------
        # 5. Validate Overview exists
        # ---------------------------------------------------------
        if doc.get("OverViewCount", 0) == 0:
            logger.warning(
                "bank_statement_report.empty_overview | "
                "account_number=%s",
                account_number
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "No monthly overview data found"
                }
            )

        monthly_rows = doc.get("OverView", [])

        # ---------------------------------------------------------
        # 6. Validate requested date range
        # ---------------------------------------------------------
        if not monthly_rows:
            logger.warning(
                "bank_statement_report.no_rows_in_range | "
                "account_number=%s",
                account_number
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "No data found for the given date range"
                }
            )

        # ---------------------------------------------------------
        # 7. Calculate consolidated report
        # ---------------------------------------------------------
        consolidated = _compute_individual_bank_account_monthly_rows(monthly_rows)

        # ---------------------------------------------------------
        # 8. Clean None values
        # ---------------------------------------------------------
        cleaned_rows = []

        for row in monthly_rows:
            cleaned_rows.append({
                key: (
                    value
                    if value is not None
                    else 0.0
                )
                for key, value in row.items()
            })

        # ---------------------------------------------------------
        # 9. Logging
        # ---------------------------------------------------------

        logger.info(
            "bank_statement_report.success | "
            "account_number=%s | duration_ms=%.2f",
            account_number,
        )

        # ---------------------------------------------------------
        # 10. Response
        # ---------------------------------------------------------
        return {
            "status":"success",
            "message":"overview report fetched successfully",
            "data":{
            "consolidated_overall_report": consolidated,
            "monthly_breakdown": cleaned_rows
            }
        }

    except JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid input body"
            }
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        logger.exception(
            "Error raised at individual overview controller | "
            "account_number=%s",
            account_number if "account_number" in locals() else None
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal Server Error"
            })

async def individual_eod_by_account(
    db,
    request: Request
) -> dict:
    """
    Fetch and consolidate EOD month-wise analysis for an individual
    bank account.

    Flow:
        account_number
            ↓
        bsa_merged_bankstatements
            ↓
        EOD Month Wise
            ↓
        date filtering
            ↓
        monthly EOD consolidation
            ↓
        consolidated EOD report
    """

    try:

        # =========================================================
        # 1. Read request body
        # =========================================================

        input_body = await request.json()

        # =========================================================
        # 2. Validate input
        # =========================================================

        from_date = input_body.get("from_date")
        to_date = input_body.get("to_date")
        account_number = input_body.get("account_number")

        if not from_date or not to_date or not account_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": (
                        "from_date, to_date, account_number "
                        "is required"
                    )
                }
            )

        logger.info(
            "individual_eod.start | account_number=%s | "
            "from_date=%s | to_date=%s",
            account_number,
            from_date,
            to_date,
        )

        # =========================================================
        # 3. Parse dates
        # =========================================================

        try:
            from_dt = datetime.strptime(
                from_date,
                "%Y-%m-%d"
            ).replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

            to_dt = datetime.strptime(
                to_date,
                "%Y-%m-%d"
            ).replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": (
                        "Invalid date format. "
                        "Expected YYYY-MM-DD"
                    )
                }
            )

        # =========================================================
        # 4. Validate date range
        # =========================================================

        if from_dt > to_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": (
                        "from_date cannot be greater than to_date"
                    )
                }
            )

        # =========================================================
        # 5. MongoDB aggregation
        # =========================================================

        pipeline = [
            {
                "$match": {
                    "account_details.Account Number": account_number

                }
            },

            {
                "$project": {
                    "_id": 0,

                    "account_number": (
                        "$account_details.Account Number"
                    ),

                    "merged_reference_id": 1,

                    "eod_month_wise": {
                        "$ifNull": [
                            "$analysis_metadata.Data.Eod analysis.EOD MONTH WISE",
                            []
                        ]
                    }
                }
            },

            {
                "$addFields": {
                    "filtered_eod": {
                        "$filter": {
                            "input": "$eod_month_wise",
                            "as": "row",
                            "cond": {
                                "$and": [
                                    {
                                        "$gte": [
                                            "$$row.parsedMonthDate",
                                            from_dt
                                        ]
                                    },
                                    {
                                        "$lte": [
                                            "$$row.parsedMonthDate",
                                            to_dt
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                }
            },

            {
                "$project": {
                    "_id": 0,
                    "account_number": 1,
                    "merged_reference_id": 1,
                    "eod_month_wise": "$filtered_eod"
                }
            }
        ]

        # =========================================================
        # 6. Execute aggregation
        # =========================================================

        cursor = db.bsa_merged_bankstatements.aggregate(
            pipeline
        )

        results = await cursor.to_list(length=1)

        print("Db call result",results)

        # =========================================================
        # 7. Validate account/report exists
        # =========================================================

        if not results:
            logger.warning(
                "individual_eod.not_found | account_number=%s",
                account_number,
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Bank statement report not found "
                        "for this account number"
                    )
                }
            )

        doc = results[0]

        # =========================================================
        # 8. Get monthly EOD rows
        # =========================================================

        monthly_rows = doc.get(
            "eod_month_wise",
            []
        )

        if not monthly_rows:
            logger.warning(
                "individual_eod.no_data_in_range | "
                "account_number=%s | from_date=%s | to_date=%s",
                account_number,
                from_date,
                to_date,
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "No EOD data found for the "
                        "given date range"
                    )
                }
            )

        # =========================================================
        # 9. Sort rows chronologically
        # =========================================================

        monthly_rows = sorted(
            monthly_rows,
            key=lambda row: row.get(
                "parsedMonthDate"
            )
        )

        # =========================================================
        # 10. Compute consolidated EOD
        # =========================================================

        consolidated_eod = (
            _compute_individual_bank_account_eod(
                monthly_rows
            )
        )

        # =========================================================
        # 11. Clean monthly rows
        # =========================================================

        cleaned_monthly_rows = []

        for row in monthly_rows:

            cleaned_row = {}

            for key, value in row.items():

                if value is None:
                    cleaned_row[key] = 0.0

                elif isinstance(value, Decimal):
                    cleaned_row[key] = float(value)

                else:
                    cleaned_row[key] = value

            cleaned_monthly_rows.append(
                cleaned_row
            )

        # =========================================================
        # 12. Logging
        # =========================================================


        logger.info(
            "individual_eod.success | "
            "account_number=%s | months=%s | "
            "duration_ms=%.2f",
            account_number,
            len(monthly_rows)
        )

        # =========================================================
        # 13. Final response
        # =========================================================

        return {
            "status":"success",
            "message":"Eod analysis fetched successfully",

            "data":{

            "consolidated_eod": consolidated_eod,

            "monthly_breakdown": cleaned_monthly_rows,
            }
        }

    # =============================================================
    # JSON parsing error
    # =============================================================

    except JSONDecodeError:

        logger.exception(
            "individual_eod.invalid_json"
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid input body"
            }
        )

    # =============================================================
    # HTTP exceptions raised intentionally by business logic
    # =============================================================

    except HTTPException:
        raise

    # =============================================================
    # Unexpected exceptions
    # =============================================================

    except Exception as e:

        logger.exception(
            "individual_eod.error | account_number=%s | error=%s",
            account_number if "account_number" in locals() else None,
            str(e),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal Server Error"
            }
        )

async def individual_loan_transaction_by_account(db,request):
    try:
        # =========================================================
        # 1. Read request body
        # =========================================================

        input_body = await request.json()

        # =========================================================
        # 2. Validate input
        # =========================================================

        account_number = input_body.get("account_number")

        if not account_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": (
                        "account_number is required"
                    )
                }
            )
        pipeline = [
            {
                "$match": {
                    "account_details.Account Number": account_number
                }
            },
            {
                "$project": {
                    "_id": 0,

                    "summary_of_loan_trans": {
                        "$map": {
                            "input": {
                                "$ifNull": [
                                    "$analysis_metadata.Data.Loan Transactions.Summary Of Loan Tranx",
                                    []
                                ]
                            },
                            "as": "summary_of_loan_transactions",
                            "in": {
                                # Include only the fields you actually need
                                "month": "$$summary_of_loan_transactions.Month",
                                "Debit": "$$summary_of_loan_transactions.Debit",
                                "Credit": "$$summary_of_loan_transactions.Credit"
                            }
                        }
                    },

                    "details_of_loan_transaction": {
                        "$map": {
                            "input": {
                                "$ifNull": [
                                    "$analysis_metadata.Data.Loan Transactions.Details Of Loan Transactions",
                                    []
                                ]
                            },
                            "as": "details_of_loan_transaction",
                            "in": {
                                # Include only the fields you need
                                "date": "$$details_of_loan_transaction.Date",
                                "particulars": "$$details_of_loan_transaction.Particular",
                                "Debit": "$$details_of_loan_transaction.Debit",
                                "Credit": "$$details_of_loan_transaction.Credit"
                            }
                        }
                    }
                }
            }
        ]

        docs = await db.bsa_merged_bankstatements.aggregate(
            pipeline
        ).to_list(length=1)

        return  {"status":"success",
            "message":"Loan transaction data fetched successfully","data":docs}
    except JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail={"message":"Invalid input body"})
    except HTTPException:
        raise
    except Exception as e:
        print("Error raised",e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal Server Error"
            }
        )



def _compute_individual_bank_account_monthly_rows(
    monthly_rows: list
) -> dict:

    if not monthly_rows:
        return {}

    def decimal_value(row, field):
        value = row.get(field)

        if value is None:
            return Decimal("0")

        return _safe_decimal(value)

    # ---------------------------------------------------------
    # Accumulators
    # ---------------------------------------------------------

    totals = {
        # Receipts
        "CashDeposit": Decimal("0"),
        "ChequeReceipts": Decimal("0"),
        "OnlineReceipts": Decimal("0"),
        "BankInstrumentReceipt": Decimal("0"),
        "ForexRemittanceReceipt": Decimal("0"),
        "RefundReversal": Decimal("0"),
        "OtherReceipts": Decimal("0"),

        # Income Receipts
        "SalaryIncome": Decimal("0"),
        "RentIncome": Decimal("0"),
        "InterestIncome": Decimal("0"),

        # Financial Receipts
        "LoanReceived": Decimal("0"),
        "InsuranceReceipt": Decimal("0"),
        "InvestmentReceipt": Decimal("0"),

        # Expenses
        "ExternalPayments": Decimal("0"),
        "CashWithdrawals": Decimal("0"),
        "ChequePayments": Decimal("0"),
        "OnlinePayments": Decimal("0"),
        "BankInstrumentPayment": Decimal("0"),
        "ForexRemittancePayment": Decimal("0"),
        "OtherPayments": Decimal("0"),

        # Maintenance Payments
        "RentPayment": Decimal("0"),
        "UtilityPayment": Decimal("0"),
        "SalaryPayment": Decimal("0"),
        "POSExpenses": Decimal("0"),
        "CreditCardPayments": Decimal("0"),
        "GoodsPurchase": Decimal("0"),
        "BankCharges": Decimal("0"),

        # Financial Payments
        "LoanRepayment": Decimal("0"),
        "InsurancePayment": Decimal("0"),
        "InterestPayment": Decimal("0"),
        "InvestmentExpense": Decimal("0"),
        "Tax": Decimal("0"),

        # Savings
        "MonthlySavings": Decimal("0"),
    }

    # ---------------------------------------------------------
    # Process every month
    # ---------------------------------------------------------

    for row in monthly_rows:

        # -----------------------------
        # Receipts
        # -----------------------------

        totals["CashDeposit"] += decimal_value(
            row, "CashDeposit"
        )

        totals["ChequeReceipts"] += decimal_value(
            row, "ChequeReceipts"
        )

        totals["OnlineReceipts"] += decimal_value(
            row, "OnlineReceipts"
        )

        totals["BankInstrumentReceipt"] += decimal_value(
            row, "BankInstrument"
        )

        totals["ForexRemittanceReceipt"] += decimal_value(
            row, "ForexRemittance"
        )

        totals["RefundReversal"] += decimal_value(
            row, "RefundReversal"
        )

        totals["OtherReceipts"] += decimal_value(
            row, "OtherReceipts"
        )

        # -----------------------------
        # Income Receipts
        # -----------------------------

        totals["SalaryIncome"] += decimal_value(
            row, "SalaryIncome"
        )

        totals["RentIncome"] += decimal_value(
            row, "RentIncome"
        )

        totals["InterestIncome"] += decimal_value(
            row, "InterestIncome"
        )

        # -----------------------------
        # Financial Receipts
        # -----------------------------

        totals["LoanReceived"] += decimal_value(
            row, "LoanReceived"
        )

        totals["InsuranceReceipt"] += decimal_value(
            row, "Insurance"
        )

        totals["InvestmentReceipt"] += decimal_value(
            row, "InvestmentReceipt"
        )

        # -----------------------------
        # Expenses
        # -----------------------------

        totals["ExternalPayments"] += decimal_value(
            row, "ExternalPayments"
        )

        totals["CashWithdrawals"] += decimal_value(
            row, "CashWithdrawals"
        )

        totals["ChequePayments"] += decimal_value(
            row, "ChequePayments"
        )

        totals["OnlinePayments"] += decimal_value(
            row, "OnlinePayments"
        )

        totals["BankInstrumentPayment"] += decimal_value(
            row, "BankInstrument"
        )

        totals["ForexRemittancePayment"] += decimal_value(
            row, "ForexRemittance"
        )

        totals["OtherPayments"] += decimal_value(
            row, "OtherPayments"
        )

        # -----------------------------
        # Maintenance Payments
        # -----------------------------

        totals["RentPayment"] += decimal_value(
            row, "RentPayment"
        )

        totals["UtilityPayment"] += decimal_value(
            row, "UtilityPayment"
        )

        totals["SalaryPayment"] += decimal_value(
            row, "SalaryPayment"
        )

        totals["POSExpenses"] += decimal_value(
            row, "POSExpenses"
        )

        totals["CreditCardPayments"] += decimal_value(
            row, "CreditCardPayments"
        )

        totals["GoodsPurchase"] += decimal_value(
            row, "GoodsPurchase"
        )

        totals["BankCharges"] += decimal_value(
            row, "BankCharges"
        )

        # -----------------------------
        # Financial Payments
        # -----------------------------

        totals["LoanRepayment"] += decimal_value(
            row, "LoanRepayment"
        )

        totals["InsurancePayment"] += decimal_value(
            row, "Insurance"
        )

        totals["InterestPayment"] += decimal_value(
            row, "Interest"
        )

        totals["InvestmentExpense"] += decimal_value(
            row, "InvestmentExpense"
        )

        totals["Tax"] += decimal_value(
            row, "Tax"
        )

        # -----------------------------
        # Monthly Savings
        # -----------------------------

        totals["MonthlySavings"] += decimal_value(
            row, "MonthlySavings"
        )

    # ---------------------------------------------------------
    # Derived calculations
    # ---------------------------------------------------------

    total_receipts = (
        totals["CashDeposit"]
        + totals["ChequeReceipts"]
        + totals["OnlineReceipts"]
        + totals["BankInstrumentReceipt"]
        + totals["ForexRemittanceReceipt"]
        + totals["RefundReversal"]
        + totals["OtherReceipts"]
        + totals["SalaryIncome"]
        + totals["RentIncome"]
        + totals["InterestIncome"]
        + totals["LoanReceived"]
        + totals["InsuranceReceipt"]
        + totals["InvestmentReceipt"]
    )

    total_expenses = (
        totals["ExternalPayments"]
        + totals["RentPayment"]
        + totals["UtilityPayment"]
        + totals["SalaryPayment"]
        + totals["POSExpenses"]
        + totals["CreditCardPayments"]
        + totals["GoodsPurchase"]
        + totals["BankCharges"]
        + totals["LoanRepayment"]
        + totals["InsurancePayment"]
        + totals["InterestPayment"]
        + totals["InvestmentExpense"]
        + totals["Tax"]
    )

    # ---------------------------------------------------------
    # Opening / Closing balance
    # ---------------------------------------------------------

    opening_balance = decimal_value(
        monthly_rows[0],
        "OpeningBalance"
    )

    closing_balance = decimal_value(
        monthly_rows[-1],
        "ClosingBalance"
    )

    monthly_savings = (
        total_receipts - total_expenses
    )

    # ---------------------------------------------------------
    # Return report
    # ---------------------------------------------------------

    return {
        "receipts": {
            "cash_deposit": float(
                totals["CashDeposit"]
            ),
            "cheque_receipts": float(
                totals["ChequeReceipts"]
            ),
            "online_receipts": float(
                totals["OnlineReceipts"]
            ),
            "bank_instrument": float(
                totals["BankInstrumentReceipt"]
            ),
            "forex_remittance": float(
                totals["ForexRemittanceReceipt"]
            ),
            "refund_reversal": float(
                totals["RefundReversal"]
            ),
            "other_receipts": float(
                totals["OtherReceipts"]
            ),
        },

        "income_receipts": {
            "salary_income": float(
                totals["SalaryIncome"]
            ),
            "rent_income": float(
                totals["RentIncome"]
            ),
            "interest_income": float(
                totals["InterestIncome"]
            ),
        },

        "financial_receipts": {
            "loan_received": float(
                totals["LoanReceived"]
            ),
            "insurance": float(
                totals["InsuranceReceipt"]
            ),
            "investment_receipt": float(
                totals["InvestmentReceipt"]
            ),
        },

        "total_receipts": float(
            total_receipts
        ),

        "expenses": {
            "external_payments": float(
                totals["ExternalPayments"]
            ),
            "cash_withdrawals": float(
                totals["CashWithdrawals"]
            ),
            "cheque_payments": float(
                totals["ChequePayments"]
            ),
            "online_payments": float(
                totals["OnlinePayments"]
            ),
            "bank_instrument": float(
                totals["BankInstrumentPayment"]
            ),
            "forex_remittance": float(
                totals["ForexRemittancePayment"]
            ),
            "other_payments": float(
                totals["OtherPayments"]
            ),
        },

        "maintenance_payments": {
            "rent_payment": float(
                totals["RentPayment"]
            ),
            "utility_payment": float(
                totals["UtilityPayment"]
            ),
            "salary_payment": float(
                totals["SalaryPayment"]
            ),
            "pos_expenses": float(
                totals["POSExpenses"]
            ),
            "credit_card_payments": float(
                totals["CreditCardPayments"]
            ),
            "goods_purchase": float(
                totals["GoodsPurchase"]
            ),
            "bank_charges": float(
                totals["BankCharges"]
            ),
        },

        "financial_payments": {
            "loan_repayment": float(
                totals["LoanRepayment"]
            ),
            "insurance": float(
                totals["InsurancePayment"]
            ),
            "interest": float(
                totals["InterestPayment"]
            ),
            "investment_expense": float(
                totals["InvestmentExpense"]
            ),
            "tax": float(
                totals["Tax"]
            ),
        },

        "total_expenses": float(
            total_expenses
        ),

        "monthly_savings": float(
            monthly_savings
        ),

        "opening_balance": float(
            opening_balance
        ),

        "closing_balance": float(
            closing_balance
        ),
    }
def _compute_individual_bank_account_eod(
    monthly_rows: list,
) -> dict:
    """
    Consolidate EOD data from monthly rows.
    """

    if not monthly_rows:
        return {}

    # =========================================================
    # Helper
    # =========================================================

    def decimal_value(
        row: dict,
        field: str,
    ) -> Decimal:

        value = row.get(field)

        if value is None or value == "":
            return Decimal("0")

        return _safe_decimal(value)

    def rounded(value: Decimal, places: int = 2) -> float:
        """
        Convert Decimal to float and round to required
        decimal places.
        """
        return round(float(value), places)

    # =========================================================
    # Ensure chronological order
    # =========================================================

    monthly_rows = sorted(
        monthly_rows,
        key=lambda row: row.get("parsedMonthDate")
    )

    num_months = len(monthly_rows)

    # =========================================================
    # Opening / Closing balance
    # =========================================================

    opening_balance = decimal_value(
        monthly_rows[0],
        "openingBalance",
    )

    closing_balance = decimal_value(
        monthly_rows[-1],
        "closingbalance",
    )

    # =========================================================
    # Average EOD
    # =========================================================

    average_eod_sum = Decimal("0")

    for row in monthly_rows:
        average_eod_sum += decimal_value(
            row,
            "averageEod",
        )

    average_eod = (
        average_eod_sum
        / Decimal(str(num_months))
    )

    # =========================================================
    # Maximum / Minimum EOD
    # =========================================================

    max_eod = None
    max_eod_date = "N/A"

    min_eod = None
    min_eod_date = "N/A"

    # =========================================================
    # EOD by income
    # =========================================================

    max_eod_by_income = None
    min_eod_by_income = None

    # =========================================================
    # EOD bucket fields
    # =========================================================

    eod_bucket_fields = [
        "oneEod",
        "fiveEod",
        "tenEod",
        "fifteenEod",
        "twentyEod",
        "twentyfiveEod",
        "lastDay",
    ]

    eod_bucket_sums = {
        field: Decimal("0")
        for field in eod_bucket_fields
    }

    # =========================================================
    # Process monthly rows
    # =========================================================

    for row in monthly_rows:

        # -----------------------------------------------------
        # Max EOD
        # -----------------------------------------------------

        current_max_eod = decimal_value(
            row,
            "MaxEod",
        )

        if (
            max_eod is None
            or current_max_eod > max_eod
        ):
            max_eod = current_max_eod

            max_eod_date = row.get(
                "maxEodDate",
                "N/A",
            )

        # -----------------------------------------------------
        # Min EOD
        # -----------------------------------------------------

        current_min_eod = decimal_value(
            row,
            "minEod",
        )

        if (
            min_eod is None
            or current_min_eod < min_eod
        ):
            min_eod = current_min_eod

            min_eod_date = row.get(
                "minEodDate",
                "N/A",
            )

        # -----------------------------------------------------
        # Max EOD by income
        # -----------------------------------------------------

        current_max_eod_by_income = decimal_value(
            row,
            "maxEodByIncome",
        )

        if (
            max_eod_by_income is None
            or current_max_eod_by_income
            > max_eod_by_income
        ):
            max_eod_by_income = (
                current_max_eod_by_income
            )

        # -----------------------------------------------------
        # Min EOD by income
        # -----------------------------------------------------

        current_min_eod_by_income = decimal_value(
            row,
            "minEodByIncome",
        )

        if (
            min_eod_by_income is None
            or current_min_eod_by_income
            < min_eod_by_income
        ):
            min_eod_by_income = (
                current_min_eod_by_income
            )

        # -----------------------------------------------------
        # EOD buckets
        # -----------------------------------------------------

        for field in eod_bucket_fields:

            eod_bucket_sums[field] += (
                decimal_value(
                    row,
                    field,
                )
            )

    # =========================================================
    # Average EOD bucket values
    # =========================================================

    eod_bucket_averages = {}

    for field in eod_bucket_fields:

        eod_bucket_averages[field] = (
            eod_bucket_sums[field]
            / Decimal(str(num_months))
        )

    # =========================================================
    # Final response
    # =========================================================

    return {
        "opening_balance": rounded(
            opening_balance
        ),

        "max_eod": rounded(
            max_eod
            if max_eod is not None
            else Decimal("0")
        ),

        "min_eod": rounded(
            min_eod
            if min_eod is not None
            else Decimal("0")
        ),

        "average_eod": rounded(
            average_eod
        ),

        "closing_balance": rounded(
            closing_balance
        ),

        "max_eod_date": max_eod_date,

        "min_eod_date": min_eod_date,

        "max_eod_by_income": rounded(
            max_eod_by_income
            if max_eod_by_income is not None
            else Decimal("0")
        ),

        "min_eod_by_income": rounded(
            min_eod_by_income
            if min_eod_by_income is not None
            else Decimal("0")
        ),

        "eod_buckets": {
            "one_eod": rounded(
                eod_bucket_averages["oneEod"]
            ),

            "five_eod": rounded(
                eod_bucket_averages["fiveEod"]
            ),

            "ten_eod": rounded(
                eod_bucket_averages["tenEod"]
            ),

            "fifteen_eod": rounded(
                eod_bucket_averages["fifteenEod"]
            ),

            "twenty_eod": rounded(
                eod_bucket_averages["twentyEod"]
            ),

            "twentyfive_eod": rounded(
                eod_bucket_averages["twentyfiveEod"]
            ),

            "last_day": rounded(
                eod_bucket_averages["lastDay"]
            ),
        },
    }
