from decimal import Decimal


def _scale_to_lakhs(val: Decimal, precision: int = 4) -> float:
    """
    Converts values stored in '000s (thousands) to Lacs (Lakhs).
    Logic: (val * 1000) / 100,000 => val / 100.
    Using 4 decimal places as 1 Lac = 1,00,000, so 0.0001 Lac = 10 INR.
    """
    if not val:
        return 0.0
    return float(round(val / Decimal("100"), precision))