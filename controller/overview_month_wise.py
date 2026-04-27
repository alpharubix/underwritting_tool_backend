import logging
import time
from fastapi import HTTPException
from starlette import status
from decimal import Decimal, InvalidOperation
from typing import Any

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

    sum_credit = sum(_safe_decimal(r.get("TotalCredit", 0)) for r in monthly_rows)
    cnt_credit = sum(_safe_decimal(r.get("TotalCreditNo", 0)) for r in monthly_rows)
    sum_debit  = sum(_safe_decimal(r.get("TotalDebit", 0)) for r in monthly_rows)
    cnt_debit  = sum(_safe_decimal(r.get("TotalDebitNo", 0)) for r in monthly_rows)

    # ── CASH INFLOW ────────────────────────────────────────────
    val_outward_chq_ret_cr   = sum(_safe_decimal(r.get("OutwardChequeReturn", 0)) for r in monthly_rows)
    val_inward_chq_ret_cr    = sum(_safe_decimal(r.get("ReversalOfInwardChequeReturn", 0)) for r in monthly_rows)
    val_inward_online_ret_cr = sum(_safe_decimal(r.get("ReversalOfOnlineReturn", 0)) for r in monthly_rows)
    gross_credits = sum_credit - (val_outward_chq_ret_cr + val_inward_chq_ret_cr + val_inward_online_ret_cr)

    # ── CASH OUTFLOW ───────────────────────────────────────────
    val_inward_chq_ret_dr    = sum(_safe_decimal(r.get("InwardChequeReturn", 0)) for r in monthly_rows)
    val_outward_chq_ret_dr   = sum(_safe_decimal(r.get("ReversalOfOutwardChequeReturn", 0)) for r in monthly_rows)
    val_outward_online_ret_dr = sum(_safe_decimal(r.get("OnlineReturn", 0)) for r in monthly_rows)
    val_contra_dr            = sum(_safe_decimal(r.get("Contra", 0)) for r in monthly_rows)
    val_inhouse_dr           = sum(_safe_decimal(r.get("InhouseDebit", 0)) for r in monthly_rows)

    gross_debits  = sum_debit - (val_inward_chq_ret_dr + val_outward_chq_ret_dr + val_outward_online_ret_dr)
    net_debits_g  = gross_debits - val_contra_dr
    net_cash_outflow = net_debits_g - val_inhouse_dr

    # ── RETURNS ────────────────────────────────────────────────
    nos_inward_chq_ret     = sum(_safe_decimal(r.get("InwardChequeReturnNos", 0)) for r in monthly_rows)
    nos_outward_chq_ret    = sum(_safe_decimal(r.get("OutwardChequeReturnNo", 0)) for r in monthly_rows)
    nos_inward_online_ret  = sum(_safe_decimal(r.get("InwardOnlineReturnNo", 0)) for r in monthly_rows)
    nos_outward_online_ret = sum(_safe_decimal(r.get("OutwardOnlineReturnNo", 0)) for r in monthly_rows)
    nos_ecs_return         = sum(_safe_decimal(r.get("EcsReturnNo", 0)) for r in monthly_rows)

    # Denominators for % — derive from monthly totals
    nos_total_chq_received = sum(_safe_decimal(r.get("TotalCreditNo", 0)) for r in monthly_rows if r.get("InwardChequeReturnNos", 0))
    nos_total_chq_paid     = sum(_safe_decimal(r.get("TotalDebitNo", 0)) for r in monthly_rows if r.get("OutwardChequeReturnNo", 0))
    nos_total_online_cr    = cnt_credit   # approximation — adjust if you have a dedicated field
    nos_total_online_dr    = cnt_debit
    nos_total_ecs_payment  = sum(_safe_decimal(r.get("EcsPayment", 0)) for r in monthly_rows)

    return {
        "overview": {
            # Convert both to float here
            "average_credit_tranx": _safe_div(float(sum_credit), float(cnt_credit)),
            "total_credit_nos":     float(cnt_credit),
            "average_debit_tranx":  _safe_div(float(sum_debit), float(cnt_debit)),
            "total_debit_nos":      float(cnt_debit),
        },
        "cash_inflow": {
            "total_credits_A":                float(round(sum_credit, 2)),
            "outward_cheque_return_B":         float(round(val_outward_chq_ret_cr, 2)),
            "reversal_inward_cheque_return_C": float(round(val_inward_chq_ret_cr, 2)),
            "reversal_online_return_D":        float(round(val_inward_online_ret_cr, 2)),
            "gross_credits_E":                 float(round(gross_credits, 2)),
        },
        "cash_outflow": {
            "total_debits_A":                   float(round(sum_debit, 2)),
            "inward_cheque_return_B":            float(round(val_inward_chq_ret_dr, 2)),
            "reversal_outward_cheque_return_C":  float(round(val_outward_chq_ret_dr, 2)),
            "online_return_D":                   float(round(val_outward_online_ret_dr, 2)),
            "gross_debits_E":                    float(round(gross_debits, 2)),
            "contra_F":                          float(round(val_contra_dr, 2)),
            "net_debits_G":                      float(round(net_debits_g, 2)),
            "inhouse_debit_H":                   float(round(val_inhouse_dr, 2)),
            "net_cash_outflow":                  float(round(net_cash_outflow, 2)),
        },
        "returns": {
            "inward_cheque_return_nos":      float(nos_inward_chq_ret),
            "inward_cheque_return_percent":  _safe_div(float(nos_inward_chq_ret), float(nos_total_chq_received), 100),
            "outward_cheque_return_nos":     float(nos_outward_chq_ret),
            "outward_cheque_return_percent": _safe_div(float(nos_outward_chq_ret), float(nos_total_chq_paid), 100),
            "inward_online_return_nos":      float(nos_inward_online_ret),
            "inward_online_return_percent":  _safe_div(float(nos_inward_online_ret), float(nos_total_online_cr), 100),
            "outward_online_return_nos":     float(nos_outward_online_ret),
            "outward_online_return_percent": _safe_div(float(nos_outward_online_ret), float(nos_total_online_dr), 100),
            "ecs_return_nos":                float(nos_ecs_return),
            "ecs_return_percent":            _safe_div(float(nos_ecs_return), float(nos_total_ecs_payment), 100),
        },
    }


async def bank_statement_report_consolidated(db, user_id: str, from_date: str = None, to_date: str = None):
    print(f"DEBUG: Searching for user_id: '{user_id}' type: {type(user_id)}")
    logger.info("bank_statement_report.start | user_id=%s", user_id)
    
    start_time = time.perf_counter()
    raw_debug = await db.bsa_merged_bankstatements.find_one({"user_id": str(user_id)})
    print(f"DEBUG: Raw document found: {raw_debug is not None}")
    
    # ✅ ONE DB call — fetch only what we need
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

    # ✅ Date filter in Python — zero DB cost
    if from_date or to_date:
        from datetime import datetime

        def parse_month(m: str):
            return datetime.strptime(m, "%b %Y")

        from_dt = datetime.strptime(from_date, "%Y-%m-%d") if from_date else None
        to_dt   = datetime.strptime(to_date,   "%Y-%m-%d") if to_date   else None

        monthly_rows = [
            r for r in monthly_rows
            if (from_dt is None or parse_month(r["Month"]) >= from_dt)
            and (to_dt is None or parse_month(r["Month"]) <= to_dt)
        ]

        if not monthly_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "No data found for the given date range"}
            )

    
    
    # ✅ All math in Python
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
        "Consolidated_OverAll_Report": consolidated,
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