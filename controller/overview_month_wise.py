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

# Month abbreviations as produced by Python's "%b" strftime (English/C locale).
# Used to translate each row's "Mon YYYY" Month string (e.g. "Jan 2024") into
# a real BSON date inside the aggregation pipeline. MongoDB's $dateFromString
# does not support %b/%B (named-month) format specifiers, so we look the
# abbreviation up ourselves and build the date with $dateFromParts instead.
_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


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


def _build_month_filter_cond(from_dt, to_dt):
    """
    Builds the $filter `cond` expression used inside the aggregation
    pipeline to keep only the OverView rows whose Month ("Mon YYYY", e.g.
    "Jan 2024") falls within [from_dt, to_dt].

    Each row's Month string is reconstructed into a real Date (day fixed at
    1) via $dateFromParts, then compared with >= / <=. This mirrors the
    previous Python-side behavior of datetime.strptime(m, "%b %Y") exactly,
    including the fact that a from_dt of e.g. 2024-01-15 still excludes the
    "Jan 2024" row (its reconstructed date is 2024-01-01, which is earlier
    than 2024-01-15).

    Returns the literal True when no bounds are given, so $filter keeps
    every row untouched (same as skipping the filter entirely).
    """
    if not from_dt and not to_dt:
        return True

    month_abbr = {"$substrCP": ["$$row.Month", 0, 3]}
    year_num = {"$toInt": {"$substrCP": ["$$row.Month", 4, 4]}}
    month_num = {"$add": [{"$indexOfArray": [_MONTH_ABBR, month_abbr]}, 1]}
    row_date = {"$dateFromParts": {"year": year_num, "month": month_num, "day": 1}}

    clauses = []
    if from_dt:
        clauses.append({"$gte": [row_date, from_dt]})
    if to_dt:
        clauses.append({"$lte": [row_date, to_dt]})

    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


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


async def bank_statement_report_consolidated_oldVersion(db, user_id: str, from_date: str = None, to_date: str = None):
    logger.info("bank_statement_report.start | user_id=%s", user_id)
    start_time = time.perf_counter()

    from_dt = datetime.strptime(from_date, "%Y-%m-%d") if from_date else None
    to_dt   = datetime.strptime(to_date,   "%Y-%m-%d") if to_date   else None

    # Optimized flow: $match(user_id) -> $project(required fields) ->
    # $filter(parsedMonthDate) -> only the required months ever leave Mongo.
    pipeline = [
        {"$match": {"user_id": str(user_id)}},
        {"$project": {
            "_id": 0,
            "merged_reference_id": 1,
            "OverView": {"$ifNull": ["$analysis_metadata.Data.OverView", []]},
        }},
        {"$addFields": {
            # Count BEFORE filtering, so we can still tell "no overview data
            # at all" apart from "no rows in the requested date range".
            "OverViewCount": {"$size": "$OverView"},
            "OverView": {
                "$filter": {
                    "input": "$OverView",
                    "as": "row",
                    "cond": _build_month_filter_cond(from_dt, to_dt),
                }
            },
        }},
    ]

    cursor = db.bsa_merged_bankstatements.aggregate(pipeline)
    results = await cursor.to_list(length=1)

    if not results:
        logger.warning("bank_statement_report.not_found | user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "bank_statement_report not found for this account"}
        )

    doc = results[0]

    if doc.get("OverViewCount", 0) == 0:
        logger.warning("bank_statement_report.empty_overview | user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "No monthly overview data found"}
        )

    monthly_rows: list = doc.get("OverView", [])

    if (from_dt or to_dt) and not monthly_rows:
        logger.warning("bank_statement_report.no_rows_in_range | user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "No data found for the given date range"}
        )

    # All math in Python
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


#######################################################
#Below code is the optimized for monthly overview (3rd module) - PrathamPai2004 :
########################################################


async def bank_statement_report_consolidated(db, user_id: str, from_date: str = None, to_date: str = None):
    logger.info("bank_statement_report.start | user_id=%s", user_id)
    start_time = time.perf_counter()

    from_dt = (
    datetime.strptime(from_date, "%Y-%m-%d")
    .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if from_date else None
    )

    to_dt = (
        datetime.strptime(to_date, "%Y-%m-%d")
        .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if to_date else None
    )

    filter_conditions = []

    if from_dt:
        filter_conditions.append({
            "$gte": [
                "$$row.parsedMonthDate",
                from_dt
            ]
        })

    if to_dt:
        filter_conditions.append({
            "$lte": [
                "$$row.parsedMonthDate",
                to_dt
            ]
        })

    filter_expression = (
        {"$and": filter_conditions}
        if filter_conditions
        else True
    )
    # Optimized flow: $match(user_id) -> $project(required fields) ->
    # $filter(parsedMonthDate) -> only the required months ever leave Mongo.
    pipeline = [
        {"$match": {"user_id": str(user_id)}},
        {"$project": {
            "_id": 0,
            "merged_reference_id": 1,
            "OverView": {"$ifNull": ["$analysis_metadata.Data.OverView", []]},
        }},
        {
            "$addFields": {
            # Count BEFORE filtering, so we can still tell "no overview data
            # at all" apart from "no rows in the requested date range".
            "OverViewCount": {"$size": "$OverView"},
            "OverView": {
                "$filter": {
                    "input": "$OverView",
                    "as": "row",
                    "cond": filter_expression
            },
        }
        }
        }
    ]

    cursor = db.bsa_merged_bankstatements.aggregate(pipeline)
    results = await cursor.to_list(length=1)

    if not results:
        logger.warning("bank_statement_report.not_found | user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "bank_statement_report not found for this account"}
        )

    doc = results[0]

    if doc.get("OverViewCount", 0) == 0:
        logger.warning("bank_statement_report.empty_overview | user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "No monthly overview data found"}
        )

    monthly_rows: list = doc.get("OverView", [])

    if (from_dt or to_dt) and not monthly_rows:
        logger.warning("bank_statement_report.no_rows_in_range | user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "No data found for the given date range"}
        )

    # All math in Python
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


async def r1xcrm_bank_statement_report_consolidated(db, acc_id: int,from_date,to_date):
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