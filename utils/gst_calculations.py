"""
GST Calculations Utility for FactoryFlow Phase 2.
Strict implementation rules:
- Uses Python `decimal.Decimal` with integer-paisa rounding (`ROUND_HALF_UP`).
- No floating-point arithmetic for financial calculations.
- Determines intra-state vs inter-state tax applicability:
    * Factory State: Tamil Nadu
    * Intra-state (Customer in Tamil Nadu): CGST 2.5%, SGST 2.5%
    * Inter-state (Customer outside Tamil Nadu, e.g. Karnataka): IGST 5.0%
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List

FACTORY_STATE = "Tamil Nadu"
FACTORY_NAME = "BLine Snacks Manufacturing Unit 1"
FACTORY_ADDRESS = "Plot 14-B, SIDCO Industrial Estate, Guindy, Chennai, Tamil Nadu - 600032"
FACTORY_GSTIN = "33AAAAF0000A1Z5"


def to_decimal(val: Any) -> Decimal:
    """Converts int, float, str, or Decimal to exact Decimal with 2 decimal places."""
    if val is None or val == "":
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_line_item_gst(
    quantity: int,
    unit_price: Any,
    gst_rate_percent: Any,
    customer_state: str,
    discount_percent: Any = 0,
) -> Dict[str, Any]:
    """
    Computes exact taxable value and CGST/SGST or IGST for an individual line item.
    """
    qty = Decimal(str(quantity))
    price = to_decimal(unit_price)
    rate_pct = to_decimal(gst_rate_percent)
    discount_pct = to_decimal(discount_percent)
    if discount_pct < 0 or discount_pct > 100:
        raise ValueError("Discount percentage must be between 0 and 100.")

    gross_value = (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    discount_amount = (gross_value * discount_pct / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    taxable_value = gross_value - discount_amount

    is_intra_state = customer_state.strip().lower() == FACTORY_STATE.strip().lower()

    if is_intra_state:
        # Intra-state: Split equally between CGST and SGST
        half_rate = (rate_pct / Decimal("2")).quantize(Decimal("0.001"))
        cgst_rate = half_rate
        sgst_rate = half_rate
        igst_rate = Decimal("0.00")

        cgst_amount = (taxable_value * cgst_rate / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        sgst_amount = (taxable_value * sgst_rate / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        igst_amount = Decimal("0.00")
    else:
        # Inter-state: Full tax under IGST
        cgst_rate = Decimal("0.00")
        sgst_rate = Decimal("0.00")
        igst_rate = rate_pct

        cgst_amount = Decimal("0.00")
        sgst_amount = Decimal("0.00")
        igst_amount = (taxable_value * igst_rate / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    total_line_amount = (taxable_value + cgst_amount + sgst_amount + igst_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return {
        "quantity": int(quantity),
        "unit_price": float(price),
        "discount_percent": float(discount_pct),
        "discount_amount": float(discount_amount),
        "taxable_value": float(taxable_value),
        "gst_rate": float(rate_pct),
        "is_intra_state": is_intra_state,
        "cgst_rate": float(cgst_rate),
        "cgst_amount": float(cgst_amount),
        "sgst_rate": float(sgst_rate),
        "sgst_amount": float(sgst_amount),
        "igst_rate": float(igst_rate),
        "igst_amount": float(igst_amount),
        "total_amount": float(total_line_amount),
    }


def calculate_invoice_totals(items: List[Dict[str, Any]], customer_state: str) -> Dict[str, Any]:
    """
    Computes aggregate invoice totals from line items using exact Decimal arithmetic.
    """
    tot_taxable = Decimal("0.00")
    tot_cgst = Decimal("0.00")
    tot_sgst = Decimal("0.00")
    tot_igst = Decimal("0.00")
    tot_amount = Decimal("0.00")

    processed_items = []
    for it in items:
        calc = calculate_line_item_gst(
            quantity=it.get("quantity", 0),
            unit_price=it.get("unit_price", 0.0),
            gst_rate_percent=it.get("gst_rate", 5.0),
            customer_state=customer_state,
            discount_percent=it.get("discount_percent", 0),
        )
        # Preserve item descriptors
        calc["product_id"] = it.get("product_id", "")
        calc["name"] = it.get("name", "")
        calc["hsn_code"] = it.get("hsn_code", "19059040")
        calc["pack_size"] = it.get("pack_size", "200g")
        processed_items.append(calc)

        tot_taxable += to_decimal(calc["taxable_value"])
        tot_cgst += to_decimal(calc["cgst_amount"])
        tot_sgst += to_decimal(calc["sgst_amount"])
        tot_igst += to_decimal(calc["igst_amount"])
        tot_amount += to_decimal(calc["total_amount"])

    return {
        "items": processed_items,
        "customer_state": customer_state,
        "is_intra_state": customer_state.strip().lower() == FACTORY_STATE.strip().lower(),
        "total_taxable_value": float(tot_taxable),
        "total_cgst": float(tot_cgst),
        "total_sgst": float(tot_sgst),
        "total_igst": float(tot_igst),
        "total_gst": float(tot_cgst + tot_sgst + tot_igst),
        "total_amount": float(tot_amount),
    }
