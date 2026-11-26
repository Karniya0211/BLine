"""
Dispatch & Stock Movement Validation for FactoryFlow Phase 2.
Enforces:
- Atomic validation against available finished goods inventory.
- Verification against invoiced quantity.
- Generates compliant stock ledger movements.
"""

from typing import Dict, Any, Tuple, List


def validate_dispatch_quantity(
    product_id: str,
    requested_dispatch_qty: int,
    invoiced_qty: int,
    dispatched_so_far: int,
    available_stock: int,
) -> Tuple[bool, str, int]:
    """
    Validates dispatch quantity against invoiced balance and warehouse stock.
    Returns: (is_valid, error_or_warning_message, remaining_dispatchable)
    """
    if requested_dispatch_qty <= 0:
        return False, "Dispatch quantity must be greater than zero.", 0

    pending_to_dispatch = invoiced_qty - dispatched_so_far
    if pending_to_dispatch <= 0:
        return False, "This line item has already been completely dispatched.", 0

    if requested_dispatch_qty > pending_to_dispatch:
        return (
            False,
            f"Requested dispatch ({requested_dispatch_qty}) exceeds pending invoiced balance ({pending_to_dispatch}).",
            pending_to_dispatch,
        )

    if requested_dispatch_qty > available_stock:
        shortage = requested_dispatch_qty - available_stock
        return (
            False,
            f"Insufficient finished goods stock! Available: {available_stock} packets, Requested: {requested_dispatch_qty} packets. Shortage: {shortage} packets.",
            available_stock,
        )

    return True, "", pending_to_dispatch - requested_dispatch_qty
