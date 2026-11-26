"""
Validation utilities for FactoryFlow Phase 1.
Handles email, phone, GSTIN, HSN, and general field integrity.
"""

import re
from typing import Tuple


def validate_email(email: str) -> bool:
    """Checks if the email string has a valid RFC standard pattern."""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def validate_phone(phone: str) -> bool:
    """Checks Indian standard 10-digit phone number format (with optional +91 or 0 prefix)."""
    if not phone:
        return False
    clean = re.sub(r"[\s\-\(\)]", "", phone)
    pattern = r"^(\+91|0)?[6-9]\d{9}$"
    return bool(re.match(pattern, clean))


def validate_gstin(gstin: str) -> bool:
    """Validates 15-digit Indian GSTIN format (e.g. 33AAAAA0000A1Z5)."""
    if not gstin:
        return True  # Optional in some flows
    clean = gstin.strip().upper()
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(pattern, clean))


def validate_hsn(hsn: str) -> bool:
    """Validates 4 to 8 digit HSN/SAC code."""
    if not hsn:
        return False
    pattern = r"^\d{4,8}$"
    return bool(re.match(pattern, hsn.strip()))


def validate_product_data(data: dict) -> Tuple[bool, str]:
    """Validates required product fields before saving."""
    if not data.get("product_id", "").strip():
        return False, "Product ID is required."
    if not data.get("name", "").strip():
        return False, "Product Name is required."
    if not data.get("category", "").strip():
        return False, "Category is required."
    if data.get("selling_price", 0) <= 0:
        return False, "Selling Price must be greater than 0."
    if data.get("gst_rate", -1) < 0:
        return False, "GST Rate cannot be negative."
    return True, ""


def validate_customer_data(data: dict) -> Tuple[bool, str]:
    """Validates required customer fields."""
    if not data.get("customer_id", "").strip():
        return False, "Customer ID is required."
    if not data.get("name", "").strip():
        return False, "Customer Name is required."
    if not data.get("phone", "").strip() or not validate_phone(data.get("phone", "")):
        return False, "Valid 10-digit phone number is required."
    if data.get("email") and not validate_email(data.get("email")):
        return False, "Provided email is invalid."
    if data.get("gstin") and not validate_gstin(data.get("gstin")):
        return False, "Provided GSTIN is invalid (must be 15 alphanumeric characters)."
    return True, ""


def validate_supplier_data(data: dict) -> Tuple[bool, str]:
    """Validates required supplier fields."""
    if not data.get("supplier_id", "").strip():
        return False, "Supplier ID is required."
    if not data.get("name", "").strip():
        return False, "Supplier Name is required."
    if not data.get("phone", "").strip() or not validate_phone(data.get("phone", "")):
        return False, "Valid 10-digit phone number is required."
    if data.get("email") and not validate_email(data.get("email")):
        return False, "Provided email is invalid."
    return True, ""


def validate_raw_material_data(data: dict) -> Tuple[bool, str]:
    """Validates required raw material master fields."""
    if not data.get("material_id", "").strip():
        return False, "Material ID is required."
    if not data.get("name", "").strip():
        return False, "Material Name is required."
    if data.get("purchase_rate", 0) <= 0:
        return False, "Purchase rate must be greater than 0."
    if data.get("min_stock_level", -1) < 0:
        return False, "Minimum stock level cannot be negative."
    return True, ""
