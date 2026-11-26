"""
Order Value & Calculation Utilities for FactoryFlow Phase 2.
Integrates strict Decimal precision for subtotal, discount, GST, and final order value.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any
from utils.gst_calculations import calculate_invoice_totals, to_decimal


def compute_order_summary(items: List[Dict[str, Any]], customer_state: str) -> Dict[str, Any]:
    """
    Computes subtotal, GST breakup, and grand total for an order before submission.
    """
    if not items:
        return {
            "total_items": 0,
            "total_quantity": 0,
            "subtotal": 0.0,
            "cgst": 0.0,
            "sgst": 0.0,
            "igst": 0.0,
            "total_gst": 0.0,
            "total_amount": 0.0,
            "items": [],
        }

    totals = calculate_invoice_totals(items, customer_state)
    total_qty = sum(it.get("quantity", 0) for it in items)

    return {
        "total_items": len(items),
        "total_quantity": total_qty,
        "subtotal": totals["total_taxable_value"],
        "cgst": totals["total_cgst"],
        "sgst": totals["total_sgst"],
        "igst": totals["total_igst"],
        "total_gst": totals["total_gst"],
        "total_amount": totals["total_amount"],
        "is_intra_state": totals["is_intra_state"],
        "items": totals["items"],
    }
