from collections import defaultdict
import logging
import time
from fastapi import HTTPException
from starlette import status
from decimal import Decimal, InvalidOperation
from typing import Any
from datetime import datetime

from utils.scale_to_laksh import _scale_to_lakhs

logger = logging.getLogger(__name__)


def _safe_div(numerator, denominator, multiply=1, round_to=2):
    if not denominator:
        return 0.0
    return round((numerator / denominator) * multiply, round_to)

def _safe_decimal(val: Any) -> Decimal:
    """Safely convert ScoreMe string values to Decimal for precision math."""
    try:
        if val is None or val == "" or val == "-":
            return Decimal("0")
        # Remove commas if present in the string
        if isinstance(val, str):
            val = val.replace(",", "").strip()
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")
    

def _compute_report(monthly_rows: list) -> dict:
    """All aggregation done in Python from pre-aggregated monthly rows."""
    """
    Consolidates multiple rows into a single report using a single pass (O(n)).
    """
    if not monthly_rows:
        return {}

    # 1. Initialize accumulators for all numeric fields
    num_months = len(monthly_rows)
    totals = defaultdict(Decimal)
    peak_val = Decimal("-Infinity")
    peak_date = "N/A"

    chq_received_sum_no = Decimal("0")
    chq_paid_sum_no = Decimal("0")

    # 2. SINGLE PASS: The "Everything Loop"
    for r in monthly_rows:
        
        summable_keys = [
            "TotalCredit", "TotalCreditNo", "TotalDebit", "TotalDebitNo",
            "OutwardChequeReturn", "ReversalOfInwardChequeReturn", "ReversalOfOnlineReturn",
            "Contra", "LoanReceived", "InhouseCredit", "InwardChequeReturn",
            "ReversalOfOutwardChequeReturn", "OnlineReturn", "InhouseDebit",
            "InwardChequeReturnNos", "OutwardChequeReturnNo", "InwardOnlineReturnNo",
            "OutwardOnlineReturnNo", "EcsReturnNo", "EcsPayment", "InhouseCreditNos",
            "InhouseDebitNos", "LoanRepaid", "NoOfUniqueEcs", "InterestPaid"
        ]
        for key in summable_keys:
            totals[key] += _safe_decimal(r.get(key, 0))

        avg_keys = [
            "AverageEod", "OdccLimit", "OdccDrawingLimit", 
            "OverDrawnAverageinRsMn", "OverDrawnAverageAsPercentOfOdCCLimit"
        ]

        for key in avg_keys:
            totals[f"SUM_{key}"] += _safe_decimal(r.get(key, 0))


        current_peak = _safe_decimal(r.get("PeakOverDrawingAmount", 0))
        if current_peak > peak_val:
            peak_val = current_peak
            peak_date = r.get("PeakOverDrawingDate", "N/A")
        
        if _safe_decimal(r.get("InwardChequeReturnNos", 0)) > 0:
            chq_received_sum_no += _safe_decimal(r.get("TotalCreditNo", 0))
        if _safe_decimal(r.get("OutwardChequeReturnNos", 0)) > 0:
            chq_paid_sum_no += _safe_decimal(r.get("TotalDebitNo", 0))
        
    # 3. Intermediate Calculations (Logic Layer)
    # Using the totals dict now instead of re-looping
    gross_credits = totals["TotalCredit"] - (
        totals["OutwardChequeReturn"] + totals["ReversalOfInwardChequeReturn"] + totals["ReversalOfOnlineReturn"]
    )
    net_credits = gross_credits - totals["Contra"] - totals["LoanReceived"]
    net_cash_inflow = net_credits - totals["InhouseCredit"]

    gross_debits = totals["TotalDebit"] - (
        totals["InwardChequeReturn"] + totals["ReversalOfOutwardChequeReturn"] + totals["OnlineReturn"]
    )
    net_debits_g = gross_debits - totals["Contra"]
    net_cash_outflow = net_debits_g - totals["InhouseDebit"]

    return {
        "overview": {
            # Convert both to float here
            "average_credit_tranx": _scale_to_lakhs(
                totals["TotalCredit"] / totals["TotalCreditNo"] if totals["TotalCreditNo"] else Decimal("0")
            ),
            "total_credit_nos":     float(totals["TotalCreditNo"]),
            "average_debit_tranx":  _scale_to_lakhs(
                totals["TotalDebit"] / totals["TotalDebitNo"] if totals["TotalDebitNo"] else Decimal("0")
            ),
            "total_debit_nos":      float(totals["TotalDebitNo"]),
        },
        "cash_inflow": {
            "total_credits_a":                _scale_to_lakhs(totals["TotalCredit"]),
            "outward_cheque_return_b":         _scale_to_lakhs(totals["OutwardChequeReturn"]),
            "reversal_inward_cheque_return_c": _scale_to_lakhs(totals["ReversalOfInwardChequeReturn"]),
            "reversal_online_return_d":        _scale_to_lakhs(totals["ReversalOfOnlineReturn"]),
            "gross_credits_e":                 _scale_to_lakhs(gross_credits),
            "contra_f":                         _scale_to_lakhs(totals["Contra"]),
            "loan_received_g":                 _scale_to_lakhs(totals["LoanReceived"]),
            "net_credits_h":                   _scale_to_lakhs(net_credits),
            "inhouse_credit_i":                _scale_to_lakhs(totals["InhouseCredit"]),
            "net_cash_inflow_j":               _scale_to_lakhs(net_cash_inflow),
        },
        "cash_outflow": {
            "total_debits_a":                   _scale_to_lakhs(totals["TotalDebit"]),
            "inward_cheque_return_b":            _scale_to_lakhs(totals["InwardChequeReturn"]),
            "reversal_outward_cheque_return_c":  _scale_to_lakhs(totals["ReversalOfOutwardChequeReturn"]),
            "online_return_d":                   _scale_to_lakhs(totals["OnlineReturn"]),
            "gross_debits_e":                    _scale_to_lakhs(gross_debits),
            "contra_f":                          _scale_to_lakhs(totals["Contra"]),
            "net_debits_g":                      _scale_to_lakhs(net_debits_g),
            "inhouse_debit_h":                   _scale_to_lakhs(totals["InhouseDebit"]),
            "net_cash_outflow":                  _scale_to_lakhs(net_cash_outflow),

        },
        "returns": {
            "inward_cheque_return_nos":      float(totals["InwardChequeReturnNos"]),
            "inward_cheque_return_percent":  _safe_div(float(totals["InwardChequeReturnNos"]), float(chq_received_sum_no), 100),
            "outward_cheque_return_nos":     float(totals["OutwardChequeReturnNos"]),
            "outward_cheque_return_percent": _safe_div(float(totals["OutwardChequeReturnNos"]), float(chq_paid_sum_no), 100),
            "inward_online_return_nos":      float(totals["InwardOnlineReturn"]),
            "inward_online_return_percent":  _safe_div(float(totals["InwardOnlineReturn"]), float(chq_received_sum_no), 100),
            "outward_online_return_nos":     float(totals["OutwardOnlineReturn"]),
            "outward_online_return_percent": _safe_div(float(totals["OutwardOnlineReturn"]), float(chq_paid_sum_no), 100),
            "ecs_return_nos":                float(totals["ECSReturn"]),
            # "ecs_return_percent":            _safe_div(float(totals["ECSReturn"]), float(totals["TotalECSPayment"]), 100),
        },
        "other_calculations": {
            "inhouse_credit_nos": float(totals["InhouseCreditNos"]),
            "inhouse_credit/total_percent": _safe_div(float(totals["InhouseCredit"]), float(totals["TotalCredit"]), 100),
            "inhouse_debit_nos": float(totals["InhouseDebitNos"]),
            "inhouse_debit/total_percent": _safe_div(float(totals["InhouseDebit"]), float(totals["TotalDebit"]), 100),
            "average_eod":              _scale_to_lakhs(totals["SUM_AverageEod"] / Decimal(str(num_months))),            
            "od_cc_sanction_limit":     _scale_to_lakhs(totals["SUM_OdccLimit"] / Decimal(str(num_months))),            
            "od/cc_drawing_power_limit": float(totals["OdccDrawingLimit"]),
            "average_od_&_cc_utilization_percent": _safe_div(float(totals["OdccDrawingLimit"]), float(totals["OdccLimit"]), 100),
            "no_of_days_limit_overdrawn": float(totals["NoOfDaysLimitOverdrawn"]),
            "no_of_times_limit_overdrawn": float(totals["NoOfTimesLimitOverdrawn"]),
            "overdrawn_amount_in_rs_mn_for_all_days": float(totals["OverdrawnAmountInRsMnForAllDays"]),
            "overdrawn_average_amount_in_rs_mn": float(totals["OverdrawnAverageAmountInRsMn"]),
            "overdrawn_average_as_percent_of_od/cc_limit": float(totals["OverdrawnAverageAsPercentOfOdccLimit"]),
            "peak_overdrawing_amount":  _scale_to_lakhs(peak_val if peak_val != Decimal("-Infinity") else Decimal("0")),            
            "peak_overdrawing_date": peak_date,
            "loan_repaid":              _scale_to_lakhs(totals["LoanRepaid"]),
            "ecs_payment":              _scale_to_lakhs(totals["EcsPayment"]),
            "no_of_unique_ecs/emis": float(totals["NoOfUniqueEcs"]),
            "interest_paid":            _scale_to_lakhs(totals["InterestPaid"]),
        },
    }


async def bank_statement_report_consolidated(db, user_id: str, from_date: str = None, to_date: str = None):
    print(f"DEBUG: Searching for user_id: '{user_id}' type: {type(user_id)}")
    logger.info("bank_statement_report.start | user_id=%s", user_id)
    
    start_time = time.perf_counter()
    raw_debug = await db.bsa_merged_bankstatements.find_one({"user_id": str(user_id)})    
    # ONE DB call — fetch only what we need
    doc = await db.bsa_merged_bankstatements.find_one(
        {"user_id": str(user_id)},
        projection={
            "merged_reference_id": 1,
            "analysis_metadata.Data.OverView": 1,
            "_id": 0,
        } 
    )

    if not doc:
        logger.warning("bank_statement_report.not_found | user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "bank_statement_report not found for this account"}
        )

    monthly_rows: list = doc.get("analysis_metadata", {}).get("Data", {}).get("OverView", [])

    if not monthly_rows:
        logger.warning("bank_statement_report.empty_overview | user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "No monthly overview data found"}
        )

    # Date filter in Python
    if from_date or to_date:
        

        def parse_month(m: str):
            return datetime.strptime(m, "%b %Y")

        from_dt = datetime.strptime(from_date, "%Y-%m-%d") if from_date else None
        to_dt   = datetime.strptime(to_date,   "%Y-%m-%d") if to_date   else None

        monthly_rows = [
            r for r in monthly_rows
            if (from_dt is None or parse_month(r["Month"]) >= from_dt)
            and (to_dt is None or parse_month(r["Month"]) <= to_dt)
        ]
        print(monthly_rows)
        if not monthly_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "No data found for the given date range"}
            )

    
    
    #  All math in Python
    consolidated = _compute_report(monthly_rows)
    # consolidated.update({
    #     "reference_id": doc.get("merged_reference_id",[]),
    #     "user_id":      str(user_id),
    #     "report_count": 1,
    # })
    cleaned_rows = []
    for r in monthly_rows:
        # This replaces any None with 0.0 for all fields in the row
        cleaned_rows.append({k: (v if v is not None else 0.0) for k, v in r.items()})
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info("bank_statement_report.success | user_id=%s | duration_ms=%.2f", user_id, elapsed_ms)

    return {
        "consolidated_overall_report": consolidated,
        "monthly_breakdown": cleaned_rows,
    }


async def get_crm_bank_statement_report(db, acc_id: int):
    if not acc_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "account id is required"}
        )
    user = await db["users"].find_one({"account_id": acc_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "account is not registered as user"}
        )
    return await bank_statement_report_consolidated(db, user["_id"])