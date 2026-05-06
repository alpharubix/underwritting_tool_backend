from datetime import datetime


def get_pdf_analysis_prompt(current_from: datetime, current_to: datetime):
    first_upload = current_from is None and current_to is None
    upload_context = (
        "This is the first upload — no prior data exists."
        if first_upload else
        f"Existing data covers {current_from.strftime('%Y-%m')} to {current_to.strftime('%Y-%m')}. "
        f"The uploaded statements must start from {_next_month(current_to).strftime('%Y-%m')}. "
        f"If the upload starts after {_next_month(current_to).strftime('%Y-%m')}, set has_gap to true. "
        f"If the upload starts before {_next_month(current_to).strftime('%Y-%m')}, set has_overlap to true."
    )

    return f"""You are an intelligent bank statement analysis agent.

Bank statements come in many formats — tabular, scanned, multi-column, or complex layouts.
Parse the document regardless of its format.

{upload_context}

Your tasks:
1. Extract every transaction date across all pages. Ignore header/footer dates, statement generation
   dates, and balance-only rows — only count rows that represent actual transactions.
2. Normalise all dates to YYYY-MM. If date format is ambiguous (DD/MM vs MM/DD), infer from context.
3. Identify all unique months (YYYY-MM) containing at least one transaction.
4. Determine the full expected range from the earliest to the latest transaction month (inclusive).
5. Find any months within that range that have zero transactions (gaps).
6. is_consecutive is true only if missing_months is empty.
7. Compare statement_period.start against the expected start month and set has_gap / has_overlap accordingly.

Return ONLY a raw JSON object — no markdown, no explanation, no code fences.

{{
  "is_consecutive": true,
  "has_gap": false,
  "has_overlap": false,
  "expected_start_month": "{_next_month(current_to).strftime('%Y-%m') if not first_upload else 'null'}",
  "statement_period": {{
    "start": "YYYY-MM",
    "end": "YYYY-MM"
  }},
  "transaction_months": ["YYYY-MM"],
  "missing_months": [],
  "total_missing": 0
}}

Field rules:
- is_consecutive       : true if missing_months is empty, false otherwise
- has_gap              : true if statement_period.start is after expected_start_month
- has_overlap          : true if statement_period.start is before expected_start_month
- expected_start_month : the month this upload should start from (null if first upload)
- statement_period     : earliest and latest transaction months
- transaction_months   : sorted list of all months with at least one transaction
- missing_months       : sorted list of months inside the range with no transactions ([] if none)
- total_missing        : integer count of missing_months
"""

def _next_month(dt: datetime) -> datetime:
    from dateutil.relativedelta import relativedelta
    return dt + relativedelta(months=1)