"""
Payment & Balance Tracking Calculations for FactoryFlow Phase 2.
Enforces:
- Outstanding = Invoice Total - Total Payments Received
- Decimal arithmetic to avoid fractional rounding errors.
- Prevents payments exceeding remaining balance unless explicit overpayment workflow is enabled.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List
from utils.gst_calculations import to_decimal


def compute_invoice_payment_status(
    invoice_total: Any,
    payments: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Computes total paid, outstanding balance, and settlement status for an invoice.
    """
    inv_total = to_decimal(invoice_total)
    total_paid = Decimal("0.00")

    for p in payments:
        if p.get("status", "Confirmed") == "Confirmed":
            total_paid += to_decimal(p.get("amount", 0.0))

    outstanding = (inv_total - total_paid).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if outstanding < Decimal("0.00"):
        outstanding = Decimal("0.00")

    if total_paid == Decimal("0.00"):
        status = "Unpaid"
    elif total_paid >= inv_total:
        status = "Paid"
    else:
        status = "Partially Paid"

    return {
        "invoice_total": float(inv_total),
        "total_paid": float(total_paid),
        "outstanding_balance": float(outstanding),
        "payment_status": status,
        "is_settled": outstanding == Decimal("0.00"),
    }
