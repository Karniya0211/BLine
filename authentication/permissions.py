"""
Role-Based Access Control (RBAC) and Navigation for FactoryFlow (Phase 1, Phase 2 & Phase 3).
Enterprise specification: No emojis, plain formal naming, strict privilege routing.
Phase 3 Pages:
1. Production Orders
2. Bill of Materials
3. Inventory Management
"""

from typing import List, Dict

ROLE_OWNER = "Owner"
ROLE_ADMIN = "Admin"
ROLE_SALESMAN = "Sales Representative"
ROLE_SUPERVISOR = "Production Supervisor"
ROLE_AUDITOR = "Statutory Auditor"

ALL_ROLES = [ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN, ROLE_SUPERVISOR, ROLE_AUDITOR]

# Formal page names without emojis
PAGE_DASHBOARD = "Operations Dashboard"
PAGE_SALES_DASHBOARD = "Sales Dashboard"
PAGE_NEW_ORDER = "New Order"
PAGE_MY_ORDERS = "My Orders"
PAGE_ORDER_MANAGEMENT = "Order Management"
PAGE_GST_BILLING = "GST Billing"
PAGE_INVOICE_HISTORY = "Invoice History"
PAGE_DISPATCH = "Dispatch Management"
PAGE_PAYMENTS = "Payments"

# Phase 3 Pages
PAGE_PRODUCTION = "Production Orders"
PAGE_BOM = "Bill of Materials"
PAGE_INVENTORY = "Inventory Management"

PAGE_PRODUCTS = "Product Master"
PAGE_CUSTOMERS = "Customer Master"
PAGE_SUPPLIERS = "Supplier Master"
PAGE_RAW_MATERIALS = "Raw Material Master"
PAGE_USERS = "User Management"
PAGE_SETTINGS = "System Settings"
PAGE_TERMS = "Terms & Privacy"
PAGE_REPORTS = "Reports Portal"
PAGE_FINANCIALS = "Financial Management"

ROLE_NAVIGATION: Dict[str, List[str]] = {
    ROLE_OWNER: [
        PAGE_DASHBOARD,
        PAGE_SALES_DASHBOARD,
        PAGE_PRODUCTION,
        PAGE_BOM,
        PAGE_NEW_ORDER,
        PAGE_ORDER_MANAGEMENT,
        PAGE_GST_BILLING,
        PAGE_INVOICE_HISTORY,
        PAGE_PAYMENTS,
        PAGE_PRODUCTS,
        PAGE_CUSTOMERS,
        PAGE_SUPPLIERS,
        PAGE_RAW_MATERIALS,
        PAGE_REPORTS,
        PAGE_TERMS,
    ],
    ROLE_ADMIN: [
        PAGE_DASHBOARD,
        PAGE_SALES_DASHBOARD,
        PAGE_PRODUCTION,
        PAGE_NEW_ORDER,
        PAGE_ORDER_MANAGEMENT,
        PAGE_GST_BILLING,
        PAGE_INVOICE_HISTORY,
        PAGE_DISPATCH,
        PAGE_PAYMENTS,
        PAGE_PRODUCTS,
        PAGE_CUSTOMERS,
        PAGE_SUPPLIERS,
        PAGE_RAW_MATERIALS,
        PAGE_USERS,
        PAGE_SETTINGS,
        PAGE_REPORTS,
        PAGE_TERMS,
    ],
    ROLE_SALESMAN: [
        PAGE_SALES_DASHBOARD,
        PAGE_NEW_ORDER,
        PAGE_MY_ORDERS,
        PAGE_PRODUCTS,
        PAGE_REPORTS,
        PAGE_TERMS,
    ],
    ROLE_SUPERVISOR: [
        PAGE_DASHBOARD,
        PAGE_PRODUCTION,
        PAGE_BOM,
        PAGE_INVENTORY,
        PAGE_DISPATCH,
        PAGE_PRODUCTS,
        PAGE_RAW_MATERIALS,
        PAGE_REPORTS,
        PAGE_TERMS,
    ],
    ROLE_AUDITOR: [
        PAGE_DASHBOARD,
        PAGE_SALES_DASHBOARD,
        PAGE_PRODUCTION,
        PAGE_INVOICE_HISTORY,
        PAGE_GST_BILLING,
        PAGE_PAYMENTS,
        PAGE_REPORTS,
        PAGE_TERMS,
    ],
}

ROLE_CAPABILITIES: Dict[str, Dict[str, bool]] = {
    ROLE_OWNER: {
        "can_edit_master_data": True,
        "can_manage_users": True,
        "can_view_financials": False,
        "can_view_audit_logs": True,
        "can_approve_orders": True,
        "can_generate_invoices": True,
        "can_dispatch": True,
        "can_record_payments": True,
        "can_manage_production": True,
        "is_read_only": False,
    },
    ROLE_ADMIN: {
        "can_edit_master_data": True,
        "can_manage_users": True,
        "can_view_financials": False,
        "can_view_audit_logs": False,
        "can_approve_orders": True,
        "can_generate_invoices": True,
        "can_dispatch": True,
        "can_record_payments": True,
        "can_manage_production": True,
        "is_read_only": False,
    },
    ROLE_SALESMAN: {
        "can_edit_master_data": False,
        "can_manage_users": False,
        "can_view_financials": False,
        "can_view_audit_logs": False,
        "can_approve_orders": False,
        "can_generate_invoices": False,
        "can_dispatch": False,
        "can_record_payments": False,
        "can_manage_production": False,
        "is_read_only": False,
    },
    ROLE_SUPERVISOR: {
        "can_edit_master_data": True,
        "can_manage_users": False,
        "can_view_financials": False,
        "can_view_audit_logs": False,
        "can_approve_orders": False,
        "can_generate_invoices": False,
        "can_dispatch": True,
        "can_record_payments": False,
        "can_manage_production": True,
        "is_read_only": False,
    },
    ROLE_AUDITOR: {
        "can_edit_master_data": False,
        "can_manage_users": False,
        "can_view_financials": False,
        "can_view_audit_logs": True,
        "can_approve_orders": False,
        "can_generate_invoices": False,
        "can_dispatch": False,
        "can_record_payments": False,
        "can_manage_production": False,
        "is_read_only": True,
    },
}


def get_allowed_pages(role: str) -> List[str]:
    return ROLE_NAVIGATION.get(role, [PAGE_SALES_DASHBOARD])


def check_page_permission(role: str, page_name: str) -> bool:
    return page_name in get_allowed_pages(role)


def can_edit(role: str) -> bool:
    cap = ROLE_CAPABILITIES.get(role, {})
    return not cap.get("is_read_only", False) and cap.get("can_edit_master_data", False)
