import pdfplumber
import io
import re

# ── helpers ──────────────────────────────────────────────────────────────────

def _clean_amount(val: str) -> str:
    """Remove commas/spaces, keep digits and dot."""
    return re.sub(r"[^\d.]", "", str(val)).strip() if val else "0.00"

def _is_header_row(row: list) -> bool:
    """True if any cell contains typical header words."""
    header_keywords = {"date", "particular", "narration", "debit", "credit",
                       "balance", "sl", "ref", "chq", "tran", "description"}
    for cell in row:
        if cell and any(k in str(cell).lower() for k in header_keywords):
            return True
    return False

def _row_has_date(cell: str) -> bool:
    """Loose check: does the cell look like a date (DD-MM-YYYY or DD/MM/YYYY)?"""
    if not cell:
        return False
    return bool(re.search(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", str(cell)))


# ── column sniffer ────────────────────────────────────────────────────────────

def _sniff_columns(header_row: list) -> dict:
    """
    Given the header row, return a dict of column indices:
    {slno, date, particular, debit, credit, balance}
    Falls back to positional defaults if nothing matches.
    """
    mapping = {}
    for i, cell in enumerate(header_row):
        c = str(cell or "").lower().strip()
        if re.search(r"sl|sno|s\.no", c):
            mapping["slno"] = i
        elif re.search(r"date", c):
            mapping["date"] = i
        elif re.search(r"particular|narration|description|detail", c):
            mapping["particular"] = i
        elif re.search(r"ref|chq|cheque", c):
            mapping["reference"] = i
        elif re.search(r"debit|dr|withdraw", c):
            mapping["debit"] = i
        elif re.search(r"credit|cr|deposit", c):
            mapping["credit"] = i
        elif re.search(r"balance|bal", c):
            mapping["balance"] = i

    # ── positional fallback for typical Indian Bank layout ──
    # Sl | Date | Particular | Ref | Debit | Credit | Balance
    defaults = {
        "slno": 0,
        "date": 1,
        "particular": 2,
        "reference": 3,
        "debit": 4,
        "credit": 5,
        "balance": 6,
    }
    for k, v in defaults.items():
        mapping.setdefault(k, v)

    return mapping


# ── main extractor ────────────────────────────────────────────────────────────

async def extract_raw_data(file_content: bytes, filename: str):
    ext = filename.rsplit(".", 1)[-1].lower()
    transactions = []

    try:
        if ext == "pdf":
            transactions = _extract_from_pdf(file_content)
        elif ext in ("xlsx", "xls"):
            transactions = _extract_from_excel(file_content)
        else:
            print(f"[Extraction] Unsupported file type: {ext}")
            return []

    except Exception as e:
        print(f"[Extraction] Fatal error on {filename}: {e}")
        return []

    return transactions


# ── PDF path ──────────────────────────────────────────────────────────────────

def _extract_from_pdf(file_content: bytes) -> list:
    transactions = []

    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
        # ── 1. Scanned-image check (generous threshold) ──
        text_found = False
        for page in pdf.pages[:5]:
            text = page.extract_text() or ""
            if len(text.strip()) > 50:
                text_found = True
                break

        if not text_found:
            print("[Extraction] PDF appears to be a scanned image — skipping")
            return []          # caller sets extraction_status = "skipped_scan"

        # ── 2. Try table extraction with multiple strategies ──
        col_map = None

        strategies = [
            # Strategy A — works well for lined Indian Bank statements
            {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
            # Strategy B — fallback for mixed PDFs
            {"vertical_strategy": "text",  "horizontal_strategy": "lines"},
            # Strategy C — last resort
            {"vertical_strategy": "lines", "horizontal_strategy": "text"},
        ]

        for strat in strategies:
            rows_collected = []
            map_found = None

            for page in pdf.pages:
                tables = page.extract_tables(strat)
                for table in tables:
                    for row in table:
                        if not any(row):          # skip completely empty rows
                            continue

                        # Auto-detect header row and build column map once
                        if map_found is None and _is_header_row(row):
                            map_found = _sniff_columns(row)
                            continue              # don't treat header as data

                        rows_collected.append(row)

            if rows_collected:
                col_map = map_found or _sniff_columns([])   # use defaults if no header
                transactions = _parse_rows(rows_collected, col_map)
                if transactions:
                    print(f"[Extraction] Strategy {strat} succeeded — "
                          f"{len(transactions)} rows")
                    break

        # ── 3. Last resort: line-by-line text parse ──
        if not transactions:
            print("[Extraction] Table strategies failed — falling back to text parse")
            transactions = _text_fallback(pdf)

    return transactions


def _parse_rows(rows: list, col_map: dict) -> list:
    """Convert raw pdfplumber rows → clean transaction dicts."""
    out = []
    slno_counter = 1

    for row in rows:
        # Pad row if shorter than expected
        while len(row) <= max(col_map.values()):
            row.append("")

        date_val = str(row[col_map["date"]] or "").strip()
        if not _row_has_date(date_val):
            continue   # skip non-transaction rows (subtotals, blank lines, etc.)

        # Normalize amounts
        debit  = _clean_amount(row[col_map.get("debit",  4)])
        credit = _clean_amount(row[col_map.get("credit", 5)])
        balance= _clean_amount(row[col_map.get("balance",6)])

        out.append({
            "Slno":       row[col_map.get("slno", 0)] or str(slno_counter),
            "Date":       date_val,
            "Particular": str(row[col_map.get("particular", 2)] or "").strip(),
            "Reference":  str(row[col_map.get("reference",  3)] or "").strip(),
            "Debit":      debit  or "0.00",
            "Credit":     credit or "0.00",
            "Balance":    balance,
        })
        slno_counter += 1

    return out


# ── text fallback (regex) ─────────────────────────────────────────────────────

def _text_fallback(pdf) -> list:
    """
    Parse raw text lines when table extraction returns nothing.
    Looks for lines that start with a date pattern.
    """
    out = []
    slno = 1
    # Pattern: DD-MM-YYYY  ...text...  amount  amount  amount
    pattern = re.compile(
        r"(\d{2}[-/]\d{2}[-/]\d{4})"   # date
        r"\s+(.*?)"                      # narration (non-greedy)
        r"\s+([\d,]+\.\d{2})"           # col 1 — debit or credit
        r"\s+([\d,]+\.\d{2})?"          # col 2 — credit or balance (optional)
        r"\s+([\d,]+\.\d{2})?"          # col 3 — balance (optional)
    )

    for page in pdf.pages:
        text = page.extract_text() or ""
        for line in text.splitlines():
            m = pattern.search(line)
            if not m:
                continue
            g = m.groups()
            out.append({
                "Slno":       str(slno),
                "Date":       g[0],
                "Particular": (g[1] or "").strip(),
                "Reference":  "",
                "Debit":      _clean_amount(g[2]) if g[2] else "0.00",
                "Credit":     _clean_amount(g[3]) if g[3] else "0.00",
                "Balance":    _clean_amount(g[4]) if g[4] else "0.00",
            })
            slno += 1

    return out


# ── Excel path ────────────────────────────────────────────────────────────────

def _extract_from_excel(file_content: bytes) -> list:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    # Find header row
    col_map = None
    data_start = 0
    for i, row in enumerate(rows):
        row_list = [str(c or "") for c in row]
        if _is_header_row(row_list):
            col_map = _sniff_columns(row_list)
            data_start = i + 1
            break

    if col_map is None:
        col_map = _sniff_columns([])   # positional defaults

    out = []
    slno_counter = 1
    for row in rows[data_start:]:
        row_list = [str(c or "").strip() for c in row]
        while len(row_list) <= max(col_map.values()):
            row_list.append("")

        date_val = row_list[col_map["date"]]
        if not _row_has_date(date_val):
            continue

        out.append({
            "Slno":       row_list[col_map.get("slno", 0)] or str(slno_counter),
            "Date":       date_val,
            "Particular": row_list[col_map.get("particular", 2)],
            "Reference":  row_list[col_map.get("reference",  3)],
            "Debit":      _clean_amount(row_list[col_map.get("debit",  4)]),
            "Credit":     _clean_amount(row_list[col_map.get("credit", 5)]),
            "Balance":    _clean_amount(row_list[col_map.get("balance", 6)]),
        })
        slno_counter += 1

    return out