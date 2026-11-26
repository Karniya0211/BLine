"""
FactoryFlow - South Indian Snacks Manufacturing Management System (Phase 1 & Phase 2)
Flask Application Controller.
- Pure Python & Flask backend
- Preserves 100% of the UI design, color palette, typography, and functionality
- Preserves Firebase Firestore integration, decimal GST calculations, ReportLab PDF generation
- Runs on http://127.0.0.1:5000 via 'python app.py'
"""

import os
import io
import uuid
import secrets
from datetime import datetime
from decimal import Decimal, InvalidOperation
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file,
    Response,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from database.firebase_config import (
    initialize_firebase,
    get_firebase_credentials,
    get_firebase_web_api_key,
)
from database.firestore_operations import (
    get_products,
    add_product,
    update_product,
    toggle_status,
    get_customers,
    add_customer,
    update_customer,
    get_suppliers,
    add_supplier,
    update_supplier,
    get_raw_materials,
    add_raw_material,
    update_raw_material,
    get_orders,
    get_orders_by_salesman,
    create_order,
    update_order_status,
    get_invoices,
    create_invoice,
    update_invoice,
    get_dispatches,
    create_dispatch,
    get_payments,
    get_payments_for_invoice,
    record_payment,
    get_stock_ledger,
    get_product_available_stock,
    reserve_product_stock,
    release_reserved_stock,
    record_stock_dispatch,
    get_all_documents,
    get_raw_material_available_stock,
    add_raw_material_stock,
    get_production_orders,
    create_production_order,
    update_production_order,
    delete_production_order,
    get_boms,
    get_bom_for_product,
    save_bom,
    calculate_bom_requirements,
    get_inventory_transactions,
    complete_production,
    delete_document,
    record_activity_log,
    get_activity_logs,
    ensure_database_seed,
    get_production_expenses,
    record_production_expense,
    get_purchase_invoices,
    create_purchase_invoice,
    get_users,
    add_user,
    update_user,
)
from authentication.permissions import (
    ALL_ROLES,
    ROLE_OWNER,
    ROLE_ADMIN,
    ROLE_SALESMAN,
    ROLE_SUPERVISOR,
    ROLE_AUDITOR,
    PAGE_DASHBOARD,
    PAGE_SALES_DASHBOARD,
    PAGE_NEW_ORDER,
    PAGE_MY_ORDERS,
    PAGE_ORDER_MANAGEMENT,
    PAGE_GST_BILLING,
    PAGE_INVOICE_HISTORY,
    PAGE_DISPATCH,
    PAGE_PAYMENTS,
    PAGE_PRODUCTS,
    PAGE_CUSTOMERS,
    PAGE_SUPPLIERS,
    PAGE_RAW_MATERIALS,
    PAGE_PRODUCTION,
    PAGE_BOM,
    PAGE_INVENTORY,
    PAGE_USERS,
    PAGE_SETTINGS,
    PAGE_TERMS,
    PAGE_REPORTS,
    PAGE_FINANCIALS,
    get_allowed_pages,
    check_page_permission,
    can_edit,
)
from authentication.login import (
    authenticate_with_firebase,
    reset_password_firebase,
    send_password_reset_code,
    set_password,
    create_employee_auth,
    get_user_profile_from_firestore,
    DEMO_USERS,
)
from utils.gst_calculations import (
    calculate_invoice_totals,
    FACTORY_STATE,
    FACTORY_NAME,
    FACTORY_ADDRESS,
    FACTORY_GSTIN,
)
from utils.order_calculations import compute_order_summary
from utils.payment_calculations import compute_invoice_payment_status
from utils.dispatch_manager import validate_dispatch_quantity
from utils.invoice_generator import generate_invoice_pdf
from utils.validators import (
    validate_email,
    validate_product_data,
    validate_customer_data,
    validate_supplier_data,
    validate_raw_material_data,
)
from utils.helpers import format_currency
from utils.financial_reports import (
    REPORTS,
    build_financial_reports,
    render_csv,
    render_pdf,
    render_xlsx,
)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "factoryflow-industrial-secret-key-2026")
app.config["TEMPLATES_AUTO_RELOAD"] = True

DATABASE_STATUS = ensure_database_seed()

# Mapping of formal page titles to Flask endpoints
PAGE_ENDPOINT_MAP = {
    PAGE_DASHBOARD: "dashboard",
    PAGE_SALES_DASHBOARD: "sales_dashboard",
    PAGE_NEW_ORDER: "new_order",
    PAGE_MY_ORDERS: "my_orders",
    PAGE_ORDER_MANAGEMENT: "order_management",
    PAGE_GST_BILLING: "gst_billing",
    PAGE_INVOICE_HISTORY: "invoice_history",
    PAGE_DISPATCH: "dispatch",
    PAGE_PAYMENTS: "payments",
    PAGE_PRODUCTS: "products",
    PAGE_CUSTOMERS: "customers",
    PAGE_SUPPLIERS: "suppliers",
    PAGE_RAW_MATERIALS: "raw_materials",
    PAGE_PRODUCTION: "production",
    PAGE_BOM: "bom",
    PAGE_INVENTORY: "inventory",
    PAGE_USERS: "users",
    PAGE_SETTINGS: "settings",
    PAGE_TERMS: "terms",
    PAGE_REPORTS: "reports",
    PAGE_FINANCIALS: "financials",
}

PRODUCT_CATEGORIES = ["Murukku", "Mixture", "Chips", "Sweets", "Savouries", "Other"]
INDIAN_STATES = [
    "Tamil Nadu",
    "Karnataka",
    "Kerala",
    "Andhra Pradesh",
    "Telangana",
    "Maharashtra",
    "Puducherry",
    "Other",
]
MATERIAL_CATEGORIES = [
    "Grains & Flours",
    "Oils & Fats",
    "Spices & Seasoning",
    "Packaging",
    "Sweeteners & Dairy",
    "Other",
]
MATERIAL_UNITS = ["Kilogram", "Gram", "Litre", "Piece", "Packet", "Carton"]


def get_nav_items_for_role(role: str):
    """Returns list of (title, endpoint) tuples allowed for this user's role."""
    allowed_titles = get_allowed_pages(role)
    return [(t, PAGE_ENDPOINT_MAP[t]) for t in allowed_titles if t in PAGE_ENDPOINT_MAP]


# Global template context helper
@app.context_processor
def inject_nav():
    if "user_role" in session:
        return {
            "nav_items": get_nav_items_for_role(session["user_role"]),
        }
    return {"nav_items": []}


_PUBLIC_ENDPOINTS = {
    "login",
    "login_post",
    "reset_password_post",
    "verify_reset_code",
    "logout",
    "static",
}

_ENDPOINT_ROLES = {
    "dashboard": {ROLE_OWNER, ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_AUDITOR},
    "sales_dashboard": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN, ROLE_AUDITOR},
    "new_order": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN},
    "add_to_cart": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN},
    "remove_from_cart": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN},
    "submit_order": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN},
    "add_order_customer_post": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN},
    "my_orders": {ROLE_ADMIN, ROLE_SALESMAN, ROLE_AUDITOR},
    "order_management": {ROLE_OWNER, ROLE_ADMIN, ROLE_AUDITOR},
    "approve_order_post": {ROLE_OWNER, ROLE_ADMIN},
    "reject_order_post": {ROLE_OWNER, ROLE_ADMIN},
    "revoke_approval_post": {ROLE_OWNER, ROLE_ADMIN},
    "gst_billing": {ROLE_OWNER, ROLE_ADMIN, ROLE_AUDITOR},
    "generate_invoice_post": {ROLE_OWNER, ROLE_ADMIN, ROLE_AUDITOR},
    "invoice_history": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN, ROLE_AUDITOR},
    "download_invoice_pdf": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN, ROLE_AUDITOR},
    "dispatch": {ROLE_ADMIN, ROLE_SUPERVISOR},
    "confirm_dispatch_post": {ROLE_OWNER, ROLE_ADMIN},
    "payments": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN, ROLE_AUDITOR},
    "record_payment_post": {ROLE_OWNER, ROLE_ADMIN},
    "products": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN, ROLE_SUPERVISOR, ROLE_AUDITOR},
    "add_product_post": {ROLE_OWNER, ROLE_ADMIN},
    "toggle_product_status": {ROLE_OWNER, ROLE_ADMIN},
    "customers": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN, ROLE_AUDITOR},
    "add_customer_post": {ROLE_OWNER, ROLE_ADMIN},
    "suppliers": {ROLE_OWNER, ROLE_ADMIN, ROLE_AUDITOR},
    "add_supplier_post": {ROLE_OWNER, ROLE_ADMIN},
    "raw_materials": {ROLE_OWNER, ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_AUDITOR},
    "add_raw_material_post": {ROLE_OWNER, ROLE_ADMIN, ROLE_SUPERVISOR},
    "edit_raw_material_post": {ROLE_OWNER, ROLE_ADMIN, ROLE_SUPERVISOR},
    "raw_material_inward_post": {ROLE_OWNER, ROLE_ADMIN, ROLE_SUPERVISOR},
    "production": {ROLE_OWNER, ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_AUDITOR},
    "create_production_post": {ROLE_OWNER, ROLE_ADMIN, ROLE_SUPERVISOR},
    "production_status_post": {ROLE_OWNER, ROLE_ADMIN, ROLE_SUPERVISOR},
    "delete_production_post": {ROLE_OWNER, ROLE_ADMIN, ROLE_SUPERVISOR},
    "edit_production_post": {ROLE_OWNER, ROLE_ADMIN, ROLE_SUPERVISOR},
    "bom": {ROLE_OWNER, ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_AUDITOR},
    "save_bom_post": {ROLE_OWNER, ROLE_ADMIN, ROLE_SUPERVISOR},
    "inventory": {ROLE_SUPERVISOR},
    "users": {ROLE_ADMIN},
    "create_user_post": {ROLE_OWNER, ROLE_ADMIN},
    "create_account_post": {ROLE_OWNER, ROLE_ADMIN},
    "update_user_role_post": {ROLE_OWNER, ROLE_ADMIN},
    "settings": {ROLE_ADMIN},
    "reports": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN, ROLE_SUPERVISOR, ROLE_AUDITOR},
    "financials": set(),
    "financial_export": set(),
    "financial_expense_post": set(),
    "financial_purchase_post": set(),
    "terms": {ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN, ROLE_SUPERVISOR, ROLE_AUDITOR},
}


@app.before_request
def enforce_rbac():
    endpoint = request.endpoint
    if endpoint in _PUBLIC_ENDPOINTS:
        return None
    if endpoint == "index":
        return None
    if not session.get("authenticated"):
        if request.path.startswith("/static/"):
            return None
        return redirect(url_for("login"))
    allowed_roles = _ENDPOINT_ROLES.get(endpoint)
    if allowed_roles is not None and session.get("user_role") not in allowed_roles:
        flash("Unauthorized: your role cannot access this operation.", "error")
        return redirect(url_for("index"))
    return None


# ----------------------------------------------------
# AUTHENTICATION ROUTES
# ----------------------------------------------------
@app.route("/")
def index():
    if "authenticated" in session and session["authenticated"]:
        role = session.get("user_role", ROLE_SALESMAN)
        if role == ROLE_SALESMAN:
            return redirect(url_for("sales_dashboard"))
        if role == ROLE_SUPERVISOR:
            return redirect(url_for("production"))
        allowed = get_allowed_pages(role)
        target_page = allowed[0] if allowed else PAGE_SALES_DASHBOARD
        return redirect(url_for(PAGE_ENDPOINT_MAP.get(target_page, "sales_dashboard")))
    return redirect(url_for("login"))


@app.route("/login")
def login():
    active_tab = request.args.get("tab", "auth")
    # Signed-in Owners/Admins use the same first-page account tab to provision
    # accounts; all other signed-in visits continue to their assigned portal.
    if session.get("authenticated") and active_tab != "account":
        return redirect(url_for("index"))
    return render_template(
        "login.html",
        active_tab=active_tab,
        account_authorized=session.get("user_role") in {ROLE_OWNER, ROLE_ADMIN},
        account_roles=ALL_ROLES,
    )


@app.route("/login", methods=["POST"])
def login_post():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email:
        flash("Email address is required.", "error")
        return redirect(url_for("login", tab="auth"))
    if not validate_email(email):
        flash("Please enter a valid RFC-compliant email address.", "error")
        return redirect(url_for("login", tab="auth"))
    if not password:
        flash("Password is required.", "error")
        return redirect(url_for("login", tab="auth"))

    # 1. Firebase live auth
    fb_data, fb_err = authenticate_with_firebase(email, password)
    if fb_data:
        uid = fb_data.get("localId", "uid")
        profile = get_user_profile_from_firestore(uid, email)
        session["authenticated"] = True
        session["user_email"] = email
        session["user_name"] = profile.get("name", email.split("@")[0])
        session["user_role"] = profile.get("role", ROLE_ADMIN)
        session["user_uid"] = uid
        return redirect(url_for("index"))

    # 2. Demo fallback
    user_email = email.lower()
    if user_email in DEMO_USERS and DEMO_USERS[user_email]["password"] == password:
        u = DEMO_USERS[user_email]
        session["authenticated"] = True
        session["user_email"] = user_email
        session["user_name"] = u["name"]
        session["user_role"] = u["role"]
        session["user_uid"] = u["uid"]
        return redirect(url_for("index"))

    flash("Authentication rejected: Incorrect email or password.", "error")
    return redirect(url_for("login", tab="auth"))


@app.route("/reset-password", methods=["POST"])
def reset_password_post():
    reset_email = request.form.get("reset_email", "").strip()
    if not validate_email(reset_email):
        flash("Valid enterprise email format required.", "error")
    else:
        code, error = send_password_reset_code(reset_email.lower())
        if code:
            session["password_reset"] = {
                "email": reset_email.lower(), "code": code,
                "expires": (datetime.utcnow().timestamp() + 600), "attempts": 0,
            }
            flash("A verification code was sent to the registered email address.", "success")
            return redirect(url_for("login", tab="verify"))
        flash(error, "error")
    return redirect(url_for("login", tab="reset"))


@app.route("/reset-password/verify", methods=["POST"])
def verify_reset_code():
    recovery = session.get("password_reset", {})
    code = request.form.get("code", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    if not recovery or datetime.utcnow().timestamp() > recovery.get("expires", 0):
        session.pop("password_reset", None)
        flash("The recovery code has expired. Request a new code.", "error")
        return redirect(url_for("login", tab="reset"))
    if recovery.get("attempts", 0) >= 5 or not secrets.compare_digest(code, recovery.get("code", "")):
        recovery["attempts"] = recovery.get("attempts", 0) + 1
        session["password_reset"] = recovery
        flash("Invalid verification code.", "error")
        return redirect(url_for("login", tab="verify"))
    if len(password) < 8 or password != confirm_password:
        flash("Passwords must match and contain at least 8 characters.", "error")
        return redirect(url_for("login", tab="verify"))
    ok, error = set_password(recovery["email"], password)
    session.pop("password_reset", None)
    flash("Your password has been reset. Please sign in.", "success" if ok else "error")
    if not ok:
        flash(error, "error")
    return redirect(url_for("login", tab="auth" if ok else "reset"))


@app.route("/account/create", methods=["POST"])
def create_account_post():
    """First-page account form; authorization is enforced by _ENDPOINT_ROLES."""
    return _create_user_from_request("account")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ----------------------------------------------------
# DASHBOARDS
# ----------------------------------------------------
@app.route("/dashboard")
def dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_DASHBOARD):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    products = get_products()
    customers = get_customers()
    suppliers = get_suppliers()
    materials = get_raw_materials()
    production_orders = get_production_orders()
    low_stock_materials = [
        m for m in materials
        if float(m.get("stock_qty", 0.0)) <= float(m.get("min_stock_level", 0.0))
    ]
    finished_stock = sum(int(p.get("stock_qty", 0)) for p in products)

    metrics = {
        "total_products": len(products),
        "total_customers": len(customers),
        "total_suppliers": len(suppliers),
        "total_raw_materials": len(materials),
        "total_production_orders": len(production_orders),
        "pending_production_orders": len([o for o in production_orders if o.get("status") in ["Pending", "In Progress"]]),
        "completed_production_orders": len([o for o in production_orders if o.get("status") == "Completed"]),
        "total_raw_material_stock": sum(float(m.get("stock_qty", 0.0)) for m in materials),
        "total_finished_goods_stock": finished_stock,
        "low_stock_materials": len(low_stock_materials),
        "total_users": len({email.lower() for email in DEMO_USERS} | {u.get("email", "").lower() for u in get_users()}),
    }

    # Chart 1: Product categories
    cat_counts = {}
    for p in products:
        c = p.get("category", "Other")
        cat_counts[c] = cat_counts.get(c, 0) + 1
    product_cat_data = {"labels": list(cat_counts.keys()), "values": list(cat_counts.values())}

    # Chart 2: Customer types
    type_counts = {}
    for c in customers:
        t = c.get("customer_type", "Retailer")
        type_counts[t] = type_counts.get(t, 0) + 1
    customer_type_data = {"names": list(type_counts.keys()), "values": list(type_counts.values())}

    # Chart 3: Material rates
    mat_names = [m.get("name", "Item") for m in materials]
    mat_rates = [float(m.get("purchase_rate", 0.0)) for m in materials]
    material_rate_data = {"names": mat_names, "values": mat_rates}

    return render_template(
        "dashboard.html",
        current_page=PAGE_DASHBOARD,
        metrics=metrics,
        recent_products=products[-5:] if products else [],
        recent_customers=customers[-5:] if customers else [],
        product_cat_data=product_cat_data,
        customer_type_data=customer_type_data,
        material_rate_data=material_rate_data,
        low_stock_materials=low_stock_materials,
        recent_production=list(reversed(production_orders[-8:])),
        all_roles=ALL_ROLES,
    )


@app.route("/sales-dashboard")
def sales_dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_SALES_DASHBOARD):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    orders = get_orders()
    invoices = get_invoices()
    payments = get_payments()
    if session.get("user_role") == ROLE_SALESMAN:
        salesman_id = session.get("user_uid")
        orders = get_orders_by_salesman(salesman_id)
        invoices = [invoice for invoice in invoices if invoice.get("salesman_id") == salesman_id]
        owned_invoice_numbers = {invoice.get("invoice_number") for invoice in invoices}
        payments = [payment for payment in payments if payment.get("invoice_number") in owned_invoice_numbers]

    # Source documents are uniquely keyed in Firestore.  De-duplicate defensively
    # so dashboard totals cannot be inflated by legacy/imported duplicate rows.
    def unique(records, key):
        seen = set()
        output = []
        for record in records:
            value = record.get(key)
            if value and value not in seen:
                seen.add(value)
                output.append(record)
        return output
    orders = unique(orders, "order_id")
    invoices = unique(invoices, "invoice_number")
    payments = unique(payments, "payment_id")

    total_sales = sum(float(inv.get("total_amount", 0.0)) for inv in invoices)
    total_paid = sum(float(p.get("amount", 0.0)) for p in payments)
    outstanding_payments = max(0.0, total_sales - total_paid)

    metrics = {
        "total_orders": len(orders),
        "pending_orders": len([o for o in orders if o.get("status") in ["Submitted", "Pending Approval"]]),
        "approved_orders": len([o for o in orders if o.get("status") in ["Approved", "Invoiced", "Dispatched"]]),
        "total_sales": total_sales,
        "total_invoices": len(invoices),
        "outstanding_payments": outstanding_payments,
    }

    # Product sales chart
    prod_sales = {}
    for inv in invoices:
        for it in inv.get("items", []):
            pn = it.get("name", "Product")
            prod_sales[pn] = prod_sales.get(pn, 0.0) + float(it.get("total_amount", 0.0))
    product_chart_data = {"names": list(prod_sales.keys()), "values": list(prod_sales.values())}

    # Customer sales chart
    cust_sales = {}
    for inv in invoices:
        cn = inv.get("customer_name", "Customer")
        cust_sales[cn] = cust_sales.get(cn, 0.0) + float(inv.get("total_amount", 0.0))
    customer_chart_data = {"names": list(cust_sales.keys()), "values": list(cust_sales.values())}

    # Status chart
    status_counts = {}
    for o in orders:
        st = o.get("status", "Submitted")
        status_counts[st] = status_counts.get(st, 0) + 1
    status_chart_data = {"labels": list(status_counts.keys()), "values": list(status_counts.values())}

    # Trend chart
    daily_sales = {}
    for inv in invoices:
        date = inv.get("invoice_date", "")
        daily_sales[date] = daily_sales.get(date, 0.0) + float(inv.get("total_amount", 0.0))
    trend_chart_data = {"dates": sorted(daily_sales), "values": [daily_sales[d] for d in sorted(daily_sales)]}

    recent_orders = list(reversed(orders[-8:])) if orders else []

    return render_template(
        "sales_dashboard.html",
        current_page=PAGE_SALES_DASHBOARD,
        metrics=metrics,
        recent_orders=recent_orders,
        product_chart_data=product_chart_data,
        customer_chart_data=customer_chart_data,
        status_chart_data=status_chart_data,
        trend_chart_data=trend_chart_data,
    )


# ----------------------------------------------------
# ORDERS (NEW ORDER & MY ORDERS & ORDER MANAGEMENT)
# ----------------------------------------------------
@app.route("/new-order")
def new_order():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_NEW_ORDER):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    customers = [c for c in get_customers() if c.get("status") == "Active"]
    products = [p for p in get_products() if p.get("status") == "Active"]

    for p in products:
        p["available_stock"] = get_product_available_stock(p["product_id"])

    # Determine selected customer
    sel_cid = request.args.get("customer_id")
    if not sel_cid and customers:
        sel_cid = customers[0]["customer_id"]

    customer_obj = next((c for c in customers if c["customer_id"] == sel_cid), customers[0] if customers else None)
    customer_state = customer_obj.get("state", "Tamil Nadu") if customer_obj else "Tamil Nadu"
    is_intra = customer_state.strip().lower() == "tamil nadu"

    cart_items = session.get("cart_items", [])
    summary = compute_order_summary(cart_items, customer_state)

    return render_template(
        "new_order.html",
        current_page=PAGE_NEW_ORDER,
        active_customers=customers,
        active_products=products,
        customer_obj=customer_obj,
        states=INDIAN_STATES,
        today=datetime.utcnow().strftime("%Y-%m-%d"),
        customer_state=customer_state,
        is_intra=is_intra,
        cart_items=cart_items,
        summary=summary,
    )


@app.route("/cart/add", methods=["POST"])
def add_to_cart():
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    customer_id = request.form.get("customer_id")
    product_id = request.form.get("product_id")
    try:
        quantity = int(request.form.get("quantity", 1))
        discount_percent = float(request.form.get("discount_percent", 0.0))
    except (TypeError, ValueError):
        flash("Quantity and discount must be valid numbers.", "error")
        return redirect(url_for("new_order", customer_id=request.form.get("customer_id")))

    if quantity < 1:
        flash("Order quantity must be at least 1 packet.", "error")
        return redirect(url_for("new_order", customer_id=request.form.get("customer_id")))
    if discount_percent < 0 or discount_percent > 100:
        flash("Discount must be between 0 and 100 percent.", "error")
        return redirect(url_for("new_order", customer_id=request.form.get("customer_id")))

    products = get_products()
    prod_obj = next((p for p in products if p["product_id"] == product_id), None)
    if not prod_obj:
        flash("Invalid product selected.", "error")
        return redirect(url_for("new_order", customer_id=customer_id))

    available_stock = get_product_available_stock(product_id)
    cart_for_stock = list(session.get("cart_items", []))
    cart_line = next((it for it in cart_for_stock if it["product_id"] == product_id), None)
    existing_quantity = int(cart_line.get("quantity", 0)) if cart_line else 0
    if existing_quantity + quantity > available_stock:
        remaining = max(0, available_stock - existing_quantity)
        flash(
            f"Cannot add {quantity} packets. Only {remaining} packet(s) remain available.",
            "error",
        )
        return redirect(url_for("new_order", customer_id=customer_id))

    if "cart_items" not in session:
        session["cart_items"] = []

    cart = list(session["cart_items"])
    existing = next((it for it in cart if it["product_id"] == product_id), None)
    if existing:
        existing["quantity"] += quantity
        existing["discount_percent"] = discount_percent
    else:
        cart.append({
            "product_id": product_id,
            "name": prod_obj.get("name", ""),
            "category": prod_obj.get("category", ""),
            "pack_size": prod_obj.get("pack_size", "200g"),
            "hsn_code": prod_obj.get("hsn_code", "19059040"),
            "unit_price": float(prod_obj.get("selling_price", 0.0)),
            "quantity": quantity,
            "discount_percent": discount_percent,
            "gst_rate": float(prod_obj.get("gst_rate", 5.0)),
        })

    session["cart_items"] = cart
    return redirect(url_for("new_order", customer_id=customer_id))


@app.route("/cart/remove", methods=["POST"])
def remove_from_cart():
    customer_id = request.form.get("customer_id")
    product_id = request.form.get("product_id")
    cart = session.get("cart_items", [])
    session["cart_items"] = [it for it in cart if it["product_id"] != product_id]
    return redirect(url_for("new_order", customer_id=customer_id))


@app.route("/order/customer/add", methods=["POST"])
def add_order_customer_post():
    if not session.get("authenticated") or not check_page_permission(
        session.get("user_role", ""), PAGE_NEW_ORDER
    ):
        flash("Unauthorized.", "error")
        return redirect(url_for("index"))

    payload = {
        "customer_id": f"CUST-{uuid.uuid4().hex[:8].upper()}",
        "name": request.form.get("name", "").strip(),
        "customer_type": request.form.get("customer_type", "Retailer"),
        "phone": request.form.get("phone", "").strip(),
        "email": request.form.get("email", "").strip(),
        "city": request.form.get("city", "").strip(),
        "state": request.form.get("state", "").strip(),
        "gstin": request.form.get("gstin", "").strip().upper(),
        "address": request.form.get("address", "").strip(),
        "special_pricing": "Standard",
        "status": "Active",
        "created_by": session.get("user_uid", ""),
    }
    valid, message = validate_customer_data(payload)
    if not valid:
        flash(message, "error")
        return redirect(url_for("new_order"))
    if not payload["state"]:
        flash("Customer state is required for GST calculation.", "error")
        return redirect(url_for("new_order"))
    if not add_customer(payload):
        flash("Customer details could not be saved.", "error")
        return redirect(url_for("new_order"))

    record_activity_log(
        session.get("user_uid", ""),
        session.get("user_role", ""),
        "CUSTOMER_CREATED_FROM_ORDER",
        "add_order_customer_post",
        payload["customer_id"],
    )
    flash(f"Customer {payload['customer_id']} added.", "success")
    return redirect(url_for("new_order", customer_id=payload["customer_id"]))


@app.route("/order/submit", methods=["POST"])
def submit_order():
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    customer_id = request.form.get("customer_id")
    notes = request.form.get("notes", "").strip()
    expected_delivery_date = request.form.get("expected_delivery_date", "").strip()
    customers = get_customers()
    customer_obj = next(
        (c for c in customers if c["customer_id"] == customer_id and c.get("status") == "Active"),
        None,
    )
    if not customer_obj:
        flash("Select a valid active customer.", "error")
        return redirect(url_for("new_order", customer_id=customer_id))

    cart = session.get("cart_items", [])
    if not cart:
        flash("Cannot submit an empty order.", "error")
        return redirect(url_for("new_order", customer_id=customer_id))

    try:
        datetime.strptime(expected_delivery_date, "%Y-%m-%d")
        if expected_delivery_date < datetime.utcnow().strftime("%Y-%m-%d"):
            raise ValueError
    except ValueError:
        flash("Enter a valid expected delivery date that is today or later.", "error")
        return redirect(url_for("new_order", customer_id=customer_id))

    products = {p.get("product_id"): p for p in get_products()}
    validated_cart = []
    for item in cart:
        product = products.get(item.get("product_id"))
        try:
            quantity = int(item.get("quantity", 0))
            discount_percent = float(item.get("discount_percent", 0.0))
        except (TypeError, ValueError):
            quantity = 0
            discount_percent = -1
        if not product or product.get("status") != "Active" or quantity < 1:
            flash("An order item is invalid or no longer available.", "error")
            return redirect(url_for("new_order", customer_id=customer_id))
        if not 0 <= discount_percent <= 100:
            flash("An order item has an invalid discount.", "error")
            return redirect(url_for("new_order", customer_id=customer_id))
        if quantity > get_product_available_stock(product["product_id"]):
            flash(f"Insufficient stock for {product.get('name', 'product')}.", "error")
            return redirect(url_for("new_order", customer_id=customer_id))
        validated_cart.append({
            **item,
            "unit_price": float(product.get("selling_price", 0.0)),
            "gst_rate": float(product.get("gst_rate", 5.0)),
            "quantity": quantity,
            "discount_percent": discount_percent,
        })

    cust_state = customer_obj.get("state", "Tamil Nadu")
    summary = compute_order_summary(validated_cart, cust_state)
    user_id = session.get("user_uid")
    user_name = session.get("user_name")
    user_role = session.get("user_role")

    order_payload = {
        "salesman_id": user_id,
        "salesman_name": user_name,
        "salesman_role": user_role,
        "creator_id": user_id,
        "creator_name": user_name,
        "creator_role": user_role,
        "customer_id": customer_id,
        "customer_name": customer_obj.get("name", ""),
        "customer_state": cust_state,
        "customer_address": customer_obj.get("address", ""),
        "customer_gstin": customer_obj.get("gstin", ""),
        "order_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "expected_delivery_date": expected_delivery_date,
        "items": summary["items"],
        "total_quantity": summary["total_quantity"],
        "taxable_amount": summary["subtotal"],
        "cgst_amount": summary["cgst"],
        "sgst_amount": summary["sgst"],
        "igst_amount": summary["igst"],
        "total_gst": summary["total_gst"],
        "total_amount": summary["total_amount"],
        "is_intra_state": summary["is_intra_state"],
        "notes": notes,
        "status": "Pending Approval",
        "production_status": "Pending",
        "delivery_status": "Pending",
    }

    if not create_order(order_payload):
        flash("Order could not be saved. Please try again.", "error")
        return redirect(url_for("new_order", customer_id=customer_id))
    session["cart_items"] = []
    record_activity_log(
        user_id or "",
        user_role or "",
        "ORDER_SUBMITTED",
        "submit_order",
        order_payload.get("order_id", ""),
    )
    flash(f"Order {order_payload.get('order_id')} submitted for admin approval.", "success")
    return redirect(url_for("my_orders"))


@app.route("/my-orders")
def my_orders():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_MY_ORDERS):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    user_uid = session.get("user_uid")
    orders = get_orders_by_salesman(user_uid)

    view_oid = request.args.get("view_order")
    selected_order = next((o for o in orders if o["order_id"] == view_oid), None) if view_oid else None

    metrics = {
        "total_val": sum(float(o.get("total_amount", 0.0)) for o in orders),
        "pending_cnt": len([o for o in orders if o.get("status") in ["Submitted", "Pending Approval"]]),
        "approved_cnt": len([o for o in orders if o.get("status") in ["Approved", "Invoiced", "Dispatched"]]),
        "rejected_cnt": len([o for o in orders if o.get("status") == "Rejected"]),
    }

    return render_template(
        "my_orders.html",
        current_page=PAGE_MY_ORDERS,
        orders=orders,
        metrics=metrics,
        selected_order=selected_order,
    )


@app.route("/order-management")
def order_management():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_ORDER_MANAGEMENT):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    orders = get_orders()
    search_kw = request.args.get("search", "").strip()
    sel_salesman = request.args.get("salesman", "All")
    sel_status = request.args.get("status", "All")

    salesmen = sorted(list(set(o.get("salesman_name", "") for o in orders if o.get("salesman_name"))))
    statuses = ["All", "Pending Approval", "Submitted", "Approved", "Invoiced", "Dispatched", "Rejected"]

    filtered = list(orders)
    if search_kw:
        k = search_kw.lower()
        filtered = [o for o in filtered if k in o.get("order_id", "").lower() or k in o.get("customer_name", "").lower()]
    if sel_salesman != "All":
        filtered = [o for o in filtered if o.get("salesman_name") == sel_salesman]
    if sel_status != "All":
        filtered = [o for o in filtered if o.get("status") == sel_status]

    inspect_oid = request.args.get("inspect_order")
    target_order = next((o for o in filtered if o["order_id"] == inspect_oid), None) if inspect_oid else (filtered[0] if filtered else None)

    stock_audit_rows = []
    has_stock_shortage = False
    shortage_details = []

    if target_order:
        for it in target_order.get("items", []):
            pid = it.get("product_id")
            req_qty = int(it.get("quantity", 0))
            avail = get_product_available_stock(pid)
            if target_order.get("status") in ["Submitted", "Pending Approval"]:
                can_fulfill = avail >= req_qty
                if not can_fulfill:
                    has_stock_shortage = True
                    shortage_details.append(f"{it.get('name')}: Shortage of {req_qty - avail} packets (Available: {avail}, Requested: {req_qty})")
                st_str = "SUFFICIENT" if can_fulfill else f"SHORTAGE ({req_qty - avail} pkts)"
            else:
                st_str = "RESERVED / PROCESSED"

            stock_audit_rows.append({
                "sku": pid,
                "name": it.get("name"),
                "pack_size": it.get("pack_size", "200g"),
                "req_qty": req_qty,
                "avail_stock": avail,
                "unit_price": float(it.get("unit_price", 0.0)),
                "total": float(it.get("total_amount", 0.0)),
                "status": st_str,
            })

    return render_template(
        "order_management.html",
        current_page=PAGE_ORDER_MANAGEMENT,
        filtered_orders=filtered,
        salesmen=salesmen,
        statuses=statuses,
        search_kw=search_kw,
        sel_salesman=sel_salesman,
        sel_status=sel_status,
        target_order=target_order,
        stock_audit_rows=stock_audit_rows,
        has_stock_shortage=has_stock_shortage,
        shortage_details=shortage_details,
    )


@app.route("/order/approve", methods=["POST"])
def approve_order_post():
    if session.get("user_role") not in [ROLE_OWNER, ROLE_ADMIN]:
        flash("Unauthorized action.", "error")
        return redirect(url_for("order_management"))

    order_id = request.form.get("order_id")
    orders = get_orders()
    order_obj = next((o for o in orders if o["order_id"] == order_id), None)
    if not order_obj:
        flash("Order not found.", "error")
        return redirect(url_for("order_management"))
    if order_obj.get("status") not in ["Pending Approval", "Submitted"]:
        flash("Only orders awaiting approval can be approved.", "error")
        return redirect(url_for("order_management", inspect_order=order_id))

    # Reserve stock atomically
    items = order_obj.get("items", [])
    reserved_items = []
    for it in items:
        ok = reserve_product_stock(it["product_id"], int(it["quantity"]))
        if not ok:
            for reserved_item in reserved_items:
                release_reserved_stock(reserved_item["product_id"], int(reserved_item["quantity"]))
            flash(f"Insufficient stock to reserve {it['name']}.", "error")
            return redirect(url_for("order_management", inspect_order=order_id))
        reserved_items.append(it)

    if not update_order_status(order_id, "Approved", "Approved by factory admin."):
        for item in items:
            release_reserved_stock(item["product_id"], int(item["quantity"]))
        flash("Order approval could not be saved.", "error")
        return redirect(url_for("order_management", inspect_order=order_id))
    record_activity_log(session.get("user_uid", ""), session.get("user_role", ""), "ORDER_APPROVED", "approve_order_post", order_id)
    flash(f"Order {order_id} approved. Stock reserved successfully.", "success")
    return redirect(url_for("order_management", inspect_order=order_id))


@app.route("/order/reject", methods=["POST"])
def reject_order_post():
    if session.get("user_role") not in [ROLE_OWNER, ROLE_ADMIN]:
        flash("Unauthorized action.", "error")
        return redirect(url_for("order_management"))

    order_id = request.form.get("order_id")
    rejection_reason = request.form.get("rejection_reason", "").strip()
    order_obj = next((o for o in get_orders() if o.get("order_id") == order_id), None)
    if not order_obj:
        flash("Order not found.", "error")
        return redirect(url_for("order_management"))
    if order_obj.get("status") not in ["Pending Approval", "Submitted"]:
        flash("Only orders awaiting approval can be rejected.", "error")
        return redirect(url_for("order_management", inspect_order=order_id))
    if not rejection_reason:
        flash("Rejection reason is mandatory.", "error")
        return redirect(url_for("order_management", inspect_order=order_id))

    if not update_order_status(order_id, "Rejected", f"Rejected: {rejection_reason}"):
        flash("Order rejection could not be saved.", "error")
        return redirect(url_for("order_management", inspect_order=order_id))
    flash(f"Order {order_id} marked as Rejected.", "warning")
    return redirect(url_for("order_management", inspect_order=order_id))


@app.route("/order/revoke", methods=["POST"])
def revoke_approval_post():
    if session.get("user_role") not in [ROLE_OWNER, ROLE_ADMIN]:
        flash("Unauthorized action.", "error")
        return redirect(url_for("order_management"))

    order_id = request.form.get("order_id")
    orders = get_orders()
    order_obj = next((o for o in orders if o["order_id"] == order_id), None)
    if order_obj:
        for it in order_obj.get("items", []):
            release_reserved_stock(it["product_id"], int(it["quantity"]))
        update_order_status(order_id, "Submitted", "Approval revoked; stock released.")
        flash(f"Approval revoked for Order {order_id}.", "info")
    return redirect(url_for("order_management", inspect_order=order_id))


# ----------------------------------------------------
# GST BILLING & INVOICE HISTORY
# ----------------------------------------------------
@app.route("/gst-billing")
def gst_billing():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_GST_BILLING):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    orders = get_orders()
    invoices = get_invoices()
    approved_orders = [o for o in orders if o.get("status") == "Approved"]
    customers = get_customers()
    selected_customer_id = request.args.get("customer_id", "")
    if selected_customer_id:
        approved_orders = [o for o in approved_orders if o.get("customer_id") == selected_customer_id]

    active_tab = request.args.get("tab", "generate")
    sel_oid = request.args.get("order_id")
    if not sel_oid and approved_orders:
        sel_oid = approved_orders[0]["order_id"]

    selected_order = next((o for o in approved_orders if o["order_id"] == sel_oid), approved_orders[0] if approved_orders else None)
    invoice_totals = None
    is_intra = True
    cust_state = "Tamil Nadu"
    existing_inv = None

    if selected_order:
        cust_state = selected_order.get("customer_state", "Tamil Nadu")
        invoice_totals = calculate_invoice_totals(selected_order.get("items", []), cust_state)
        is_intra = invoice_totals["is_intra_state"]
        existing_inv = next((inv for inv in invoices if inv.get("order_id") == selected_order["order_id"]), None)

    return render_template(
        "gst_billing.html",
        current_page=PAGE_GST_BILLING,
        active_tab=active_tab,
        approved_orders=approved_orders,
        selected_order=selected_order,
        invoice_totals=invoice_totals,
        is_intra=is_intra,
        cust_state=cust_state,
        existing_inv=existing_inv,
        invoices=invoices,
        customers=customers,
        selected_customer_id=selected_customer_id,
    )


@app.route("/invoice/generate", methods=["POST"])
def generate_invoice_post():
    if session.get("user_role") not in [ROLE_OWNER, ROLE_ADMIN, ROLE_AUDITOR]:
        flash("Unauthorized action.", "error")
        return redirect(url_for("gst_billing"))

    order_id = request.form.get("order_id")
    orders = get_orders()
    order_obj = next((o for o in orders if o["order_id"] == order_id), None)
    if not order_obj:
        flash("Order not found.", "error")
        return redirect(url_for("gst_billing"))

    # Guard duplicate
    invoices = get_invoices()
    existing = next((inv for inv in invoices if inv.get("order_id") == order_id), None)
    if existing:
        flash(f"Invoice already generated: {existing['invoice_number']}", "warning")
        return redirect(url_for("gst_billing", tab="roster"))

    cust_state = order_obj.get("customer_state", "Tamil Nadu")
    totals = calculate_invoice_totals(order_obj.get("items", []), cust_state)

    invoice_payload = {
        "order_id": order_id,
        "salesman_id": order_obj.get("salesman_id", ""),
        "salesman_name": order_obj.get("salesman_name", ""),
        "customer_id": order_obj.get("customer_id", ""),
        "customer_name": order_obj.get("customer_name", ""),
        "customer_state": cust_state,
        "customer_address": order_obj.get("customer_address", ""),
        "customer_gstin": order_obj.get("customer_gstin", ""),
        "invoice_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "items": totals["items"],
        "is_intra_state": totals["is_intra_state"],
        "total_taxable_value": totals["total_taxable_value"],
        "total_cgst": totals["total_cgst"],
        "total_sgst": totals["total_sgst"],
        "total_igst": totals["total_igst"],
        "total_gst": totals["total_gst"],
        "total_amount": totals["total_amount"],
        "created_by": session.get("user_uid", "usr_admin"),
        "payment_status": "Unpaid",
        "dispatch_status": "Pending",
    }

    create_invoice(invoice_payload)
    update_order_status(order_id, "Invoiced", f"Invoiced under {invoice_payload.get('invoice_number')}")
    flash(f"Statutory Invoice {invoice_payload.get('invoice_number')} generated successfully.", "success")
    return redirect(url_for("invoice_history"))


@app.route("/invoice-history")
def invoice_history():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_INVOICE_HISTORY):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    invoices = get_invoices()
    if session.get("user_role") == ROLE_SALESMAN:
        invoices = [inv for inv in invoices if inv.get("salesman_id") == session.get("user_uid")]
    search_kw = request.args.get("search", "").strip()
    sel_cust = request.args.get("customer", "All")
    sel_status = request.args.get("status", "All")

    cust_options = sorted(list(set(i.get("customer_name", "") for i in invoices if i.get("customer_name"))))
    statuses = ["All", "Unpaid", "Partially Paid", "Paid"]

    filtered = list(invoices)
    if search_kw:
        k = search_kw.lower()
        filtered = [i for i in filtered if k in i.get("invoice_number", "").lower() or k in i.get("customer_name", "").lower() or k in i.get("order_id", "").lower()]
    if sel_cust != "All":
        filtered = [i for i in filtered if i.get("customer_name") == sel_cust]
    if sel_status != "All":
        filtered = [i for i in filtered if i.get("payment_status") == sel_status]

    inspect_inv_no = request.args.get("inspect_inv")
    target_inv = next((i for i in filtered if i["invoice_number"] == inspect_inv_no), None) if inspect_inv_no else (filtered[0] if filtered else None)

    return render_template(
        "invoice_history.html",
        current_page=PAGE_INVOICE_HISTORY,
        filtered_invoices=filtered,
        cust_options=cust_options,
        statuses=statuses,
        search_kw=search_kw,
        sel_cust=sel_cust,
        sel_status=sel_status,
        target_inv=target_inv,
    )


@app.route("/invoice/pdf/<path:invoice_number>")
def download_invoice_pdf(invoice_number):
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    invoices = get_invoices()
    inv_obj = next((i for i in invoices if i["invoice_number"] == invoice_number), None)
    if not inv_obj:
        flash("Invoice not found.", "error")
        return redirect(url_for("invoice_history"))
    if session.get("user_role") == ROLE_SALESMAN and inv_obj.get("salesman_id") != session.get("user_uid"):
        flash("Unauthorized: invoice is outside your sales records.", "error")
        return redirect(url_for("invoice_history"))

    pdf_bytes = generate_invoice_pdf(inv_obj)
    clean_fname = invoice_number.replace("/", "_") + ".pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=clean_fname,
    )


# ----------------------------------------------------
# DISPATCH MANAGEMENT
# ----------------------------------------------------
@app.route("/dispatch")
def dispatch():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_DISPATCH):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    active_tab = request.args.get("tab", "gatepass")
    invoices = get_invoices()
    pending_invoices = [i for i in invoices if i.get("dispatch_status") != "Completed"]

    sel_inv_no = request.args.get("invoice_number")
    if not sel_inv_no and pending_invoices:
        sel_inv_no = pending_invoices[0]["invoice_number"]

    target_inv = next((i for i in pending_invoices if i["invoice_number"] == sel_inv_no), pending_invoices[0] if pending_invoices else None)
    dispatch_items_review = []

    if target_inv:
        for it in target_inv.get("items", []):
            pid = it.get("product_id")
            inv_q = int(it.get("quantity", 0))
            disp_q = int(it.get("dispatched_quantity", 0))
            pending_q = inv_q - disp_q
            avail = get_product_available_stock(pid)
            dispatch_items_review.append({
                "product_id": pid,
                "name": it.get("name"),
                "invoiced_qty": inv_q,
                "already_dispatched": disp_q,
                "pending_qty": pending_q,
                "avail_stock": avail,
                "recommended_qty": min(pending_q, avail),
            })

    ledger = get_stock_ledger()
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    return render_template(
        "dispatch.html",
        current_page=PAGE_DISPATCH,
        active_tab=active_tab,
        pending_invoices=pending_invoices,
        target_inv=target_inv,
        dispatch_items_review=dispatch_items_review,
        ledger=ledger,
        today_str=today_str,
    )


@app.route("/dispatch/confirm", methods=["POST"])
def confirm_dispatch_post():
    if session.get("user_role") not in [ROLE_OWNER, ROLE_ADMIN]:
        flash("Unauthorized action.", "error")
        return redirect(url_for("dispatch"))

    invoice_number = request.form.get("invoice_number")
    dispatch_date = request.form.get("dispatch_date")
    transport_ref = request.form.get("transport_ref", "").strip()
    transporter_name = request.form.get("transporter_name", "").strip()
    gate_pass_notes = request.form.get("gate_pass_notes", "").strip()

    invoices = get_invoices()
    inv_obj = next((i for i in invoices if i["invoice_number"] == invoice_number), None)
    if not inv_obj:
        flash("Invoice not found.", "error")
        return redirect(url_for("dispatch"))

    items = inv_obj.get("items", [])
    dispatch_payload_items = []
    all_fulfilled = True

    for it in items:
        pid = it.get("product_id")
        inv_q = int(it.get("quantity", 0))
        cur_disp = int(it.get("dispatched_quantity", 0))
        qty_to_disp = int(request.form.get(f"disp_qty_{pid}", 0))

        if qty_to_disp > 0:
            avail = get_product_available_stock(pid)
            is_ok, err_msg, _ = validate_dispatch_quantity(pid, qty_to_disp, inv_q, cur_disp, avail)
            if not is_ok:
                flash(err_msg, "error")
                return redirect(url_for("dispatch", invoice_number=invoice_number))

            # Deduct stock atomically
            ok = record_stock_dispatch(pid, qty_to_disp, invoice_number, session.get("user_uid", "usr_sup"))
            if not ok:
                flash(f"Stock deduction failed for {it['name']}.", "error")
                return redirect(url_for("dispatch", invoice_number=invoice_number))

            dispatch_payload_items.append({
                "product_id": pid,
                "name": it.get("name"),
                "quantity": qty_to_disp,
            })

        new_total_disp = cur_disp + qty_to_disp
        it["dispatched_quantity"] = new_total_disp
        if new_total_disp < inv_q:
            all_fulfilled = False

    if not dispatch_payload_items:
        flash("Please enter a dispatch quantity greater than zero.", "error")
        return redirect(url_for("dispatch", invoice_number=invoice_number))

    # Log dispatch record
    create_dispatch({
        "invoice_number": invoice_number,
        "order_id": inv_obj.get("order_id"),
        "customer_id": inv_obj.get("customer_id"),
        "customer_name": inv_obj.get("customer_name"),
        "dispatch_date": dispatch_date,
        "transport_ref": transport_ref,
        "transporter_name": transporter_name,
        "items": dispatch_payload_items,
        "notes": gate_pass_notes,
        "dispatched_by": session.get("user_uid", "usr_sup"),
    })

    new_inv_status = "Completed" if all_fulfilled else "Partially Dispatched"
    update_invoice(invoice_number, {
        "dispatch_status": new_inv_status,
        "items": items,
    })

    if inv_obj.get("order_id"):
        new_order_st = "Dispatched" if all_fulfilled else "Partially Dispatched"
        update_order_status(inv_obj.get("order_id"), new_order_st, f"Dispatched under LR {transport_ref}")

    flash(f"Outward dispatch confirmed under LR {transport_ref}. Stock reduced and ledger updated.", "success")
    return redirect(url_for("dispatch", tab="ledger"))


# ----------------------------------------------------
# PAYMENTS
# ----------------------------------------------------
@app.route("/payments")
def payments():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_PAYMENTS):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    active_tab = request.args.get("tab", "record")
    invoices = get_invoices()
    payments_list = get_payments()
    if session.get("user_role") == ROLE_SALESMAN:
        invoices = [inv for inv in invoices if inv.get("salesman_id") == session.get("user_uid")]
        payments_list = [payment for payment in payments_list if payment.get("invoice_number") in {inv.get("invoice_number") for inv in invoices}]
        active_tab = "ledger"

    customer_options = sorted(list(set(i.get("customer_name") for i in invoices if i.get("customer_name"))))
    sel_cust = request.args.get("customer", "All")

    eligible_invoices = list(invoices)
    if sel_cust != "All":
        eligible_invoices = [i for i in eligible_invoices if i.get("customer_name") == sel_cust]

    sel_inv_no = request.args.get("invoice_number")
    if not sel_inv_no and eligible_invoices:
        sel_inv_no = eligible_invoices[0]["invoice_number"]

    target_inv = next((i for i in eligible_invoices if i["invoice_number"] == sel_inv_no), eligible_invoices[0] if eligible_invoices else None)
    balance_summary = None
    past_payments = []

    if target_inv:
        past_payments = get_payments_for_invoice(target_inv["invoice_number"])
        balance_summary = compute_invoice_payment_status(target_inv.get("total_amount", 0.0), past_payments)

    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    return render_template(
        "payments.html",
        current_page=PAGE_PAYMENTS,
        active_tab=active_tab,
        invoices=invoices,
        eligible_invoices=eligible_invoices,
        customer_options=customer_options,
        sel_cust=sel_cust,
        target_inv=target_inv,
        balance_summary=balance_summary,
        past_payments=past_payments,
        payments=payments_list,
        today_str=today_str,
    )


@app.route("/payment/record", methods=["POST"])
def record_payment_post():
    if session.get("user_role") not in [ROLE_OWNER, ROLE_ADMIN, ROLE_SALESMAN]:
        flash("Unauthorized action.", "error")
        return redirect(url_for("payments"))

    invoice_number = request.form.get("invoice_number")
    amount = float(request.form.get("amount", 0.0))
    payment_mode = request.form.get("payment_mode")
    payment_date = request.form.get("payment_date")
    transaction_ref = request.form.get("transaction_ref", "").strip()
    remarks = request.form.get("remarks", "").strip()

    invoices = get_invoices()
    inv_obj = next((i for i in invoices if i["invoice_number"] == invoice_number), None)
    if not inv_obj:
        flash("Invoice not found.", "error")
        return redirect(url_for("payments"))

    past_p = get_payments_for_invoice(invoice_number)
    bal = compute_invoice_payment_status(inv_obj.get("total_amount", 0.0), past_p)

    if amount <= 0 or amount > bal["outstanding_balance"]:
        flash("Payment amount cannot exceed remaining outstanding balance.", "error")
        return redirect(url_for("payments", invoice_number=invoice_number))

    record_payment({
        "invoice_number": invoice_number,
        "customer_id": inv_obj.get("customer_id", ""),
        "customer_name": inv_obj.get("customer_name", ""),
        "amount": amount,
        "payment_mode": payment_mode,
        "payment_date": payment_date,
        "transaction_ref": transaction_ref,
        "remarks": remarks,
        "recorded_by": session.get("user_uid", "usr_admin"),
        "status": "Confirmed",
    })

    all_payments = get_payments_for_invoice(invoice_number)
    new_bal = compute_invoice_payment_status(inv_obj.get("total_amount", 0.0), all_payments)
    update_invoice(invoice_number, {
        "payment_status": new_bal["payment_status"],
        "outstanding_amount": new_bal["outstanding_balance"],
    })

    flash(f"Payment of Rs. {amount:.2f} successfully recorded.", "success")
    return redirect(url_for("payments", tab="ledger"))


# ----------------------------------------------------
# MASTER DATA (PRODUCTS, CUSTOMERS, SUPPLIERS, MATERIALS, USERS)
# ----------------------------------------------------
@app.route("/products")
def products():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_PRODUCTS):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    prods = get_products()
    active_tab = request.args.get("tab", "directory")
    search_kw = request.args.get("search", "").strip()
    sel_cat = request.args.get("category", "All")
    sel_status = request.args.get("status", "All")

    filtered = list(prods)
    if search_kw:
        k = search_kw.lower()
        filtered = [p for p in filtered if k in p.get("name", "").lower() or k in p.get("product_id", "").lower()]
    if sel_cat != "All":
        filtered = [p for p in filtered if p.get("category") == sel_cat]
    if sel_status != "All":
        filtered = [p for p in filtered if p.get("status") == sel_status]

    return render_template(
        "products.html",
        current_page=PAGE_PRODUCTS,
        active_tab=active_tab,
        filtered_products=filtered,
        categories=PRODUCT_CATEGORIES,
        search_kw=search_kw,
        sel_cat=sel_cat,
        sel_status=sel_status,
        can_edit=can_edit(session["user_role"]),
    )


@app.route("/product/add", methods=["POST"])
def add_product_post():
    if not can_edit(session.get("user_role")):
        flash("Unauthorized.", "error")
        return redirect(url_for("products"))

    payload = {
        "product_id": request.form.get("product_id", "").strip().upper(),
        "name": request.form.get("name", "").strip(),
        "category": request.form.get("category"),
        "pack_size": request.form.get("pack_size", "").strip(),
        "selling_price": float(request.form.get("selling_price", 0.0)),
        "gst_rate": float(request.form.get("gst_rate", 5.0)),
        "hsn_code": request.form.get("hsn_code", "").strip(),
        "description": request.form.get("description", "").strip(),
        "status": request.form.get("status", "Active"),
        "stock_qty": 0,
        "reserved_qty": 0,
    }

    ok, msg = validate_product_data(payload)
    if not ok:
        flash(msg, "error")
        return redirect(url_for("products", tab="add"))

    add_product(payload)
    flash(f"Product {payload['product_id']} registered successfully.", "success")
    return redirect(url_for("products", tab="directory"))


@app.route("/product/toggle", methods=["POST"])
def toggle_product_status():
    if not can_edit(session.get("user_role")):
        flash("Unauthorized.", "error")
        return redirect(url_for("products"))

    pid = request.form.get("product_id")
    toggle_status("products", "product_id", pid)
    flash(f"Status toggled for {pid}.", "info")
    return redirect(url_for("products"))


@app.route("/customers")
def customers():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_CUSTOMERS):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    custs = get_customers()
    active_tab = request.args.get("tab", "directory")
    return render_template(
        "customers.html",
        current_page=PAGE_CUSTOMERS,
        active_tab=active_tab,
        customers=custs,
        states=INDIAN_STATES,
        can_edit=can_edit(session["user_role"]),
    )


@app.route("/customer/add", methods=["POST"])
def add_customer_post():
    if not can_edit(session.get("user_role")):
        flash("Unauthorized.", "error")
        return redirect(url_for("customers"))

    payload = {
        "customer_id": request.form.get("customer_id", "").strip().upper(),
        "name": request.form.get("name", "").strip(),
        "customer_type": request.form.get("customer_type"),
        "phone": request.form.get("phone", "").strip(),
        "email": request.form.get("email", "").strip(),
        "city": request.form.get("city", "").strip(),
        "state": request.form.get("state"),
        "gstin": request.form.get("gstin", "").strip().upper(),
        "special_pricing": request.form.get("special_pricing", "").strip(),
        "address": request.form.get("address", "").strip(),
        "status": request.form.get("status", "Active"),
    }

    ok, msg = validate_customer_data(payload)
    if not ok:
        flash(msg, "error")
        return redirect(url_for("customers", tab="add"))

    add_customer(payload)
    flash(f"Customer {payload['customer_id']} registered successfully.", "success")
    return redirect(url_for("customers", tab="directory"))


@app.route("/suppliers")
def suppliers():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_SUPPLIERS):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    sups = get_suppliers()
    active_tab = request.args.get("tab", "directory")
    return render_template(
        "suppliers.html",
        current_page=PAGE_SUPPLIERS,
        active_tab=active_tab,
        suppliers=sups,
        can_edit=can_edit(session["user_role"]),
    )


@app.route("/supplier/add", methods=["POST"])
def add_supplier_post():
    if not can_edit(session.get("user_role")):
        flash("Unauthorized.", "error")
        return redirect(url_for("suppliers"))

    payload = {
        "supplier_id": request.form.get("supplier_id", "").strip().upper(),
        "name": request.form.get("name", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "email": request.form.get("email", "").strip(),
        "gstin": request.form.get("gstin", "").strip().upper(),
        "supplied_materials": request.form.get("supplied_materials", "").strip(),
        "address": request.form.get("address", "").strip(),
        "status": request.form.get("status", "Active"),
    }

    ok, msg = validate_supplier_data(payload)
    if not ok:
        flash(msg, "error")
        return redirect(url_for("suppliers", tab="add"))

    add_supplier(payload)
    flash(f"Supplier {payload['supplier_id']} registered successfully.", "success")
    return redirect(url_for("suppliers", tab="directory"))


@app.route("/raw-materials")
def raw_materials():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_RAW_MATERIALS):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    mats = get_raw_materials()
    active_tab = request.args.get("tab", "directory")
    return render_template(
        "raw_materials.html",
        current_page=PAGE_RAW_MATERIALS,
        active_tab=active_tab,
        materials=mats,
        categories=MATERIAL_CATEGORIES,
        units=MATERIAL_UNITS,
        can_edit=can_edit(session["user_role"]),
    )


@app.route("/raw-material/add", methods=["POST"])
def add_raw_material_post():
    if not can_edit(session.get("user_role")):
        flash("Unauthorized.", "error")
        return redirect(url_for("raw_materials"))

    payload = {
        "material_id": request.form.get("material_id", "").strip().upper(),
        "name": request.form.get("name", "").strip(),
        "category": request.form.get("category"),
        "unit": request.form.get("unit"),
        "purchase_rate": float(request.form.get("purchase_rate", 0.0)),
        "min_stock_level": float(request.form.get("min_stock_level", 0.0)),
        "stock_qty": 0.0,
        "description": request.form.get("description", "").strip(),
        "status": request.form.get("status", "Active"),
    }

    ok, msg = validate_raw_material_data(payload)
    if not ok:
        flash(msg, "error")
        return redirect(url_for("raw_materials", tab="add"))

    add_raw_material(payload)
    flash(f"Material {payload['material_id']} registered successfully.", "success")
    return redirect(url_for("raw_materials", tab="directory"))


@app.route("/raw-material/edit", methods=["POST"])
def edit_raw_material_post():
    if not can_edit(session.get("user_role")):
        flash("Unauthorized.", "error")
        return redirect(url_for("raw_materials"))

    material_id = request.form.get("material_id", "").strip()
    try:
        stock_qty = max(0.0, float(request.form.get("stock_qty", 0.0)))
        purchase_rate = max(0.0, float(request.form.get("purchase_rate", 0.0)))
        min_stock_level = max(0.0, float(request.form.get("min_stock_level", 0.0)))
    except ValueError:
        flash("Invalid stock or pricing value.", "error")
        return redirect(url_for("raw_materials"))

    existing = next((m for m in get_raw_materials() if m.get("material_id") == material_id), None)
    old_stock = float(existing.get("stock_qty", 0.0)) if existing else stock_qty
    if not update_raw_material(material_id, {
        "name": request.form.get("name", "").strip(),
        "category": request.form.get("category"),
        "unit": request.form.get("unit"),
        "purchase_rate": purchase_rate,
        "min_stock_level": min_stock_level,
        "stock_qty": stock_qty,
        "status": request.form.get("status", "Active"),
        "description": request.form.get("description", "").strip(),
    }):
        flash("Unable to update raw material.", "error")
    else:
        if old_stock != stock_qty:
            from database.firestore_operations import add_inventory_transaction
            add_inventory_transaction({
                "item_type": "RAW_MATERIAL",
                "item_id": material_id,
                "item_name": request.form.get("name", "").strip(),
                "movement_type": "STOCK_ADJUSTMENT",
                "change_qty": stock_qty - old_stock,
                "balance_qty": stock_qty,
                "reference_id": "MANUAL-ADJUSTMENT",
                "user_id": session.get("user_uid", "staff"),
            })
        flash(f"Material {material_id} updated successfully.", "success")
    return redirect(url_for("raw_materials", tab="directory"))


@app.route("/raw-material/inward", methods=["POST"])
def raw_material_inward_post():
    if not can_edit(session.get("user_role")):
        flash("Unauthorized.", "error")
        return redirect(url_for("inventory"))
    material_id = request.form.get("material_id", "").strip()
    try:
        quantity = float(request.form.get("quantity", 0.0))
    except ValueError:
        quantity = 0.0
    reference = request.form.get("reference", "").strip()
    notes = request.form.get("notes", "").strip()
    if quantity <= 0:
        flash("Inward quantity must be greater than zero.", "error")
        return redirect(url_for("inventory"))
    if add_raw_material_stock(material_id, quantity, reference or "MATERIAL-INWARD", session.get("user_uid", "staff"), notes):
        record_activity_log(session.get("user_uid", ""), session.get("user_role", ""), "RAW_MATERIAL_INWARD", "raw_material_inward_post", f"{material_id}:{quantity}")
        flash("Raw material stock received successfully.", "success")
    else:
        flash("Unable to record raw material inward.", "error")
    return redirect(url_for("inventory"))


@app.route("/production")
def production():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_PRODUCTION):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    orders = get_production_orders()
    search = request.args.get("search", "").strip().lower()
    status_filter = request.args.get("status", "All")
    filtered = orders
    if search:
        filtered = [o for o in filtered if search in o.get("production_id", "").lower() or search in o.get("product_name", "").lower()]
    if status_filter != "All":
        filtered = [o for o in filtered if o.get("status") == status_filter]

    active_tab = request.args.get("tab", "orders")
    view_id = request.args.get("view")
    selected = next((o for o in orders if o.get("production_id") == view_id), None)
    products = [p for p in get_products() if p.get("status") == "Active"]
    can_manage = can_edit(session["user_role"])
    approved_orders = [
        o for o in get_orders()
        if o.get("status") in ["Approved", "Invoiced", "Dispatched"]
    ] if session["user_role"] in [ROLE_SUPERVISOR, ROLE_OWNER, ROLE_ADMIN] else []

    requirements = None
    if selected:
        bom_exists, material_requirements, _, _ = calculate_bom_requirements(
            selected.get("product_id"),
            float(selected.get("planned_quantity", selected.get("quantity", 0))),
        )
        if bom_exists:
            requirements = [{
                "material_name": item["material_name"],
                "required_quantity": item["total_required"],
                "available_quantity": item["available_stock"],
                "unit": item["unit"],
                "available": item["sufficient"],
                "shortage": item["shortage"],
            } for item in material_requirements]

    return render_template(
        "production.html",
        current_page=PAGE_PRODUCTION,
        active_tab=active_tab,
        orders=filtered,
        selected=selected,
        requirements=requirements,
        products=products,
        statuses=["All", "Pending", "In Progress", "Completed", "Cancelled"],
        search=search,
        status_filter=status_filter,
        can_manage=can_manage,
        approved_orders=approved_orders,
    )


@app.route("/production/create", methods=["POST"])
def create_production_post():
    if not can_edit(session.get("user_role")):
        flash("Unauthorized.", "error")
        return redirect(url_for("production"))

    product_id = request.form.get("product_id", "").strip()
    product = next((p for p in get_products() if p.get("product_id") == product_id), None)
    if not product:
        flash("Invalid finished product.", "error")
        return redirect(url_for("production", tab="create"))
    try:
        quantity = float(request.form.get("quantity", 0))
    except ValueError:
        quantity = 0
    if quantity <= 0:
        flash("Production quantity must be greater than zero.", "error")
        return redirect(url_for("production", tab="create"))

    bom_exists, requirements, all_available, _ = calculate_bom_requirements(product_id, quantity)
    if not bom_exists:
        flash("Create a Bill of Materials for this product before production.", "error")
        return redirect(url_for("bom", tab="create"))
    if not all_available:
        flash("Insufficient raw materials for the requested production quantity.", "error")
        return redirect(url_for("production", tab="create"))

    payload = {
        "product_id": product_id,
        "product_name": product.get("name", ""),
        "planned_quantity": quantity,
        "start_date": request.form.get("start_date", "").strip(),
        "expected_completion_date": request.form.get("expected_completion_date", "").strip(),
        "status": "Pending",
        "progress_percent": 0,
        "notes": request.form.get("notes", "").strip(),
        "created_by": session.get("user_uid", "staff"),
    }
    if create_production_order(payload):
        record_activity_log(session.get("user_uid", ""), session.get("user_role", ""), "PRODUCTION_CREATED", "create_production_post", payload.get("production_id", "") or "")
        flash("Production order created successfully.", "success")
    else:
        flash("Unable to create production order.", "error")
    return redirect(url_for("production"))


@app.route("/production/status", methods=["POST"])
def production_status_post():
    if not can_edit(session.get("user_role")):
        flash("Unauthorized.", "error")
        return redirect(url_for("production"))
    production_id = request.form.get("production_id", "")
    status_value = request.form.get("status", "")
    try:
        progress = min(100, max(0, int(request.form.get("progress_percent", 0))))
    except ValueError:
        progress = 0
    if status_value not in ["Pending", "In Progress", "Completed", "Cancelled"]:
        flash("Invalid production status.", "error")
        return redirect(url_for("production"))
    if status_value == "Completed":
        order = next((o for o in get_production_orders() if o.get("production_id") == production_id), None)
        try:
            actual_quantity = float(request.form.get("actual_quantity", order.get("planned_quantity", 0) if order else 0))
        except (TypeError, ValueError):
            actual_quantity = float(order.get("planned_quantity", 0)) if order else 0
        try:
            wastage_quantity = max(0.0, float(request.form.get("wastage_quantity", 0)))
        except (TypeError, ValueError):
            wastage_quantity = 0.0
        ok, msg = complete_production(
            production_id,
            actual_quantity,
            session.get("user_uid", "staff"),
            wastage_quantity,
        )
        record_activity_log(session.get("user_uid", ""), session.get("user_role", ""), "PRODUCTION_COMPLETED" if ok else "PRODUCTION_COMPLETION_FAILED", "production_status_post", production_id)
        flash(msg, "success" if ok else "error")
    elif update_production_order(production_id, {"status": status_value, "progress_percent": progress}):
        flash("Production progress updated.", "success")
    else:
        flash("Unable to update production order.", "error")
    return redirect(url_for("production"))


@app.route("/production/delete", methods=["POST"])
def delete_production_post():
    if not can_edit(session.get("user_role")):
        flash("Unauthorized.", "error")
        return redirect(url_for("production"))
    production_id = request.form.get("production_id", "")
    order = next((o for o in get_production_orders() if o.get("production_id") == production_id), None)
    if order and order.get("status") == "Completed":
        flash("Completed production records cannot be deleted.", "error")
    elif delete_production_order(production_id):
        flash("Production record deleted.", "success")
    else:
        flash("Unable to delete production record.", "error")
    return redirect(url_for("production"))


@app.route("/production/edit", methods=["POST"])
def edit_production_post():
    if not can_edit(session.get("user_role")):
        flash("Unauthorized.", "error")
        return redirect(url_for("production"))
    production_id = request.form.get("production_id", "")
    order = next((o for o in get_production_orders() if o.get("production_id") == production_id), None)
    if not order:
        flash("Production order not found.", "error")
    elif order.get("status") == "Completed":
        flash("Completed production records cannot be edited.", "error")
    else:
        try:
            planned_quantity = float(request.form.get("planned_quantity", 0))
        except ValueError:
            planned_quantity = 0
        if planned_quantity <= 0:
            flash("Planned quantity must be greater than zero.", "error")
        else:
            bom_exists, _, all_available, _ = calculate_bom_requirements(order.get("product_id"), planned_quantity)
            if not bom_exists:
                flash("No Bill of Materials configured for this product.", "error")
            elif not all_available:
                flash("Insufficient raw materials for the revised quantity.", "error")
            elif update_production_order(production_id, {
                "planned_quantity": planned_quantity,
                "start_date": request.form.get("start_date", ""),
                "expected_completion_date": request.form.get("expected_completion_date", ""),
                "notes": request.form.get("notes", "").strip(),
            }):
                flash("Production order updated.", "success")
            else:
                flash("Unable to update production order.", "error")
    return redirect(url_for("production", view=production_id))


@app.route("/bom")
def bom():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_BOM):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    boms = get_boms()
    product_id = request.args.get("product_id")
    selected = get_bom_for_product(product_id) if product_id else (boms[0] if boms else None)
    return render_template(
        "bom.html",
        current_page=PAGE_BOM,
        active_tab=request.args.get("tab", "directory"),
        boms=boms,
        selected=selected,
        products=[p for p in get_products() if p.get("status") == "Active"],
        materials=[m for m in get_raw_materials() if m.get("status") == "Active"],
        can_manage=can_edit(session["user_role"]),
    )


@app.route("/bom/save", methods=["POST"])
def save_bom_post():
    if not can_edit(session.get("user_role")):
        flash("Unauthorized.", "error")
        return redirect(url_for("bom"))
    product_id = request.form.get("product_id", "").strip()
    product = next((p for p in get_products() if p.get("product_id") == product_id), None)
    if not product:
        flash("Invalid finished product.", "error")
        return redirect(url_for("bom"))

    material_ids = request.form.getlist("material_id")
    quantities = request.form.getlist("quantity_per_unit")
    items = []
    materials_by_id = {material["material_id"]: material for material in get_raw_materials()}
    for material_id, quantity in zip(material_ids, quantities):
        try:
            qty = float(quantity)
        except ValueError:
            qty = 0
        material = materials_by_id.get(material_id)
        if material and qty > 0:
            items.append({
                "material_id": material_id,
                "material_name": material.get("name", ""),
                "required_per_unit": qty,
                "unit": material.get("unit", "Unit"),
            })

    if items and save_bom({
        "product_id": product_id,
        "product_name": product.get("name", ""),
        "output_unit": f"Packet ({product.get('pack_size', '')})",
        "output_quantity": 1,
        "materials": items,
    }):
        flash("Bill of Materials saved successfully.", "success")
    else:
        flash("Add at least one valid raw material and quantity.", "error")
    return redirect(url_for("bom", product_id=product_id))


@app.route("/inventory")
def inventory():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_INVENTORY):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    search = request.args.get("search", "").strip().lower()
    stock_filter = request.args.get("stock", "All")
    materials = get_raw_materials()
    products = get_products()

    raw_rows = []
    for material in materials:
        stock = float(material.get("stock_qty", 0.0))
        minimum = float(material.get("min_stock_level", 0.0))
        row = dict(material)
        row["stock_qty"] = stock
        row["low_stock"] = stock <= minimum
        raw_rows.append(row)
    if search:
        raw_rows = [m for m in raw_rows if search in m.get("name", "").lower() or search in m.get("material_id", "").lower()]
        products = [p for p in products if search in p.get("name", "").lower() or search in p.get("product_id", "").lower()]
    if stock_filter == "Low":
        raw_rows = [m for m in raw_rows if m["low_stock"]]
    elif stock_filter == "Available":
        raw_rows = [m for m in raw_rows if m["stock_qty"] > 0]

    transactions = get_inventory_transactions()
    return render_template(
        "inventory.html",
        current_page=PAGE_INVENTORY,
        materials=raw_rows,
        products=products,
        transactions=transactions,
        search=search,
        stock_filter=stock_filter,
        can_manage=can_edit(session["user_role"]),
    )


@app.route("/reports")
def reports():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_REPORTS):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    role = session["user_role"]
    orders = get_orders()
    invoices = get_invoices()
    payments = get_payments()
    production_orders = get_production_orders()
    materials = get_raw_materials()
    products = get_products()

    if role == ROLE_SALESMAN:
        uid = session.get("user_uid")
        orders = [o for o in orders if o.get("salesman_id") == uid]
        invoices = [i for i in invoices if i.get("salesman_id") == uid]
        production_orders = []
        materials = []
        products = [p for p in products if p.get("status") == "Active"]
    elif role == ROLE_SUPERVISOR:
        orders = [o for o in orders if o.get("status") in ["Approved", "Invoiced", "Dispatched"]]
        invoices = []
        payments = []

    low_stock = [
        m for m in materials
        if float(m.get("stock_qty", 0.0)) <= float(m.get("min_stock_level", 0.0))
    ]
    return render_template(
        "reports.html",
        current_page=PAGE_REPORTS,
        role=role,
        orders=orders,
        invoices=invoices,
        payments=payments,
        production_orders=production_orders,
        materials=materials,
        low_stock=low_stock,
        products=products,
        transactions=get_inventory_transactions(),
        activity_logs=get_activity_logs() if role in [ROLE_OWNER, ROLE_AUDITOR] else [],
    )


def _financial_report_data(start_date="", end_date="", customer_name="", production_product_id="", production_id=""):
    return build_financial_reports(
        invoices=get_invoices(),
        payments=get_payments(),
        production_orders=get_production_orders(),
        materials=get_raw_materials(),
        products=get_products(),
        inventory_transactions=get_inventory_transactions(),
        expenses=get_production_expenses(),
        purchase_invoices=get_purchase_invoices(),
        start_date=start_date or None,
        end_date=end_date or None,
        customer_name=customer_name or None,
        production_product_id=production_product_id or None,
        production_id=production_id or None,
    )


@app.route("/financials")
def financials():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_FINANCIALS):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    customer_name = request.args.get("customer", "").strip()
    production_product_id = request.args.get("product_id", "").strip()
    production_id = request.args.get("production_id", "").strip()
    try:
        reports_data = _financial_report_data(
            start_date, end_date, customer_name, production_product_id, production_id
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("financials"))
    return render_template(
        "financials.html",
        current_page=PAGE_FINANCIALS,
        reports_data=reports_data,
        monthly_chart={
            "labels": list(reports_data["monthly"]),
            "revenue": [float(value["revenue"]) for value in reports_data["monthly"].values()],
            "expenses": [float(value["expenses"]) for value in reports_data["monthly"].values()],
            "gross_profit": [float(value["gross_profit"]) for value in reports_data["monthly"].values()],
        },
        report_titles={key: value[0] for key, value in REPORTS.items()},
        start_date=start_date,
        end_date=end_date,
        production_orders=get_production_orders(),
        products=get_products(),
        materials=get_raw_materials(),
        customers=get_customers(),
        selected_customer=customer_name,
        selected_product=production_product_id,
        selected_production=production_id,
        can_record_expenses=session["user_role"] in [ROLE_OWNER, ROLE_ADMIN],
    )


@app.route("/financials/expense", methods=["POST"])
def financial_expense_post():
    if session.get("user_role") not in [ROLE_OWNER, ROLE_ADMIN]:
        flash("Unauthorized action.", "error")
        return redirect(url_for("financials"))

    production_id = request.form.get("production_id", "").strip()
    order = next(
        (item for item in get_production_orders() if item.get("production_id") == production_id),
        None,
    )
    if not order:
        flash("Select a valid production batch.", "error")
        return redirect(url_for("financials"))
    try:
        costs = {
            "labour_cost": Decimal(request.form.get("labour_cost", "0")),
            "utilities_cost": Decimal(request.form.get("utilities_cost", "0")),
            "maintenance_cost": Decimal(request.form.get("maintenance_cost", "0")),
            "other_cost": Decimal(request.form.get("other_cost", "0")),
        }
    except (InvalidOperation, TypeError, ValueError):
        flash("Enter valid production expense amounts.", "error")
        return redirect(url_for("financials"))
    if any(not value.is_finite() or value < 0 for value in costs.values()):
        flash("Production expenses must be finite non-negative amounts.", "error")
        return redirect(url_for("financials"))
    expense_date = request.form.get("expense_date", "").strip()
    try:
        datetime.strptime(expense_date, "%Y-%m-%d")
    except ValueError:
        flash("Enter a valid expense date.", "error")
        return redirect(url_for("financials"))
    payload = {
        "production_id": production_id,
        "expense_date": expense_date,
        **{key: float(value) for key, value in costs.items()},
        "notes": request.form.get("notes", "").strip(),
        "created_by": session.get("user_uid", ""),
    }
    if not record_production_expense(payload):
        flash("Production expense could not be saved.", "error")
        return redirect(url_for("financials"))
    record_activity_log(
        session.get("user_uid", ""),
        session.get("user_role", ""),
        "PRODUCTION_EXPENSE_RECORDED",
        "financial_expense_post",
        production_id,
    )
    flash("Production expense recorded in the audit history.", "success")
    return redirect(url_for("financials"))


@app.route("/financials/purchase", methods=["POST"])
def financial_purchase_post():
    """Record a supplier invoice before its linked receipt is exposed in reports."""
    if session.get("user_role") not in [ROLE_OWNER, ROLE_ADMIN]:
        flash("Unauthorized action.", "error")
        return redirect(url_for("financials"))
    invoice_number = request.form.get("purchase_invoice_number", "").strip()
    material_id = request.form.get("material_id", "").strip()
    material = next((item for item in get_raw_materials() if item.get("material_id") == material_id), None)
    try:
        quantity = Decimal(request.form.get("quantity", "0"))
        unit_price = Decimal(request.form.get("unit_price", "0"))
        gst_rate = Decimal(request.form.get("gst_rate", "0"))
        amount_paid = Decimal(request.form.get("amount_paid", "0"))
        purchase_date = request.form.get("purchase_date", "").strip()
        datetime.strptime(purchase_date, "%Y-%m-%d")
    except (InvalidOperation, TypeError, ValueError):
        flash("Enter valid purchase date and financial values.", "error")
        return redirect(url_for("financials"))
    if not invoice_number or not material or quantity <= 0 or unit_price < 0 or gst_rate < 0 or amount_paid < 0:
        flash("Invoice, material, and non-negative purchase values are required.", "error")
        return redirect(url_for("financials"))
    taxable = quantity * unit_price
    cgst = sgst = igst = Decimal("0")
    if request.form.get("tax_type") == "interstate":
        igst = taxable * gst_rate / Decimal("100")
    else:
        cgst = sgst = taxable * gst_rate / Decimal("200")
    total = taxable + cgst + sgst + igst
    if amount_paid > total:
        flash("Amount paid cannot exceed the purchase invoice total.", "error")
        return redirect(url_for("financials"))
    purchase = {
        "purchase_invoice_number": invoice_number, "purchase_date": purchase_date,
        "supplier_name": request.form.get("supplier_name", "").strip() or "Not recorded",
        "material_id": material_id, "material_name": material.get("name", ""),
        "quantity": float(quantity), "unit_price": float(unit_price), "taxable_value": float(taxable),
        "gst_rate": float(gst_rate), "cgst": float(cgst), "sgst": float(sgst), "igst": float(igst),
        "total_amount": float(total), "amount_paid": float(amount_paid),
        "itc_eligible": request.form.get("itc_eligible") == "on", "created_by": session.get("user_uid", ""),
    }
    if not create_purchase_invoice(purchase):
        flash("Purchase invoice already exists or could not be saved; stock was not changed.", "error")
        return redirect(url_for("financials"))
    if not add_raw_material_stock(material_id, float(quantity), invoice_number, session.get("user_uid", "staff"), "Supplier purchase invoice"):
        flash("Purchase invoice was saved but stock receipt needs reconciliation.", "error")
        return redirect(url_for("financials"))
    record_activity_log(session.get("user_uid", ""), session.get("user_role", ""), "PURCHASE_INVOICE_RECORDED", "financial_purchase_post", invoice_number)
    flash("Purchase invoice and stock receipt recorded.", "success")
    return redirect(url_for("financials"))


@app.route("/financials/export/<report_type>")
def financial_export(report_type):
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_FINANCIALS):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))
    if report_type not in REPORTS:
        flash("Unknown financial report.", "error")
        return redirect(url_for("financials"))

    export_format = request.args.get("format", "csv").lower()
    if export_format not in {"csv", "xlsx", "pdf"}:
        flash("Choose CSV, Excel, or PDF export.", "error")
        return redirect(url_for("financials"))
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    customer_name = request.args.get("customer", "").strip()
    production_product_id = request.args.get("product_id", "").strip()
    production_id = request.args.get("production_id", "").strip()
    try:
        data = _financial_report_data(
            start_date, end_date, customer_name, production_product_id, production_id
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("financials"))

    rows = data[report_type]
    if export_format == "csv":
        content = render_csv(report_type, rows)
        mimetype, extension = "text/csv; charset=utf-8", "csv"
    elif export_format == "xlsx":
        content = render_xlsx(report_type, rows, data["summaries"])
        mimetype, extension = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    else:
        content = render_pdf(report_type, rows, data["summaries"], data["date_range"])
        mimetype, extension = "application/pdf", "pdf"
    return send_file(
        io.BytesIO(content),
        mimetype=mimetype,
        as_attachment=True,
        download_name=f"bline-{report_type}.{extension}",
    )


@app.route("/users")
def users():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    if not check_page_permission(session["user_role"], PAGE_USERS):
        flash("Unauthorized page access.", "error")
        return redirect(url_for("index"))

    active_tab = request.args.get("tab", "roster")
    users_list = [
        {"email": email, "name": val["name"], "role": val["role"], "uid": val["uid"], "status": "Active"}
        for email, val in DEMO_USERS.items()
    ]
    known_emails = {u["email"].lower() for u in users_list}
    users_list.extend(u for u in get_users() if u.get("email", "").lower() not in known_emails)

    return render_template(
        "users.html",
        current_page=PAGE_USERS,
        active_tab=active_tab,
        users_list=users_list,
        all_roles=ALL_ROLES,
    )


@app.route("/user/create", methods=["POST"])
def create_user_post():
    return _create_user_from_request("users")


def _create_user_from_request(origin: str):
    if session.get("user_role") not in [ROLE_OWNER, ROLE_ADMIN]:
        flash("Unauthorized.", "error")
        return redirect(url_for("login", tab="account") if origin == "account" else url_for("users"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    role = request.form.get("role")
    status = request.form.get("status", "Active")

    if not name or not validate_email(email):
        flash("Full name and valid enterprise email are required.", "error")
        return redirect(url_for("login", tab="account") if origin == "account" else url_for("users", tab="create"))
    if role not in ALL_ROLES:
        flash("Select a valid employee role.", "error")
        return redirect(url_for("login", tab="account") if origin == "account" else url_for("users", tab="create"))
    if email in DEMO_USERS or any(u.get("email", "").lower() == email for u in get_users()):
        flash("An account with that email address already exists.", "error")
        return redirect(url_for("login", tab="account") if origin == "account" else url_for("users", tab="create"))

    new_uid = f"usr_{uuid.uuid4().hex[:12]}"
    auth_ok, auth_uid_or_error = create_employee_auth(email, "Password123!", name)
    if not auth_ok:
        flash(auth_uid_or_error, "error")
        return redirect(url_for("login", tab="account") if origin == "account" else url_for("users", tab="create"))
    if auth_uid_or_error:
        new_uid = auth_uid_or_error
    DEMO_USERS[email] = {
        "password": "Password123!",
        "name": name,
        "role": role,
        "uid": new_uid,
    }
    if not add_user({"uid": new_uid, "name": name, "email": email, "phone": phone, "role": role, "status": status}):
        DEMO_USERS.pop(email, None)
        flash("Unable to save the employee profile. No account was created.", "error")
        return redirect(url_for("login", tab="account") if origin == "account" else url_for("users", tab="create"))
    invitation_ok, invitation_message = reset_password_firebase(email)
    if invitation_ok:
        flash(f"Account created for {name}; a password setup invitation was sent to {email}.", "success")
    else:
        flash(f"Account created for {name}, but the password setup invitation could not be sent: {invitation_message}", "warning")
    return redirect(url_for("login", tab="account") if origin == "account" else url_for("users", tab="roster"))


@app.route("/user/role", methods=["POST"])
def update_user_role_post():
    if session.get("user_role") not in [ROLE_OWNER, ROLE_ADMIN]:
        flash("Unauthorized: only administrators can change roles.", "error")
        return redirect(url_for("users"))
    email = request.form.get("email", "").strip().lower()
    role = request.form.get("role", "")
    if role not in ALL_ROLES:
        flash("Invalid system role.", "error")
        return redirect(url_for("users"))
    if email in DEMO_USERS:
        DEMO_USERS[email]["role"] = role
    else:
        user = next((u for u in get_users() if u.get("email", "").lower() == email), None)
        if not user or not update_user(user["uid"], {"role": role}):
            flash("User account not found.", "error")
            return redirect(url_for("users"))
    record_activity_log(
        session.get("user_uid", ""),
        session.get("user_role", ""),
        "ROLE_UPDATED",
        "update_user_role_post",
        f"{email} assigned role {role}",
    )
    flash(f"Role for {email} updated to {role}.", "success")
    return redirect(url_for("users", tab="roster"))


# ----------------------------------------------------
# SETTINGS, TERMS & PRIVACY
# ----------------------------------------------------
@app.route("/settings")
def settings():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    db, mode = initialize_firebase()
    creds = get_firebase_credentials()
    web_api_key = get_firebase_web_api_key()

    return render_template(
        "settings.html",
        current_page=PAGE_SETTINGS,
        mode=mode,
        creds=creds,
        web_api_key=web_api_key,
        database_status=DATABASE_STATUS,
    )


@app.route("/terms")
def terms():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return render_template("terms.html", current_page=PAGE_TERMS)


@app.route("/privacy")
def privacy():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return redirect(url_for("terms"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
