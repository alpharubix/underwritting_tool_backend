from __future__ import annotations

import logging
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

# --- HELPERS ---

def parse_any_month(month_str: str) -> datetime | None:
    if not month_str:
        return None
    
    month_str = month_str.strip()

    if len(month_str) >= 7 and month_str[4] == "-" and month_str[:4].isdigit():
        try:
            return datetime.strptime(month_str[:7], "%Y-%m")
        except (ValueError, TypeError):
            pass

    formats = ["%b-%Y", "%m-%Y", "%b %Y", "%B %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(month_str, fmt)
        except (ValueError, TypeError):
            continue
            
    return None

def normalize_date_range(from_date: datetime, to_date: datetime):
            normalized_from = from_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            normalized_to   = to_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return normalized_from, normalized_to

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

# --- MAIN SERVICE ---

async def build_cashflow_report(db, user_id: str, from_month: str, to_month: str):
    # 1. Input Validation
    if not user_id or len(user_id.strip()) < 5:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    
    from_dt_raw = parse_any_month(from_month)
    to_dt_raw = parse_any_month(to_month)

    if not from_dt_raw or not to_dt_raw:
        raise HTTPException(
            status_code=400, 
            detail="Invalid month format. Use YYYY-MM, MMM-YYYY, or MM-YYYY"
        )

    from_dt, to_dt = normalize_date_range(from_dt_raw, to_dt_raw)
    
    if from_dt > to_dt:
        raise HTTPException(status_code=400, detail="from_month cannot be after to_month")

    # 2. Fetch documents from MongoDB
    query_start = from_dt.replace(tzinfo=timezone.utc)
    query_end = (to_dt + relativedelta(months=1)).replace(tzinfo=timezone.utc)

    query = {
        "user_id": user_id,
        "from_date": {"$lt": query_end},
        "to_date": {"$gte": query_start},
    }

    # Sort by created_at to ensure consistent latest-wins logic
    cursor = db["bankstatementreport"].find(query).sort("created_at", 1)
    docs = await cursor.to_list(length=None)

    if not docs:
        raise HTTPException(status_code=404, detail="No bank statements found for this range")

    # 3. Extract & Filter (Latest Upload Wins per month)
    final_monthly_map: dict[str, tuple[dict, datetime]] = {}

    for doc in docs:
        # FIX: Safe extraction of created_at (handling both dict and datetime object)
        created_at_raw = doc.get("created_at")
        if isinstance(created_at_raw, dict):
            created_at_val = created_at_raw.get("$date", created_at_raw)
        else:
            created_at_val = created_at_raw

        try:
            if isinstance(created_at_val, datetime):
                upload_ts = created_at_val.replace(tzinfo=timezone.utc) if created_at_val.tzinfo is None else created_at_val
            else:
                upload_ts = datetime.fromisoformat(str(created_at_val).replace("Z", "+00:00"))
        except:
            upload_ts = datetime.min.replace(tzinfo=timezone.utc)

        # Handle different potential analysis locations
        analysis = doc.get("analysis_metadata", {})
        raw_cashflow = (
            analysis.get("cashflow") or 
            analysis.get("Data", {}).get("Cash Flow")
        )

        if not raw_cashflow:
            continue

        if isinstance(raw_cashflow, str):
            try:
                raw_cashflow = json.loads(raw_cashflow)
            except:
                continue

        for row in raw_cashflow:
            m_str = row.get("month") or row.get("Month") or row.get("MONTH") or row.get("MonthYear")
            row_dt_raw = parse_any_month(m_str)
            if not row_dt_raw:
                continue

            row_dt, _ = normalize_date_range(row_dt_raw, row_dt_raw)
            
            if from_dt <= row_dt <= to_dt:
                ym_key = row_dt.strftime("%Y-%m")
                # Update map if this is the first time seeing this month or if this doc is newer
                if ym_key not in final_monthly_map or upload_ts >= final_monthly_map[ym_key][1]:
                    final_monthly_map[ym_key] = (row, upload_ts)

    if not final_monthly_map:
        raise HTTPException(status_code=404, detail="No usable cashflow data found in range")

    # 4. Aggregation and Summary Calculations
    totals = {
        "A_inflows": Decimal("0"),
        "B_outflows": Decimal("0"),
        "D_indirect_exp": Decimal("0"),
        "E_indirect_inc": Decimal("0"),
        "payables": Decimal("0"),
        "receivables": Decimal("0"),
        "accruals": Decimal("0"),
        "opening": Decimal("0"),
        "closing": Decimal("0")
    }

    formatted_data = []
    sorted_month_keys = sorted(final_monthly_map.keys())

    for i, ym_key in enumerate(sorted_month_keys):
        row, _ = final_monthly_map[ym_key]
        
        # Capture Boundaries: Opening balance of first month, Closing of last month
        if i == 0:
            totals["opening"] = _safe_decimal(row.get("OpeningBalance"))
        if i == len(sorted_month_keys) - 1:
            totals["closing"] = _safe_decimal(row.get("ClosingBalance"))

        # Inflows/Revenue: (A)
        totals["A_inflows"] += (
            _safe_decimal(row.get("CashDeposit")) + _safe_decimal(row.get("ChequeReceipt")) +
            _safe_decimal(row.get("OnlineReceipt")) + _safe_decimal(row.get("OtherReceipt"))
        )

        # OutFlows/Expenses: (B)
        totals["B_outflows"] += (
            _safe_decimal(row.get("CashWithdraw")) + _safe_decimal(row.get("ChequePayment")) +
            _safe_decimal(row.get("OnlinePayment")) + _safe_decimal(row.get("OtherPayment"))
        )

        # Indirect Expenses: (D)
        totals["D_indirect_exp"] += (
            _safe_decimal(row.get("SalaryPayment")) + _safe_decimal(row.get("InsurancePayment")) +
            _safe_decimal(row.get("RentPayment")) + _safe_decimal(row.get("CompanyExpense")) +
            _safe_decimal(row.get("BankCharge")) + _safe_decimal(row.get("UtilityExpense")) +
            _safe_decimal(row.get("TaxPaid")) + _safe_decimal(row.get("InterestPaid")) +
            _safe_decimal(row.get("RefundPayment")) + _safe_decimal(row.get("CreditCardPayment")) +
            _safe_decimal(row.get("ForexPayment"))
        )

        # Indirect Income: (E)
        totals["E_indirect_inc"] += (
            _safe_decimal(row.get("InterestReceived")) + _safe_decimal(row.get("TaxRefund")) +
            _safe_decimal(row.get("RentReceipt"))
        )

        # Payables
        totals["payables"] += (
            _safe_decimal(row.get("LoanPayment")) + _safe_decimal(row.get("workCapitalPayment")) +
            _safe_decimal(row.get("InvestmentPayment")) + _safe_decimal(row.get("ContraPayment")) +
            _safe_decimal(row.get("FiPayment")) + _safe_decimal(row.get("SweepOut")) +
            _safe_decimal(row.get("BankInstrumentPayment"))
        )
        
        # Receivables (G)
        totals["receivables"] += (
            _safe_decimal(row.get("LoanReceipt")) + _safe_decimal(row.get("WorkCapitalReceipt")) +
            _safe_decimal(row.get("InvestmentReceipt")) + _safe_decimal(row.get("InsuranceReceipt")) +
            _safe_decimal(row.get("ContraReceipt")) + _safe_decimal(row.get("FiReceipt")) +
            _safe_decimal(row.get("SweepIn"))
        )

        totals["accruals"] += _safe_decimal(row.get("BankAccural"))

        formatted_data.append(row)

    # Formula Results
    gross_profit_c = totals["A_inflows"] - totals["B_outflows"]
    net_profit_f = gross_profit_c - totals["D_indirect_exp"] + totals["E_indirect_inc"]

    # 5. Final Response
    return {
        "status": "success",
        "data":{
            "summary": {
                "inflows_revenue_a": float(totals["A_inflows"]),
                "outflows_expenses_b": float(totals["B_outflows"]),
                "gross_inflow_profit_c": float(gross_profit_c),
                "indirect_expenses_d": float(totals["D_indirect_exp"]),
                "indirect_income_e": float(totals["E_indirect_inc"]),
                "net_inflow_profit_f": float(net_profit_f),
                "total_payables": float(totals["payables"]),
                "total_receivables_g": float(totals["receivables"]),
                "bank_accruals": float(totals["accruals"]),
                "opening_balance": float(totals["opening"]),
                "closing_balance": float(totals["closing"]),
                "net_cashflow": float(totals["A_inflows"] - totals["B_outflows"])
            },
            "monthly_breakdown": formatted_data,
            
        }  
    }