"""Financial report calculations and export rendering for FactoryFlow."""

import csv
import io
from bisect import bisect_right
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from utils.gst_calculations import to_decimal

REPORTS = {
    "sales": ("Sales Register", [
        "Invoice", "Date", "Customer", "Product", "Quantity", "Unit Price",
        "Discount", "Taxable Value", "GST Rate", "CGST", "SGST", "IGST",
        "Invoice Total", "Paid", "Outstanding", "Payment Status",
    ]),
    "purchases": ("Material Receipt Register", [
        "Reference", "Date", "Supplier", "Material", "Quantity", "Unit Cost",
        "Recorded Value", "GST Status",
    ]),
    "gst": ("GST Summary", [
        "Invoice", "Date", "Customer", "Taxable Value", "CGST", "SGST", "IGST", "Total GST",
    ]),
    "production": ("Production Cost Register", [
        "Batch", "Date", "Product", "Good Packets", "Rejected Packets",
        "Material Cost", "Labour", "Utilities", "Maintenance", "Other Overhead",
        "Total Cost", "Cost Per Packet", "Cost Basis",
    ]),
    "stock": ("Stock Valuation", [
        "Item Type", "Item", "Quantity", "Unit", "Unit Cost", "Stock Value",
    ]),
    "profit_loss": ("Gross Profit Summary", [
        "Invoice", "Order", "Date", "Customer", "Product", "Taxable Sales", "Estimated COGS",
        "Gross Profit", "Gross Margin %",
    ]),
    "receivables": ("Customer Receivables", [
        "Invoice", "Date", "Customer", "Invoice Total", "Paid", "Outstanding", "Status",
    ]),
    "payables": ("Supplier Payables", [
        "Purchase Invoice", "Date", "Supplier", "Purchase Total", "Paid", "Outstanding", "Status",
    ]),
}


def _date(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def _in_period(value: Any, start: Optional[date], end: Optional[date]) -> bool:
    record_date = _date(value)
    if record_date is None:
        return start is None and end is None
    return (start is None or record_date >= start) and (end is None or record_date <= end)


def _money(value: Any) -> Decimal:
    return to_decimal(value)


def _sum_payments(invoice_number: str, payments: Iterable[Dict[str, Any]]) -> Decimal:
    return sum(
        (_money(payment.get("amount")) for payment in payments
         if payment.get("invoice_number") == invoice_number
         and payment.get("status", "Confirmed") == "Confirmed"),
        Decimal("0.00"),
    )


def _invoice_tax(invoice: Dict[str, Any]) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
    cgst = _money(invoice.get("total_cgst", invoice.get("total_cgst_amount", 0)))
    sgst = _money(invoice.get("total_sgst", invoice.get("total_sgst_amount", 0)))
    igst = _money(invoice.get("total_igst", invoice.get("total_igst_amount", 0)))
    if not (cgst or sgst or igst):
        for item in invoice.get("items", []):
            cgst += _money(item.get("cgst_amount"))
            sgst += _money(item.get("sgst_amount"))
            igst += _money(item.get("igst_amount"))
    return cgst, sgst, igst, cgst + sgst + igst


def build_financial_reports(
    *,
    invoices: List[Dict[str, Any]],
    payments: List[Dict[str, Any]],
    production_orders: List[Dict[str, Any]],
    materials: List[Dict[str, Any]],
    products: List[Dict[str, Any]],
    inventory_transactions: List[Dict[str, Any]],
    expenses: List[Dict[str, Any]],
    purchase_invoices: Optional[List[Dict[str, Any]]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    customer_name: Optional[str] = None,
    production_product_id: Optional[str] = None,
    production_id: Optional[str] = None,
) -> Dict[str, Any]:
    start = _date(start_date)
    end = _date(end_date)
    if start_date and start is None:
        raise ValueError("Start date must use YYYY-MM-DD format.")
    if end_date and end is None:
        raise ValueError("End date must use YYYY-MM-DD format.")
    if start and end and start > end:
        raise ValueError("Start date must not be after end date.")

    filtered_invoices = [
        invoice for invoice in invoices
        if _in_period(invoice.get("invoice_date"), start, end)
        and (not customer_name or invoice.get("customer_name") == customer_name)
    ]
    filtered_transactions = [
        transaction for transaction in inventory_transactions
        if _in_period(transaction.get("timestamp"), start, end)
    ]
    payments_by_invoice: Dict[str, List[Dict[str, Any]]] = {}
    for payment in payments:
        if payment.get("status", "Confirmed") == "Confirmed":
            payments_by_invoice.setdefault(payment.get("invoice_number", ""), []).append(payment)
    transactions_by_reference: Dict[str, List[Dict[str, Any]]] = {}
    for transaction in inventory_transactions:
        transactions_by_reference.setdefault(transaction.get("reference_id", ""), []).append(transaction)

    current_rates = {
        material.get("material_id"): _money(material.get("purchase_rate"))
        for material in materials
    }
    product_names = {product.get("product_id"): product.get("name", "") for product in products}
    expense_by_batch: Dict[str, Dict[str, Decimal]] = {}
    for expense in expenses:
        batch_id = expense.get("production_id", "")
        values = expense_by_batch.setdefault(batch_id, {})
        for field in ("labour_cost", "utilities_cost", "maintenance_cost", "other_cost"):
            values[field] = values.get(field, Decimal("0.00")) + _money(expense.get(field))

    production_rows: List[Dict[str, Any]] = []
    unit_cost_history: Dict[str, List[Tuple[date, Decimal]]] = {}
    for order in production_orders:
        batch_id = order.get("production_id", "")
        production_date_value = order.get("completed_at") or order.get("start_date")
        production_date = _date(production_date_value)
        consumption = [
            transaction for transaction in transactions_by_reference.get(batch_id, [])
            if transaction.get("transaction_type", transaction.get("movement_type")) == "PRODUCTION_CONSUMPTION"
        ]
        material_cost = Decimal("0.00")
        cost_complete = bool(consumption)
        used_snapshot = bool(consumption)
        for transaction in consumption:
            rate = transaction.get("unit_cost")
            if rate is None:
                used_snapshot = False
                rate = current_rates.get(transaction.get("item_id"), Decimal("0.00"))
            if _money(rate) <= 0:
                cost_complete = False
            material_cost += abs(_money(transaction.get("quantity_change", transaction.get("change_qty", 0)))) * _money(rate)
        batch_expenses = expense_by_batch.get(batch_id, {})
        labour = batch_expenses.get("labour_cost", Decimal("0.00"))
        utilities = batch_expenses.get("utilities_cost", Decimal("0.00"))
        maintenance = batch_expenses.get("maintenance_cost", Decimal("0.00"))
        other = batch_expenses.get("other_cost", Decimal("0.00"))
        calculated_cost = material_cost + labour + utilities + maintenance + other
        total_cost = calculated_cost if cost_complete else None
        quantity = _money(order.get("actual_quantity", 0))
        rejected = _money(order.get("rejected_quantity", order.get("wastage_quantity", 0)))
        cost_per_packet = _money(calculated_cost / quantity) if cost_complete and quantity > 0 else None
        if cost_per_packet is not None and order.get("status") == "Completed":
            product_id = order.get("product_id")
            if production_date:
                unit_cost_history.setdefault(product_id, []).append((production_date, cost_per_packet))
        production_row = {
            "Batch": batch_id,
            "Date": production_date_value or "",
            "Product": order.get("product_name", product_names.get(order.get("product_id"), "")),
            "Good Packets": quantity,
            "Rejected Packets": rejected,
            "Material Cost": material_cost if consumption else "Not recorded",
            "Labour": labour,
            "Utilities": utilities,
            "Maintenance": maintenance,
            "Other Overhead": other,
            "Total Cost": total_cost,
            "Cost Per Packet": cost_per_packet if cost_per_packet is not None else "Not costed",
            "Cost Basis": (
                "Recorded consumption rates" if used_snapshot
                else "Estimated using current material rates" if cost_complete
                else "Incomplete: no priced material consumption"
            ),
        }
        if (
            _in_period(production_date_value, start, end)
            and (not production_product_id or order.get("product_id") == production_product_id)
            and (not production_id or batch_id == production_id)
        ):
            production_rows.append(production_row)
    for history in unit_cost_history.values():
        history.sort(key=lambda item: item[0])
    product_unit_costs = {
        product_id: history[-1][1]
        for product_id, history in unit_cost_history.items()
        if history
    }
    unit_cost_history_dates = {
        product_id: [record_date for record_date, _ in history]
        for product_id, history in unit_cost_history.items()
    }

    sales_rows: List[Dict[str, Any]] = []
    gst_rows: List[Dict[str, Any]] = []
    pnl_rows: List[Dict[str, Any]] = []
    receivable_rows: List[Dict[str, Any]] = []
    for invoice in filtered_invoices:
        invoice_number = invoice.get("invoice_number", "")
        paid = _sum_payments(invoice_number, payments_by_invoice.get(invoice_number, []))
        total = _money(invoice.get("total_amount"))
        outstanding = max(Decimal("0.00"), total - paid)
        cgst, sgst, igst, total_gst = _invoice_tax(invoice)
        taxable = _money(invoice.get("total_taxable_value", invoice.get("taxable_amount", 0)))
        gst_rows.append({
            "Invoice": invoice_number, "Date": invoice.get("invoice_date", ""),
            "Customer": invoice.get("customer_name", ""), "Taxable Value": taxable,
            "CGST": cgst, "SGST": sgst, "IGST": igst, "Total GST": total_gst,
        })
        receivable_rows.append({
            "Invoice": invoice_number, "Date": invoice.get("invoice_date", ""),
            "Customer": invoice.get("customer_name", ""), "Invoice Total": total,
            "Paid": paid, "Outstanding": outstanding,
            "Status": "Paid" if outstanding == 0 else "Partially Paid" if paid > 0 else "Unpaid",
        })
        for item in invoice.get("items", []):
            line_taxable = _money(item.get("taxable_value"))
            sales_rows.append({
                "Invoice": invoice_number, "Date": invoice.get("invoice_date", ""),
                "Customer": invoice.get("customer_name", ""), "Product": item.get("name", ""),
                "Quantity": _money(item.get("quantity")), "Unit Price": _money(item.get("unit_price")),
                "Discount": _money(item.get("discount_amount")), "Taxable Value": line_taxable,
                "GST Rate": _money(item.get("gst_rate")), "CGST": _money(item.get("cgst_amount")),
                "SGST": _money(item.get("sgst_amount")), "IGST": _money(item.get("igst_amount")),
                "Invoice Total": total, "Paid": paid, "Outstanding": outstanding,
                "Payment Status": receivable_rows[-1]["Status"],
            })
            quantity = _money(item.get("quantity"))
            invoice_date = _date(invoice.get("invoice_date"))
            history = unit_cost_history.get(item.get("product_id"), [])
            history_dates = unit_cost_history_dates.get(item.get("product_id"), [])
            history_index = bisect_right(history_dates, invoice_date) - 1 if invoice_date else -1
            unit_cost = history[history_index][1] if history_index >= 0 else None
            cogs = quantity * unit_cost if unit_cost is not None else None
            gross_profit = line_taxable - cogs if cogs is not None else None
            margin = _money(gross_profit / line_taxable * Decimal("100")) if gross_profit is not None and line_taxable else None
            pnl_rows.append({
                "Invoice": invoice_number, "Order": invoice.get("order_id", ""),
                "Date": invoice.get("invoice_date", ""),
                "Customer": invoice.get("customer_name", ""), "Product": item.get("name", ""),
                "Taxable Sales": line_taxable,
                "Estimated COGS": cogs if cogs is not None else "Not costed",
                "Gross Profit": gross_profit if gross_profit is not None else "Not costed",
                "Gross Margin %": margin if margin is not None else "Not costed",
            })

    material_receipts = []
    payables: List[Dict[str, Any]] = []
    input_cgst = input_sgst = input_igst = Decimal("0.00")
    for purchase in purchase_invoices or []:
        if not _in_period(purchase.get("purchase_date"), start, end):
            continue
        taxable = _money(purchase.get("taxable_value"))
        cgst = _money(purchase.get("cgst"))
        sgst = _money(purchase.get("sgst"))
        igst = _money(purchase.get("igst"))
        total = _money(purchase.get("total_amount", taxable + cgst + sgst + igst))
        paid = _money(purchase.get("amount_paid"))
        outstanding = max(Decimal("0.00"), total - paid)
        input_cgst += cgst if purchase.get("itc_eligible", False) else Decimal("0.00")
        input_sgst += sgst if purchase.get("itc_eligible", False) else Decimal("0.00")
        input_igst += igst if purchase.get("itc_eligible", False) else Decimal("0.00")
        material_receipts.append({
            "Reference": purchase.get("purchase_invoice_number", ""),
            "Date": purchase.get("purchase_date", ""),
            "Supplier": purchase.get("supplier_name", ""),
            "Material": purchase.get("material_name", ""),
            "Quantity": _money(purchase.get("quantity")),
            "Unit Cost": _money(purchase.get("unit_price")),
            "Recorded Value": taxable,
            "GST Status": "ITC eligible" if purchase.get("itc_eligible", False) else "ITC not eligible",
        })
        payables.append({
            "Purchase Invoice": purchase.get("purchase_invoice_number", ""),
            "Date": purchase.get("purchase_date", ""),
            "Supplier": purchase.get("supplier_name", ""),
            "Purchase Total": total, "Paid": paid, "Outstanding": outstanding,
            "Status": "Paid" if outstanding == 0 else "Partially Paid" if paid > 0 else "Unpaid",
        })
    # Legacy inward movements without an invoice remain visible, but cannot
    # contribute to supplier balances or input-tax credit.
    for transaction in filtered_transactions:
        movement = transaction.get("transaction_type", transaction.get("movement_type", ""))
        quantity = _money(transaction.get("quantity_change", transaction.get("change_qty", 0)))
        if movement == "MATERIAL_RECEIPT" and quantity > 0:
            unit_cost = transaction.get("unit_cost")
            material_receipts.append({
                "Reference": transaction.get("reference_id", ""),
                "Date": transaction.get("timestamp", ""),
                "Supplier": transaction.get("supplier_name", "Not recorded"),
                "Material": transaction.get("item_name", ""),
                "Quantity": quantity,
                "Unit Cost": _money(unit_cost) if unit_cost is not None else "Not recorded",
                "Recorded Value": quantity * _money(unit_cost) if unit_cost is not None else "Not recorded",
                "GST Status": "Not recorded",
            })

    stock_rows = []
    for material in materials:
        quantity = _money(material.get("quantity", material.get("stock_qty", 0)))
        unit_cost = current_rates.get(material.get("material_id"), Decimal("0.00"))
        stock_rows.append({
            "Item Type": "Raw Material", "Item": material.get("name", ""),
            "Quantity": quantity, "Unit": material.get("unit", ""),
            "Unit Cost": unit_cost, "Stock Value": quantity * unit_cost,
        })
    for product in products:
        quantity = _money(product.get("stock_qty", 0))
        unit_cost = product_unit_costs.get(product.get("product_id"))
        stock_rows.append({
            "Item Type": "Finished Good", "Item": product.get("name", ""),
            "Quantity": quantity, "Unit": "packets",
            "Unit Cost": unit_cost if unit_cost is not None else "Not costed",
            "Stock Value": quantity * unit_cost if unit_cost is not None else "Not costed",
        })

    sales_total = sum((_money(row["Taxable Value"]) for row in gst_rows), Decimal("0.00"))
    gst_total = sum((_money(row["Total GST"]) for row in gst_rows), Decimal("0.00"))
    total_paid = sum((_money(row["Paid"]) for row in receivable_rows), Decimal("0.00"))
    receivables = sum((_money(row["Outstanding"]) for row in receivable_rows), Decimal("0.00"))
    production_total = sum(
        (_money(row["Total Cost"]) for row in production_rows if isinstance(row["Total Cost"], Decimal)),
        Decimal("0.00"),
    )
    costed_pnl_rows = [row for row in pnl_rows if isinstance(row["Estimated COGS"], Decimal)]
    estimated_cogs = sum((_money(row["Estimated COGS"]) for row in costed_pnl_rows), Decimal("0.00"))
    gross_profit = sum((_money(row["Gross Profit"]) for row in costed_pnl_rows), Decimal("0.00"))
    costed_sales = sum((_money(row["Taxable Sales"]) for row in costed_pnl_rows), Decimal("0.00"))
    gross_margin = _money(gross_profit / costed_sales * Decimal("100")) if costed_sales else Decimal("0.00")
    material_valuation = sum((_money(row["Stock Value"]) for row in stock_rows if row["Item Type"] == "Raw Material"), Decimal("0.00"))
    summaries = {
        "sales": sales_total,
        "gst": gst_total,
        "input_gst": input_cgst + input_sgst + input_igst,
        "net_gst_payable": gst_total - input_cgst - input_sgst - input_igst,
        "paid": total_paid,
        "receivables": receivables,
        "payables": sum((_money(row["Outstanding"]) for row in payables), Decimal("0.00")),
        "production_cost": production_total,
        "estimated_cogs": estimated_cogs,
        "gross_profit": gross_profit,
        "gross_margin": gross_margin,
        "costed_sales": costed_sales,
        "inventory_value": material_valuation,
    }
    monthly = {}
    product_profitability = {}
    for row in gst_rows:
        month = str(row["Date"])[:7]
        if month:
            monthly.setdefault(month, {"revenue": Decimal("0.00"), "expenses": Decimal("0.00")})
            monthly[month]["revenue"] += _money(row["Taxable Value"])
    for row in production_rows:
        month = str(row["Date"])[:7]
        if month and isinstance(row["Total Cost"], Decimal):
            monthly.setdefault(month, {"revenue": Decimal("0.00"), "expenses": Decimal("0.00")})
            monthly[month]["expenses"] += row["Total Cost"]
    for row in costed_pnl_rows:
        name = row["Product"]
        entry = product_profitability.setdefault(name, {"sales": Decimal("0.00"), "cogs": Decimal("0.00"), "profit": Decimal("0.00")})
        entry["sales"] += _money(row["Taxable Sales"])
        entry["cogs"] += _money(row["Estimated COGS"])
        entry["profit"] += _money(row["Gross Profit"])
        month = str(row["Date"])[:7]
        if month:
            monthly.setdefault(month, {"revenue": Decimal("0.00"), "expenses": Decimal("0.00"), "gross_profit": Decimal("0.00")})
            monthly[month].setdefault("gross_profit", Decimal("0.00"))
            monthly[month]["gross_profit"] += _money(row["Gross Profit"])

    for values in monthly.values():
        values.setdefault("gross_profit", Decimal("0.00"))
    return {
        "sales": sales_rows,
        "purchases": material_receipts,
        "gst": gst_rows,
        "production": production_rows,
        "stock": stock_rows,
        "profit_loss": pnl_rows,
        "receivables": receivable_rows,
        "payables": payables,
        "summaries": summaries,
        "monthly": {key: monthly[key] for key in sorted(monthly)},
        "product_profitability": product_profitability,
        "date_range": (start_date or "", end_date or ""),
        "purchase_data_note": "Supplier invoices contribute to payables and eligible input tax credit. Legacy material receipts remain visible but do not infer tax, payment, or ITC eligibility.",
        "cost_data_note": "Historical production without recorded material-rate snapshots is estimated using current material rates.",
    }


def render_csv(report_type: str, rows: List[Dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    columns = REPORTS[report_type][1]
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: str(value) if value is not None else "" for key, value in row.items()})
    return output.getvalue().encode("utf-8-sig")


def render_xlsx(report_type: str, rows: List[Dict[str, Any]], summaries: Dict[str, Any]) -> bytes:
    import xlsxwriter

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    worksheet = workbook.add_worksheet(REPORTS[report_type][0][:31])
    header = workbook.add_format({"bold": True, "bg_color": "#17324d", "font_color": "#ffffff", "border": 1})
    money = workbook.add_format({"num_format": '"Rs. "#,##0.00'})
    date_format = workbook.add_format({"num_format": "yyyy-mm-dd"})
    columns = REPORTS[report_type][1]
    for col, name in enumerate(columns):
        worksheet.write(0, col, name, header)
        worksheet.set_column(col, col, min(max(len(name) + 2, 14), 26))
    for row_index, row in enumerate(rows, start=1):
        for col, name in enumerate(columns):
            value = row.get(name, "")
            if isinstance(value, Decimal):
                worksheet.write_number(row_index, col, float(value), money)
            elif name == "Date" and isinstance(value, str) and _date(value):
                worksheet.write_datetime(
                    row_index, col,
                    datetime.strptime(value[:10], "%Y-%m-%d"),
                    date_format,
                )
            else:
                worksheet.write(row_index, col, value)
    worksheet.freeze_panes(1, 0)
    worksheet.autofilter(0, 0, max(0, len(rows)), max(0, len(columns) - 1))
    summary_sheet = workbook.add_worksheet("Summary")
    summary_sheet.write_row(0, 0, ["Metric", "Value"], header)
    for index, (key, value) in enumerate(summaries.items(), start=1):
        summary_sheet.write(index, 0, key.replace("_", " ").title())
        summary_sheet.write(index, 1, float(value) if isinstance(value, Decimal) else str(value), money)
    summary_sheet.set_column(0, 0, 28)
    summary_sheet.set_column(1, 1, 20)
    workbook.close()
    return output.getvalue()


def render_pdf(
    report_type: str,
    rows: List[Dict[str, Any]],
    summaries: Dict[str, Any],
    period: Tuple[str, str],
) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    from utils.gst_calculations import FACTORY_NAME
    from xml.sax.saxutils import escape

    output = io.BytesIO()
    page_size = landscape(A4) if len(REPORTS[report_type][1]) > 7 else A4
    document = SimpleDocTemplate(
        output, pagesize=page_size, leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="TableCell", parent=styles["BodyText"], fontSize=6, leading=7))
    styles.add(ParagraphStyle(name="TableHeader", parent=styles["BodyText"], fontSize=6, leading=7, textColor=colors.white))
    available_width = page_size[0] - document.leftMargin - document.rightMargin
    elements = [
        Paragraph(FACTORY_NAME, styles["Heading2"]),
        Paragraph(REPORTS[report_type][0], styles["ReportTitle"]),
        Paragraph(
            "Period: {} to {} | Generated: {}".format(
                period[0] or "All dates", period[1] or "All dates",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            ),
            styles["Normal"],
        ),
        Spacer(1, 8),
    ]
    if rows:
        columns = REPORTS[report_type][1]
        data = [[Paragraph(escape(column), styles["TableHeader"]) for column in columns]]
        for row in rows:
            data.append([
                Paragraph(escape(str(row.get(column, ""))), styles["TableCell"])
                for column in columns
            ])
        table = Table(data, repeatRows=1, colWidths=[available_width / len(columns)] * len(columns))
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("LEADING", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c8d0d8")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f8")]),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No records for the selected period.", styles["Normal"]))
    elements.extend([Spacer(1, 10), Paragraph("Summary", styles["Heading3"])])
    summary_data = [["Metric", "Value"]] + [
        [key.replace("_", " ").title(), str(value)] for key, value in summaries.items()
    ]
    summary_table = Table(summary_data, colWidths=[available_width * 0.55, available_width * 0.45])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce6ef")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(page_size[0] - document.rightMargin, 7 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return output.getvalue()
