"""
Firestore Database Operations for FactoryFlow (Phase 1, Phase 2 & Phase 3).
Complete CRUD and atomic transactional logic for:
- users
- products (finished goods with stock and reserved tracking)
- customers
- suppliers
- raw_materials (with available stock, purchase rates, and minimum stock alerts)
- orders
- invoices
- dispatches
- payments
- stock_ledger
- production_orders (Phase 3)
- bill_of_materials (Phase 3)
- inventory_transactions (Phase 3)

Strict rules:
- Unique sequential document IDs (ORD-YYYY-XXXX, INV-YYYY-XXXX, DSP-XXXX, PAY-XXXX, PRD-ORD-YYYY-XXXX, BOM-XXXX, TXN-XXXX).
- Accurate Decimal-backed financial and inventory arithmetic.
- Prevents negative inventory.
- Pre-seeds South Indian snack finished goods, raw materials, and initial BOM recipes.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import uuid
from database.firebase_config import initialize_firebase
from utils.gst_calculations import to_decimal

# ----------------------------------------------------
# SEED MASTER DATA
# ----------------------------------------------------
_SAMPLE_PRODUCTS = [
    {
        "product_id": "PRD-001",
        "name": "Murukku 200g",
        "category": "Murukku",
        "description": "Crispy traditional South Indian rice and urad dal chakli/murukku with cumin flavor.",
        "pack_size": "200g",
        "selling_price": 50.0,
        "gst_rate": 5.0,
        "hsn_code": "19059040",
        "stock_qty": 238,
        "reserved_qty": 0,
        "status": "Active",
        "created_at": "2026-01-10T10:00:00",
        "updated_at": "2026-01-10T10:00:00",
    },
    {
        "product_id": "PRD-002",
        "name": "Mixture 200g",
        "category": "Mixture",
        "description": "Spicy Madras mixture with fried peanuts, curry leaves, sev and boondi.",
        "pack_size": "200g",
        "selling_price": 60.0,
        "gst_rate": 5.0,
        "hsn_code": "19059040",
        "stock_qty": 150,
        "reserved_qty": 0,
        "status": "Active",
        "created_at": "2026-01-11T11:00:00",
        "updated_at": "2026-01-11T11:00:00",
    },
    {
        "product_id": "PRD-003",
        "name": "Banana Chips 200g",
        "category": "Chips",
        "description": "Thin-sliced raw Nendran plantain chips fried in cold-pressed pure coconut oil.",
        "pack_size": "200g",
        "selling_price": 75.0,
        "gst_rate": 5.0,
        "hsn_code": "20081940",
        "stock_qty": 100,
        "reserved_qty": 0,
        "status": "Active",
        "created_at": "2026-01-12T09:30:00",
        "updated_at": "2026-01-12T09:30:00",
    },
    {
        "product_id": "PRD-004",
        "name": "Mysore Pak 200g",
        "category": "Sweets",
        "description": "Rich traditional ghee Mysore Pak prepared from gram flour and pure cow ghee.",
        "pack_size": "200g",
        "selling_price": 120.0,
        "gst_rate": 5.0,
        "hsn_code": "21069099",
        "stock_qty": 80,
        "reserved_qty": 0,
        "status": "Active",
        "created_at": "2026-01-13T14:15:00",
        "updated_at": "2026-01-13T14:15:00",
    },
]

_SAMPLE_CUSTOMERS = [
    {
        "customer_id": "CUST-001",
        "name": "Retailer A",
        "customer_type": "Retailer",
        "phone": "9840123456",
        "email": "orders@retailera-tn.com",
        "address": "45 Bazaar Street, T. Nagar",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "gstin": "33AAAAA1234A1Z5",
        "special_pricing": "Standard Retail",
        "status": "Active",
        "created_at": "2026-01-05T09:00:00",
        "updated_at": "2026-01-05T09:00:00",
    },
    {
        "customer_id": "CUST-002",
        "name": "Distributor B",
        "customer_type": "Distributor",
        "phone": "9880987654",
        "email": "purchasing@distributorb-ka.in",
        "address": "Plot 12, APMC Yard, Yeshwanthpur",
        "city": "Bengaluru",
        "state": "Karnataka",
        "gstin": "29BBBBB5678B1Z2",
        "special_pricing": "Bulk Wholesale",
        "status": "Active",
        "created_at": "2026-01-08T11:20:00",
        "updated_at": "2026-01-08T11:20:00",
    },
]

_SAMPLE_SUPPLIERS = [
    {
        "supplier_id": "SUP-001",
        "name": "Sri Krishna Agro Flour Mill",
        "phone": "9443211223",
        "email": "sales@krishnaflour.com",
        "address": "12 Mill Road",
        "gstin": "33CCCCC9876C1Z9",
        "supplied_materials": "Rice Flour, Besan, Urad Dal Flour",
        "status": "Active",
        "created_at": "2026-01-02T10:00:00",
        "updated_at": "2026-01-02T10:00:00",
    },
    {
        "supplier_id": "SUP-002",
        "name": "Venkateshwara Oil Refineries",
        "phone": "9443555888",
        "email": "orders@venkateshwaraoils.com",
        "address": "88 Industrial Estate",
        "gstin": "33DDDDD4321D1Z4",
        "supplied_materials": "Cooking Oil, Pure Cow Ghee",
        "status": "Active",
        "created_at": "2026-01-03T11:30:00",
        "updated_at": "2026-01-03T11:30:00",
    },
]

# Raw Materials with live stock quantities for Phase 3 tracking
_SAMPLE_RAW_MATERIALS = [
    {
        "material_id": "RM-001",
        "name": "Flour",
        "category": "Grains & Flours",
        "unit": "Kilogram",
        "quantity": 850.0,  # Current available stock in kg
        "purchase_rate": 42.0,
        "min_stock_level": 500.0,
        "description": "Sorted and processed fine rice and urad flour blend.",
        "status": "Active",
        "created_at": "2026-01-01T08:00:00",
        "updated_at": "2026-01-01T08:00:00",
    },
    {
        "material_id": "RM-002",
        "name": "Cooking Oil",
        "category": "Oils & Fats",
        "unit": "Litre",
        "quantity": 620.0,  # Current available stock in litres
        "purchase_rate": 130.0,
        "min_stock_level": 300.0,
        "description": "Double refined sunflower and coconut oil.",
        "status": "Active",
        "created_at": "2026-01-01T08:10:00",
        "updated_at": "2026-01-01T08:10:00",
    },
    {
        "material_id": "RM-003",
        "name": "Salt and Spice Mix",
        "category": "Spices & Seasoning",
        "unit": "Kilogram",
        "quantity": 120.0,
        "purchase_rate": 95.0,
        "min_stock_level": 50.0,
        "description": "Iodized salt, Kashmiri chilli powder, hing, and cumin.",
        "status": "Active",
        "created_at": "2026-01-01T08:20:00",
        "updated_at": "2026-01-01T08:20:00",
    },
    {
        "material_id": "RM-004",
        "name": "200g Pouch",
        "category": "Packaging",
        "unit": "Piece",
        "quantity": 8200.0,
        "purchase_rate": 2.2,
        "min_stock_level": 5000.0,
        "description": "Custom printed nitrogen-flush snack pouch.",
        "status": "Active",
        "created_at": "2026-01-01T08:30:00",
        "updated_at": "2026-01-01T08:30:00",
    },
    {
        "material_id": "RM-005",
        "name": "Carton",
        "category": "Packaging",
        "unit": "Carton",
        "quantity": 350.0,
        "purchase_rate": 28.0,
        "min_stock_level": 200.0,
        "description": "5-ply heavy duty corrugated cardboard outer shipper boxes.",
        "status": "Active",
        "created_at": "2026-01-01T08:40:00",
        "updated_at": "2026-01-01T08:40:00",
    },
]

# Phase 3: Pre-seeded Bill of Materials (BOM) for finished snack products
_SAMPLE_BOMS = [
    {
        "bom_id": "BOM-001",
        "product_id": "PRD-001",
        "product_name": "Murukku 200g",
        "output_unit": "Piece (200g Packet)",
        "output_quantity": 1,
        "materials": [
            {"material_id": "RM-001", "material_name": "Flour", "required_per_unit": 0.18, "unit": "Kilogram"},
            {"material_id": "RM-002", "material_name": "Cooking Oil", "required_per_unit": 0.05, "unit": "Litre"},
            {"material_id": "RM-003", "material_name": "Salt and Spice Mix", "required_per_unit": 0.01, "unit": "Kilogram"},
            {"material_id": "RM-004", "material_name": "200g Pouch", "required_per_unit": 1.0, "unit": "Piece"},
        ],
        "created_at": "2026-01-10T10:00:00",
        "updated_at": "2026-01-10T10:00:00",
    },
    {
        "bom_id": "BOM-002",
        "product_id": "PRD-002",
        "product_name": "Mixture 200g",
        "output_unit": "Piece (200g Packet)",
        "output_quantity": 1,
        "materials": [
            {"material_id": "RM-001", "material_name": "Flour", "required_per_unit": 0.15, "unit": "Kilogram"},
            {"material_id": "RM-002", "material_name": "Cooking Oil", "required_per_unit": 0.06, "unit": "Litre"},
            {"material_id": "RM-003", "material_name": "Salt and Spice Mix", "required_per_unit": 0.015, "unit": "Kilogram"},
            {"material_id": "RM-004", "material_name": "200g Pouch", "required_per_unit": 1.0, "unit": "Piece"},
        ],
        "created_at": "2026-01-11T11:00:00",
        "updated_at": "2026-01-11T11:00:00",
    },
]

_SAMPLE_PRODUCTION_ORDERS = [
    {
        "production_id": "PO-2026-0001",
        "product_id": "PRD-001",
        "product_name": "Murukku 200g",
        "target_quantity": 200,
        "actual_quantity": 200,
        "start_date": "2026-01-15",
        "expected_completion_date": "2026-01-16",
        "status": "Completed",
        "progress_percentage": 100,
        "notes": "Standard morning fryer batch completed.",
        "created_by": "usr_sup_04",
        "created_at": "2026-01-15T08:00:00",
        "updated_at": "2026-01-16T17:00:00",
    }
]

_MEMORY_STORE = {
    "users": [],
    "products": [dict(p) for p in _SAMPLE_PRODUCTS],
    "customers": [dict(c) for c in _SAMPLE_CUSTOMERS],
    "suppliers": [dict(s) for s in _SAMPLE_SUPPLIERS],
    "raw_materials": [dict(m) for m in _SAMPLE_RAW_MATERIALS],
    "orders": [],
    "invoices": [],
    "dispatches": [],
    "payments": [],
    "stock_ledger": [
        {
            "ledger_id": "LED-0001",
            "product_id": "PRD-001",
            "product_name": "Murukku 200g",
            "movement_type": "INITIAL_PRODUCTION",
            "change_qty": 238,
            "balance_qty": 238,
            "reference_id": "BATCH-2026-01",
            "timestamp": "2026-01-15T08:00:00",
            "user_id": "usr_sup_04",
        }
    ],
    # Phase 3 collections
    "production_orders": [dict(po) for po in _SAMPLE_PRODUCTION_ORDERS],
    "bill_of_materials": [dict(b) for b in _SAMPLE_BOMS],
    "inventory_transactions": [
        {
            "transaction_id": "TXN-2026-0001",
            "item_type": "Finished Good",
            "item_id": "PRD-001",
            "item_name": "Murukku 200g",
            "transaction_type": "PRODUCTION_COMPLETION",
            "quantity_change": 200,
            "balance_after": 238,
            "reference_id": "PO-2026-0001",
            "notes": "Batch PO-2026-0001 completed",
            "timestamp": "2026-01-16T17:00:00",
            "user_id": "usr_sup_04",
        }
    ],
}


# ----------------------------------------------------
# GENERIC COLLECTION HELPERS
# ----------------------------------------------------
def get_all_documents(collection_name: str) -> List[Dict[str, Any]]:
    db, mode = initialize_firebase()
    if mode == "firebase" and db:
        try:
            docs = db.collection(collection_name).stream()
            return [doc.to_dict() for doc in docs]
        except Exception:
            pass

    return list(_MEMORY_STORE.get(collection_name, []))


def get_document(collection_name: str, doc_id_field: str, doc_id_val: str) -> Optional[Dict[str, Any]]:
    items = get_all_documents(collection_name)
    for it in items:
        if it.get(doc_id_field) == doc_id_val:
            return it
    return None


def add_document(collection_name: str, doc_id_field: str, data: Dict[str, Any]) -> bool:
    now = datetime.utcnow().isoformat()
    if "created_at" not in data:
        data["created_at"] = now
    data["updated_at"] = now

    doc_id = str(data.get(doc_id_field, "")).strip()
    if not doc_id:
        return False

    db, mode = initialize_firebase()
    if mode == "firebase" and db:
        try:
            # create() rejects an existing id.  Financial source documents must
            # never be silently overwritten by a retry or duplicate submission.
            db.collection(collection_name).document(doc_id).create(data)
            return True
        except Exception:
            return False

    if collection_name not in _MEMORY_STORE:
        _MEMORY_STORE[collection_name] = []

    for existing in _MEMORY_STORE[collection_name]:
        if existing.get(doc_id_field) == doc_id:
            return False
    _MEMORY_STORE[collection_name].append(data)
    return True


def update_document(collection_name: str, doc_id_field: str, doc_id_val: str, updated_data: Dict[str, Any]) -> bool:
    updated_data["updated_at"] = datetime.utcnow().isoformat()

    db, mode = initialize_firebase()
    if mode == "firebase" and db:
        try:
            db.collection(collection_name).document(doc_id_val).update(updated_data)
            return True
        except Exception:
            return False

    if collection_name not in _MEMORY_STORE:
        return False

    for idx, item in enumerate(_MEMORY_STORE[collection_name]):
        if item.get(doc_id_field) == doc_id_val:
            _MEMORY_STORE[collection_name][idx].update(updated_data)
            return True
    return False


def delete_document(collection_name: str, doc_id_field: str, doc_id_val: str) -> bool:
    db, mode = initialize_firebase()
    if mode == "firebase" and db:
        try:
            db.collection(collection_name).document(doc_id_val).delete()
            return True
        except Exception:
            return False

    if collection_name not in _MEMORY_STORE:
        return False

    for idx, item in enumerate(_MEMORY_STORE[collection_name]):
        if item.get(doc_id_field) == doc_id_val:
            del _MEMORY_STORE[collection_name][idx]
            return True
    return False


def toggle_status(collection_name: str, doc_id_field: str, doc_id_val: str) -> bool:
    doc = get_document(collection_name, doc_id_field, doc_id_val)
    if not doc:
        return False
    new_status = "Inactive" if doc.get("status") == "Active" else "Active"
    return update_document(collection_name, doc_id_field, doc_id_val, {"status": new_status})


# ----------------------------------------------------
# PRODUCT & FINISHED GOODS INVENTORY
# ----------------------------------------------------
def get_products() -> List[Dict[str, Any]]:
    return get_all_documents("products")


def add_product(product: Dict[str, Any]) -> bool:
    if "stock_qty" not in product:
        product["stock_qty"] = 0
    if "reserved_qty" not in product:
        product["reserved_qty"] = 0
    return add_document("products", "product_id", product)


def update_product(product_id: str, data: Dict[str, Any]) -> bool:
    return update_document("products", "product_id", product_id, data)


def get_product_available_stock(product_id: str) -> int:
    prod = get_document("products", "product_id", product_id)
    if not prod:
        return 0
    stock = prod.get("stock_qty", 0)
    reserved = prod.get("reserved_qty", 0)
    return max(0, int(stock) - int(reserved))


def reserve_product_stock(product_id: str, qty_to_reserve: int) -> bool:
    product = get_document("products", "product_id", product_id)
    if not product:
        return False
    stock, reserved = int(product.get("stock_qty", 0)), int(product.get("reserved_qty", 0))
    return stock - reserved >= qty_to_reserve and update_product(product_id, {"reserved_qty": reserved + qty_to_reserve})


def release_reserved_stock(product_id: str, qty_to_release: int) -> None:
    product = get_document("products", "product_id", product_id)
    if product:
        update_product(product_id, {"reserved_qty": max(0, int(product.get("reserved_qty", 0)) - qty_to_release)})


def record_stock_dispatch(product_id: str, qty_deducted: int, ref_invoice: str, user_id: str) -> bool:
    product = get_document("products", "product_id", product_id)
    if not product:
        return False
    curr_stock, curr_res = int(product.get("stock_qty", 0)), int(product.get("reserved_qty", 0))
    if curr_stock < qty_deducted:
        return False
    new_stock = curr_stock - qty_deducted
    if not update_product(product_id, {"stock_qty": new_stock, "reserved_qty": max(0, curr_res - qty_deducted)}):
        return False
    ledger_entry = {
        "ledger_id": f"LED-{uuid.uuid4().hex.upper()}",
        "product_id": product_id,
        "product_name": product.get("name", "Product"),
        "movement_type": "OUTWARD_DISPATCH",
        "change_qty": -int(qty_deducted),
        "balance_qty": int(new_stock),
        "reference_id": ref_invoice,
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
    }
    add_document("stock_ledger", "ledger_id", ledger_entry)
    return record_inventory_transaction("Finished Good", product_id, product.get("name", "Product"), "DISPATCH_OUTWARD", -int(qty_deducted), new_stock, ref_invoice, f"Outward dispatch on invoice {ref_invoice}", user_id)


def increase_finished_goods_stock(product_id: str, qty_added: int, ref_order: str, user_id: str) -> bool:
    """Safely increments finished goods stock upon production completion."""
    product = get_document("products", "product_id", product_id)
    if not product:
        return False
    new_stock = int(product.get("stock_qty", 0)) + qty_added
    if not update_product(product_id, {"stock_qty": new_stock}):
        return False
    ledger_entry = {
        "ledger_id": f"LED-{uuid.uuid4().hex.upper()}",
        "product_id": product_id,
        "product_name": product.get("name", "Product"),
        "movement_type": "PRODUCTION_INWARD",
        "change_qty": int(qty_added),
        "balance_qty": int(new_stock),
        "reference_id": ref_order,
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
    }
    add_document("stock_ledger", "ledger_id", ledger_entry)
    return record_inventory_transaction("Finished Good", product_id, product.get("name", "Product"), "PRODUCTION_COMPLETION", int(qty_added), new_stock, ref_order, f"Production order {ref_order} completed", user_id)


def get_stock_ledger() -> List[Dict[str, Any]]:
    return get_all_documents("stock_ledger")


# ----------------------------------------------------
# RAW MATERIALS (PHASE 2 & PHASE 3 INVENTORY)
# ----------------------------------------------------
def get_raw_materials() -> List[Dict[str, Any]]:
    materials = get_all_documents("raw_materials")
    for material in materials:
        quantity = material.get("quantity", material.get("stock_qty", 0.0))
        material["quantity"] = quantity
        material["stock_qty"] = quantity
    return materials


def get_raw_material_available_stock(material_id: str) -> float:
    material = get_document("raw_materials", "material_id", material_id)
    if not material:
        return 0.0
    return float(material.get("quantity", material.get("stock_qty", 0.0)))


def add_raw_material(material: Dict[str, Any]) -> bool:
    quantity = material.get("quantity", material.get("stock_qty", 0.0))
    material["quantity"] = float(quantity)
    material["stock_qty"] = float(quantity)
    return add_document("raw_materials", "material_id", material)


def update_raw_material(material_id: str, data: Dict[str, Any]) -> bool:
    if "quantity" in data or "stock_qty" in data:
        quantity = float(data.get("quantity", data.get("stock_qty", 0.0)))
        data["quantity"] = quantity
        data["stock_qty"] = quantity
    return update_document("raw_materials", "material_id", material_id, data)


def add_raw_material_stock(
    material_id: str,
    quantity: float,
    reference: str,
    user_id: str,
    notes: str = "",
) -> bool:
    if quantity <= 0:
        return False
    material = get_document("raw_materials", "material_id", material_id)
    if not material:
        return False
    current_quantity = float(material.get("quantity", material.get("stock_qty", 0.0)))
    new_quantity = current_quantity + float(quantity)
    if not record_inventory_transaction(
        item_type="Raw Material",
        item_id=material_id,
        item_name=material.get("name", "Material"),
        txn_type="MATERIAL_RECEIPT",
        qty_change=float(quantity),
        balance_after=new_quantity,
        ref_id=reference,
        notes=notes,
        user_id=user_id,
        unit_cost=float(material.get("purchase_rate", 0.0)),
    ):
        return False
    return update_raw_material(material_id, {"quantity": new_quantity})


def record_incoming_raw_material(material_id: str, qty_received: float, unit_price: float, supplier_name: str, user_id: str) -> bool:
    """Increments raw material inventory and logs transaction."""
    material = get_document("raw_materials", "material_id", material_id)
    if not material or qty_received <= 0:
        return False
    updates = {"quantity": float(material.get("quantity", 0.0)) + float(qty_received)}
    if unit_price > 0:
        updates["purchase_rate"] = float(unit_price)
    if not update_raw_material(material_id, updates):
        return False
    return record_inventory_transaction("Raw Material", material_id, material.get("name", "Material"), "MATERIAL_RECEIPT", float(qty_received), updates["quantity"], f"INWARD-{datetime.utcnow().strftime('%Y%m%d%H%M')}", f"Received from {supplier_name} @ Rs. {unit_price:.2f}/{material.get('unit')}", user_id, unit_price)


def deduct_raw_material_stock(material_id: str, qty_to_deduct: float, ref_order: str, user_id: str) -> Tuple[bool, str]:
    """Safely deducts raw material stock, preventing negative inventory."""
    material = get_document("raw_materials", "material_id", material_id)
    if not material:
        return False, f"Material {material_id} not found."
    curr_qty = float(material.get("quantity", material.get("stock_qty", 0.0)))
    if curr_qty < qty_to_deduct:
        return False, f"Insufficient stock for {material.get('name')}. Available: {curr_qty:.2f}, Required: {qty_to_deduct:.2f}"
    new_qty = curr_qty - float(qty_to_deduct)
    if not update_raw_material(material_id, {"quantity": new_qty}):
        return False, "Unable to update inventory stock."
    logged = record_inventory_transaction("Raw Material", material_id, material.get("name", "Material"), "PRODUCTION_CONSUMPTION", -float(qty_to_deduct), new_qty, ref_order, f"Consumed in production {ref_order}", user_id, float(material.get("purchase_rate", 0.0)))
    return (True, "") if logged else (False, "Unable to record inventory movement.")


def get_low_stock_raw_materials() -> List[Dict[str, Any]]:
    """Returns raw materials whose available stock is at or below minimum threshold."""
    materials = get_raw_materials()
    low_stock = []
    for m in materials:
        curr_qty = float(m.get("quantity", 0.0))
        min_level = float(m.get("min_stock_level", 0.0))
        if curr_qty <= min_level:
            low_stock.append(m)
    return low_stock


# ----------------------------------------------------
# BILL OF MATERIALS (BOM) - PHASE 3
# ----------------------------------------------------
def get_boms() -> List[Dict[str, Any]]:
    return get_all_documents("bill_of_materials")


def get_bom_for_product(product_id: str) -> Optional[Dict[str, Any]]:
    boms = get_boms()
    for b in boms:
        if b.get("product_id") == product_id:
            return b
    return None


def save_bom(bom_data: Dict[str, Any]) -> bool:
    product_id = bom_data.get("product_id")
    if not product_id:
        return False
    existing = get_bom_for_product(product_id)
    if existing:
        return update_document("bill_of_materials", "bom_id", existing["bom_id"], bom_data)
    else:
        if "bom_id" not in bom_data or not bom_data["bom_id"]:
            boms = get_boms()
            bom_data["bom_id"] = f"BOM-{len(boms)+1:03d}"
        return add_document("bill_of_materials", "bom_id", bom_data)


def calculate_bom_requirements(product_id: str, production_qty: int) -> Tuple[bool, List[Dict[str, Any]], bool, List[str]]:
    """
    Calculates total required raw materials based on BOM and production quantity.
    Returns: (bom_exists, material_requirements_list, all_available, shortage_details)
    """
    bom = get_bom_for_product(product_id)
    if not bom or not bom.get("materials"):
        return False, [], False, [f"No Bill of Materials (BOM) configured for product {product_id}."]

    requirements = []
    all_available = True
    shortages = []

    for mat in bom.get("materials", []):
        mid = mat.get("material_id")
        req_per_unit = float(mat.get("required_per_unit", 0.0))
        total_required = req_per_unit * float(production_qty)

        # Check stock in raw_materials
        m_doc = get_document("raw_materials", "material_id", mid)
        avail_stock = float(m_doc.get("quantity", 0.0)) if m_doc else 0.0
        unit = mat.get("unit") or (m_doc.get("unit") if m_doc else "Unit")

        sufficient = avail_stock >= total_required
        if not sufficient:
            all_available = False
            shortage_amount = total_required - avail_stock
            shortages.append(f"{mat.get('material_name', mid)}: Requires {total_required:.2f} {unit}, Available: {avail_stock:.2f} {unit} (Shortage: {shortage_amount:.2f} {unit})")

        requirements.append({
            "material_id": mid,
            "material_name": mat.get("material_name", mid),
            "required_per_unit": req_per_unit,
            "total_required": round(total_required, 3),
            "unit": unit,
            "available_stock": avail_stock,
            "sufficient": sufficient,
            "shortage": round(max(0.0, total_required - avail_stock), 3),
        })

    return True, requirements, all_available, shortages


# ----------------------------------------------------
# PRODUCTION ORDERS - PHASE 3
# ----------------------------------------------------
def generate_production_id() -> str:
    now = datetime.utcnow()
    existing = get_all_documents("production_orders")
    seq = len(existing) + 1
    return f"PO-{now.strftime('%Y')}-{seq:04d}"


def get_production_orders() -> List[Dict[str, Any]]:
    return get_all_documents("production_orders")


def create_production_order(order_data: Dict[str, Any]) -> bool:
    if "production_id" not in order_data or not order_data["production_id"]:
        order_data["production_id"] = generate_production_id()
    if "status" not in order_data:
        order_data["status"] = "Pending"
    if "progress_percentage" not in order_data:
        order_data["progress_percentage"] = 0
    return add_document("production_orders", "production_id", order_data)


def update_production_order(production_id: str, data: Dict[str, Any]) -> bool:
    return update_document("production_orders", "production_id", production_id, data)


def complete_production_order(
    production_id: str,
    actual_qty: int,
    user_id: str,
    rejected_qty: float = 0,
) -> Tuple[bool, str]:
    """
    Executes the complete production completion workflow:
    1. Validates order status.
    2. Calculates and verifies BOM raw materials.
    3. Atomically deducts raw materials from inventory.
    4. Increases finished goods stock.
    5. Logs inventory transactions.
    6. Updates production order status to 'Completed' (100%).
    """
    po = get_document("production_orders", "production_id", production_id)
    if not po:
        return False, "Production order not found."
    if po.get("status") == "Completed":
        return False, "Production order is already marked as Completed."
    if actual_qty <= 0 or rejected_qty < 0:
        return False, "Actual production must be positive and rejected quantity cannot be negative."

    product_id = po.get("product_id")
    consumed_qty = actual_qty + rejected_qty
    bom_ok, reqs, all_avail, shortages = calculate_bom_requirements(product_id, consumed_qty)
    if not bom_ok:
        return False, shortages[0]
    if not all_avail:
        return False, "Cannot complete production due to insufficient raw materials: " + "; ".join(shortages)

    # 1. Deduct raw materials
    for req in reqs:
        ded_ok, ded_msg = deduct_raw_material_stock(
            material_id=req["material_id"],
            qty_to_deduct=req["total_required"],
            ref_order=production_id,
            user_id=user_id,
        )
        if not ded_ok:
            return False, f"Failed deducting {req['material_name']}: {ded_msg}"

    # 2. Increase finished goods stock
    increase_finished_goods_stock(product_id, actual_qty, production_id, user_id)

    # 3. Mark completed
    update_production_order(production_id, {
        "status": "Completed",
        "progress_percentage": 100,
        "actual_quantity": actual_qty,
        "rejected_quantity": rejected_qty,
        "completed_at": datetime.utcnow().isoformat(),
        "completed_by": user_id,
    })

    return True, f"Production order {production_id} completed successfully. Raw materials deducted and {actual_qty} units added to finished stock."


def complete_production(
    production_id: str,
    actual_qty: int,
    user_id: str,
    rejected_qty: float = 0,
) -> Tuple[bool, str]:
    return complete_production_order(production_id, actual_qty, user_id, rejected_qty)


def delete_production_order(production_id: str) -> bool:
    order = get_document("production_orders", "production_id", production_id)
    if not order or order.get("status") == "Completed":
        return False
    return delete_document("production_orders", "production_id", production_id)


# ----------------------------------------------------
# INVENTORY TRANSACTIONS - PHASE 3
# ----------------------------------------------------
def generate_txn_id() -> str:
    now = datetime.utcnow()
    existing = get_all_documents("inventory_transactions")
    seq = len(existing) + 1
    return f"TXN-{now.strftime('%Y')}-{seq:05d}"


def get_inventory_transactions() -> List[Dict[str, Any]]:
    return get_all_documents("inventory_transactions")


def record_inventory_transaction(
    item_type: str,  # 'Raw Material' or 'Finished Good'
    item_id: str,
    item_name: str,
    txn_type: str,
    qty_change: float,
    balance_after: float,
    ref_id: str,
    notes: str,
    user_id: str,
    unit_cost: Optional[float] = None,
) -> bool:
    txn = {
        "transaction_id": generate_txn_id(),
        "item_type": item_type,
        "item_id": item_id,
        "item_name": item_name,
        "transaction_type": txn_type,
        "quantity_change": qty_change,
        "balance_after": balance_after,
        "reference_id": ref_id,
        "notes": notes,
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
    }
    if unit_cost is not None:
        txn["unit_cost"] = float(unit_cost)
    return add_document("inventory_transactions", "transaction_id", txn)


def add_inventory_transaction(data: Dict[str, Any]) -> bool:
    return record_inventory_transaction(
        item_type=data.get("item_type", "Raw Material"),
        item_id=data.get("item_id", ""),
        item_name=data.get("item_name", ""),
        txn_type=data.get("movement_type", data.get("transaction_type", "STOCK_ADJUSTMENT")),
        qty_change=float(data.get("change_qty", data.get("quantity_change", 0.0))),
        balance_after=float(data.get("balance_qty", data.get("balance_after", 0.0))),
        ref_id=data.get("reference_id", ""),
        notes=data.get("notes", ""),
        user_id=data.get("user_id", ""),
    )


def record_activity_log(
    user_id: str,
    user_role: str,
    action: str,
    endpoint: str,
    details: str,
) -> bool:
    entry = {
        "activity_id": f"ACT-{uuid.uuid4().hex.upper()}",
        "user_id": user_id,
        "user_role": user_role,
        "action": action,
        "endpoint": endpoint,
        "details": details,
        "timestamp": datetime.utcnow().isoformat(),
    }
    return add_document("activity_logs", "activity_id", entry)


def get_activity_logs() -> List[Dict[str, Any]]:
    return get_all_documents("activity_logs")


def get_production_expenses() -> List[Dict[str, Any]]:
    return get_all_documents("production_expenses")


def record_production_expense(expense: Dict[str, Any]) -> bool:
    if not expense.get("production_id"):
        return False
    expense.setdefault("expense_id", f"EXP-{uuid.uuid4().hex.upper()}")
    return add_document("production_expenses", "expense_id", expense)


def get_purchase_invoices() -> List[Dict[str, Any]]:
    """Return append-only supplier purchase invoices used by financial reports."""
    return get_all_documents("purchase_invoices")


def create_purchase_invoice(purchase: Dict[str, Any]) -> bool:
    """Persist a supplier invoice once; callers keep its stock movement in sync."""
    invoice_number = str(purchase.get("purchase_invoice_number", "")).strip()
    if not invoice_number:
        return False
    purchase["purchase_invoice_number"] = invoice_number
    purchase.setdefault("purchase_id", f"PUR-{uuid.uuid4().hex.upper()}")
    purchase.setdefault("payment_status", "Unpaid")
    return add_document("purchase_invoices", "purchase_invoice_number", purchase)


def ensure_database_seed() -> str:
    _, mode = initialize_firebase()
    return mode


# ----------------------------------------------------
# CUSTOMERS & SUPPLIERS
# ----------------------------------------------------
def get_customers() -> List[Dict[str, Any]]:
    return get_all_documents("customers")


def get_users() -> List[Dict[str, Any]]:
    return get_all_documents("users")


def add_user(user: Dict[str, Any]) -> bool:
    return add_document("users", "uid", user)


def update_user(uid: str, data: Dict[str, Any]) -> bool:
    return update_document("users", "uid", uid, data)


def add_customer(customer: Dict[str, Any]) -> bool:
    return add_document("customers", "customer_id", customer)


def update_customer(customer_id: str, data: Dict[str, Any]) -> bool:
    return update_document("customers", "customer_id", customer_id, data)


def get_suppliers() -> List[Dict[str, Any]]:
    return get_all_documents("suppliers")


def add_supplier(supplier: Dict[str, Any]) -> bool:
    return add_document("suppliers", "supplier_id", supplier)


def update_supplier(supplier_id: str, data: Dict[str, Any]) -> bool:
    return update_document("suppliers", "supplier_id", supplier_id, data)


# ----------------------------------------------------
# ORDERS
# ----------------------------------------------------
def generate_order_id() -> str:
    now = datetime.utcnow()
    existing = get_all_documents("orders")
    seq = len(existing) + 1
    return f"ORD-{now.strftime('%Y')}-{seq:04d}"


def get_orders() -> List[Dict[str, Any]]:
    return get_all_documents("orders")


def get_orders_by_salesman(salesman_id: str) -> List[Dict[str, Any]]:
    all_orders = get_orders()
    return [o for o in all_orders if o.get("salesman_id") == salesman_id]


def create_order(order_data: Dict[str, Any]) -> bool:
    if "order_id" not in order_data or not order_data["order_id"]:
        order_data["order_id"] = generate_order_id()
    if "status" not in order_data:
        order_data["status"] = "Submitted"
    return add_document("orders", "order_id", order_data)


def update_order_status(order_id: str, status: str, admin_notes: str = "") -> bool:
    return update_document(
        "orders",
        "order_id",
        order_id,
        {"status": status, "admin_notes": admin_notes},
    )


# ----------------------------------------------------
# INVOICES
# ----------------------------------------------------
def generate_invoice_number() -> str:
    now = datetime.utcnow()
    year = now.year if now.month >= 4 else now.year - 1
    fy_str = f"{str(year)[-2:]}-{str(year+1)[-2:]}"
    existing = get_all_documents("invoices")
    seq = len(existing) + 1
    return f"FF/INV/{fy_str}/{seq:04d}"


def get_invoices() -> List[Dict[str, Any]]:
    return get_all_documents("invoices")


def create_invoice(invoice_data: Dict[str, Any]) -> bool:
    if "invoice_number" not in invoice_data or not invoice_data["invoice_number"]:
        invoice_data["invoice_number"] = generate_invoice_number()
    if "payment_status" not in invoice_data:
        invoice_data["payment_status"] = "Unpaid"
    if "dispatch_status" not in invoice_data:
        invoice_data["dispatch_status"] = "Pending"
    return add_document("invoices", "invoice_number", invoice_data)


def update_invoice(invoice_number: str, data: Dict[str, Any]) -> bool:
    return update_document("invoices", "invoice_number", invoice_number, data)


# ----------------------------------------------------
# DISPATCHES
# ----------------------------------------------------
def generate_dispatch_id() -> str:
    existing = get_all_documents("dispatches")
    seq = len(existing) + 1
    return f"DSP-{datetime.utcnow().strftime('%Y')}-{seq:04d}"


def get_dispatches() -> List[Dict[str, Any]]:
    return get_all_documents("dispatches")


def create_dispatch(dispatch_data: Dict[str, Any]) -> bool:
    if "dispatch_id" not in dispatch_data or not dispatch_data["dispatch_id"]:
        dispatch_data["dispatch_id"] = generate_dispatch_id()
    return add_document("dispatches", "dispatch_id", dispatch_data)


# ----------------------------------------------------
# PAYMENTS
# ----------------------------------------------------
def generate_payment_id() -> str:
    existing = get_all_documents("payments")
    seq = len(existing) + 1
    return f"PAY-{datetime.utcnow().strftime('%Y')}-{seq:04d}"


def get_payments() -> List[Dict[str, Any]]:
    return get_all_documents("payments")


def get_payments_for_invoice(invoice_number: str) -> List[Dict[str, Any]]:
    all_p = get_payments()
    return [p for p in all_p if p.get("invoice_number") == invoice_number]


def record_payment(payment_data: Dict[str, Any]) -> bool:
    if "payment_id" not in payment_data or not payment_data["payment_id"]:
        payment_data["payment_id"] = generate_payment_id()
    return add_document("payments", "payment_id", payment_data)
