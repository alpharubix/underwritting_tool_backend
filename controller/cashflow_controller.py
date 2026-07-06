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

    formats = ["%Y-%m", "%b-%Y", "%m-%Y", "%b %Y", "%B %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(month_str, fmt)
        except (ValueError, TypeError):
            continue
    return None

def normalize_date_range(from_date: datetime, to_date: datetime):
    normalized_from = from_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    normalized_to = to_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return normalized_from, normalized_to

def _safe_decimal(val: Any) -> Decimal:
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
    logger.info(f"Building cashflow report for user_id={user_id} from={from_month} to={to_month}")
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
    logger.debug(f"Normalized range: {from_dt} to {to_dt}")
    
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
    cursor = db["bsa_merged_bankstatements"].find(query).sort("created_at", 1)
    docs = await cursor.to_list(length=None)
    logger.info(f"Fetched {len(docs)} documents from MongoDB for user_id={user_id}")

    if not docs:
        logger.warning(f"No documents found in DB for user_id={user_id} in range {from_dt} to {to_dt}")
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
                logger.error(f"Failed to parse month string '{m_str}' in doc_id={doc.get('_id')}")
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
        "closing": Decimal("0"),

        # ── Phase 2: Inflow % and line items ────────────────────────────
        "total_inflows_percent":  Decimal("0"),
        "cash_deposit":           Decimal("0"),
        "cheque_receipt":         Decimal("0"),
        "online_receipt":         Decimal("0"),
        "other_receipt":          Decimal("0"),
 
        # ── Phase 2: Outflow % and line items ───────────────────────────
        "total_outflows_percent": Decimal("0"),
        "cash_withdraw":          Decimal("0"),
        "cheque_payment":         Decimal("0"),
        "online_payment":         Decimal("0"),
        "other_payment":          Decimal("0"),
 
        # ── Phase 2: Indirect expense breakdown ─────────────────────────
        "salary_payment":         Decimal("0"),
        "insurance_payment":      Decimal("0"),
        "rent_payment":           Decimal("0"),
        "company_expense":        Decimal("0"),
        "bank_charge":            Decimal("0"),
        "utility_expense":        Decimal("0"),
        "tax_paid":               Decimal("0"),
        "interest_paid":          Decimal("0"),
        "refund_payment":         Decimal("0"),
        "credit_card_payment":    Decimal("0"),
        "forex_payment":          Decimal("0"),
 
        # ── Phase 2: Indirect income breakdown ──────────────────────────
        "interest_received":      Decimal("0"),
        "tax_refund":             Decimal("0"),
        "rent_receipt":           Decimal("0"),
 
        # ── Phase 2: Payables breakdown ──────────────────────────────────
        "loan_payment":               Decimal("0"),
        "work_capital_payment":       Decimal("0"),
        "investment_payment":         Decimal("0"),
        "contra_payment":             Decimal("0"),
        "fi_payment":                 Decimal("0"),
        "sweep_out":                  Decimal("0"),
        "bank_instrument_payment":    Decimal("0"),
 
        # ── Phase 2: Receivables breakdown ──────────────────────────────
        "loan_receipt":           Decimal("0"),
        "work_capital_receipt":   Decimal("0"),
        "investment_receipt":     Decimal("0"),
        "insurance_receipt":      Decimal("0"),
        "contra_receipt":         Decimal("0"),
        "fi_receipt":             Decimal("0"),
        "sweep_in":               Decimal("0"),

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

        totals["total_inflows_percent"] += _safe_decimal(row.get("TotalInflowPercentage"))


        cash_dep   = _safe_decimal(row.get("CashDeposit"))
        chq_rec    = _safe_decimal(row.get("ChequeReceipt"))
        onl_rec    = _safe_decimal(row.get("OnlineReceipt"))
        oth_rec    = _safe_decimal(row.get("OtherReceipt"))
        totals["cash_deposit"]    += cash_dep
        totals["cheque_receipt"]  += chq_rec
        totals["online_receipt"]  += onl_rec
        totals["other_receipt"]   += oth_rec
        totals["A_inflows"]       += cash_dep + chq_rec + onl_rec + oth_rec

                # ── Phase 2: Outflow % (average across months) ──────────────────
        totals["total_outflows_percent"] += _safe_decimal(row.get("TotalOutflowPercentage"))
 
        # ── Phase 1 + Phase 2: Outflow line items ───────────────────────
        cash_wd    = _safe_decimal(row.get("CashWithdraw"))
        chq_pay    = _safe_decimal(row.get("ChequePayment"))
        onl_pay    = _safe_decimal(row.get("OnlinePayment"))
        oth_pay    = _safe_decimal(row.get("OtherPayment"))
        totals["cash_withdraw"]   += cash_wd
        totals["cheque_payment"]  += chq_pay
        totals["online_payment"]  += onl_pay
        totals["other_payment"]   += oth_pay
        totals["B_outflows"]      += cash_wd + chq_pay + onl_pay + oth_pay

        sal  = _safe_decimal(row.get("SalaryPayment"))
        ins  = _safe_decimal(row.get("InsurancePayment"))
        ren  = _safe_decimal(row.get("RentPayment"))
        cmp  = _safe_decimal(row.get("CompanyExpense"))
        bnk  = _safe_decimal(row.get("BankCharge"))
        utl  = _safe_decimal(row.get("UtilityExpense"))
        tax  = _safe_decimal(row.get("TaxPaid"))
        itp  = _safe_decimal(row.get("InterestPaid"))
        ref  = _safe_decimal(row.get("RefundPayment"))
        ccp  = _safe_decimal(row.get("CreditCardPayment"))
        frx  = _safe_decimal(row.get("ForexPayment"))
        totals["salary_payment"]       += sal
        totals["insurance_payment"]    += ins
        totals["rent_payment"]         += ren
        totals["company_expense"]      += cmp
        totals["bank_charge"]          += bnk
        totals["utility_expense"]      += utl
        totals["tax_paid"]             += tax
        totals["interest_paid"]        += itp
        totals["refund_payment"]       += ref
        totals["credit_card_payment"]  += ccp
        totals["forex_payment"]        += frx
        totals["D_indirect_exp"]       += sal + ins + ren + cmp + bnk + utl + tax + itp + ref + ccp + frx


        itr  = _safe_decimal(row.get("InterestReceived"))
        txr  = _safe_decimal(row.get("TaxRefund"))
        rnr  = _safe_decimal(row.get("RentReceipt"))
        totals["interest_received"] += itr
        totals["tax_refund"]        += txr
        totals["rent_receipt"]      += rnr
        totals["E_indirect_inc"]    += itr + txr + rnr

        lnp  = _safe_decimal(row.get("LoanPayment"))
        wcp  = _safe_decimal(row.get("workCapitalPayment"))
        ivp  = _safe_decimal(row.get("InvestmentPayment"))
        cop  = _safe_decimal(row.get("ContraPayment"))
        fip  = _safe_decimal(row.get("FiPayment"))
        swo  = _safe_decimal(row.get("SweepOut"))
        bip  = _safe_decimal(row.get("BankInstrumentPayment"))
        totals["loan_payment"]            += lnp
        totals["work_capital_payment"]    += wcp
        totals["investment_payment"]      += ivp
        totals["contra_payment"]          += cop
        totals["fi_payment"]              += fip
        totals["sweep_out"]               += swo
        totals["bank_instrument_payment"] += bip
        totals["payables"]                += lnp + wcp + ivp + cop + fip + swo + bip
 


        lnr  = _safe_decimal(row.get("LoanReceipt"))
        wcr  = _safe_decimal(row.get("WorkCapitalReceipt"))
        ivr  = _safe_decimal(row.get("InvestmentReceipt"))
        insr = _safe_decimal(row.get("InsuranceReceipt"))
        cor  = _safe_decimal(row.get("ContraReceipt"))
        fir  = _safe_decimal(row.get("FiReceipt"))
        swi  = _safe_decimal(row.get("SweepIn"))
        totals["loan_receipt"]          += lnr
        totals["work_capital_receipt"]  += wcr
        totals["investment_receipt"]    += ivr
        totals["insurance_receipt"]     += insr
        totals["contra_receipt"]        += cor
        totals["fi_receipt"]            += fir
        totals["sweep_in"]              += swi
        totals["receivables"]           += lnr + wcr + ivr + insr + cor + fir + swi
 
        totals["accruals"] += _safe_decimal(row.get("BankAccural"))

        formatted_data.append(row)

    # Formula Results
    gross_profit_c = totals["A_inflows"] - totals["B_outflows"]
    net_profit_f = gross_profit_c - totals["D_indirect_exp"] + totals["E_indirect_inc"]

    total_inflows_pct  = totals["total_inflows_percent"]
    total_outflows_pct = totals["total_outflows_percent"]

    def f(d: Decimal) -> float:
        return float(d)


    logger.info(
        f"Report generated: {len(formatted_data)} months. "
        f"Gross Profit: {gross_profit_c}, Net Profit: {net_profit_f}"
    )

    # 5. Final Response
    return {
        "status": "success",
        "data":{
            "summary": {
                                # ── Phase 1: Top-level P&L ───────────────────────────────
                "total_inflows_percent": f(total_inflows_pct),
                "inflows_revenue_a":     f(totals["A_inflows"]),
                "cash_deposit":          f(totals["cash_deposit"]),
                "cheque_receipt":        f(totals["cheque_receipt"]),
                "online_receipt":        f(totals["online_receipt"]),
                "other_receipt":         f(totals["other_receipt"]),

                "total_outflows_percent": f(total_outflows_pct),
                "outflows_expenses_b":   f(totals["B_outflows"]),
                "cash_withdrawal":          f(totals["cash_withdraw"]),
                "cheque_payment":         f(totals["cheque_payment"]),
                "online_payment":         f(totals["online_payment"]),
                "other_payment":          f(totals["other_payment"]),

                "gross_inflow_profit_c": f(gross_profit_c),


                "indirect_expenses_d":   f(totals["D_indirect_exp"]),
                 "salary_payment":        f(totals["salary_payment"]),
                "insurance_payment":     f(totals["insurance_payment"]),
                "rent_payment":          f(totals["rent_payment"]),
                "company_expense":       f(totals["company_expense"]),
                "bank_charge":           f(totals["bank_charge"]),
                "utility_expense":       f(totals["utility_expense"]),
                "tax_paid":              f(totals["tax_paid"]),
                "interest_paid":         f(totals["interest_paid"]),
                "refund_payment":        f(totals["refund_payment"]),
                "credit_card_payment":   f(totals["credit_card_payment"]),
                "forex_payment":         f(totals["forex_payment"]),
 
                
                "indirect_income_e":     f(totals["E_indirect_inc"]),
                "interest_received":     f(totals["interest_received"]),
                "tax_refund":            f(totals["tax_refund"]),
                "rent_receipt":          f(totals["rent_receipt"]),

                "net_inflow_profit_f":   f(net_profit_f),


                "total_payables":        f(totals["payables"]),
                "loan_payment":               f(totals["loan_payment"]),
                "work_capital_payment":       f(totals["work_capital_payment"]),
                "investment_payment":         f(totals["investment_payment"]),
                "contra_payment":             f(totals["contra_payment"]),
                "fi_payment":                 f(totals["fi_payment"]),
                "sweep_out":                  f(totals["sweep_out"]),
                "bank_instrument_payment":    f(totals["bank_instrument_payment"]),


                "total_receivables_g":   f(totals["receivables"]),
                "loan_receipt":          f(totals["loan_receipt"]),
                "work_capital_receipt":  f(totals["work_capital_receipt"]),
                "investment_receipt":    f(totals["investment_receipt"]),
                "insurance_receipt":     f(totals["insurance_receipt"]),
                "contra_receipt":        f(totals["contra_receipt"]),
                "fi_receipt":            f(totals["fi_receipt"]),
                "sweep_in":              f(totals["sweep_in"]),

                "bank_accruals":         f(totals["accruals"]),
                "opening_balance":       f(totals["opening"]),
                "closing_balance":       f(totals["closing"]),
                "net_cashflow":          f(gross_profit_c),
            },
            "monthly_breakdown": formatted_data,
            
        }  

        }


async def r1xcrm_build_cashflow_report(db, acc_id: int, from_month: str, to_month: str):
    user_collection = db["users"]

    user = await user_collection.find_one(
        {"account_id": acc_id},
        {"_id": 1}
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user_id = str(user["_id"])  # or keep it as ObjectId depending on your DB

    print(user_id,"user_id")

    return await build_cashflow_report(db,user_id,from_month,to_month)