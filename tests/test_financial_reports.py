import unittest
import zipfile
from decimal import Decimal
from io import BytesIO

from utils.financial_reports import (
    build_financial_reports,
    render_csv,
    render_pdf,
    render_xlsx,
)


class FinancialReportTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "invoices": [{
                "invoice_number": "INV-001",
                "invoice_date": "2026-03-10",
                "customer_name": "Retailer A",
                "total_taxable_value": 100,
                "total_cgst": 2.5,
                "total_sgst": 2.5,
                "total_amount": 105,
                "items": [{
                    "product_id": "PRD-001",
                    "name": "Murukku 200g",
                    "quantity": 2,
                    "unit_price": 50,
                    "taxable_value": 100,
                    "discount_amount": 0,
                    "gst_rate": 5,
                    "cgst_amount": 2.5,
                    "sgst_amount": 2.5,
                    "igst_amount": 0,
                }],
            }],
            "payments": [{
                "invoice_number": "INV-001",
                "amount": 25,
                "status": "Confirmed",
            }],
            "production_orders": [{
                "production_id": "PO-001",
                "product_id": "PRD-001",
                "product_name": "Murukku 200g",
                "actual_quantity": 2,
                "rejected_quantity": 1,
                "status": "Completed",
                "completed_at": "2026-03-09T15:00:00",
            }],
            "materials": [{
                "material_id": "RM-001",
                "name": "Flour",
                "unit": "kg",
                "quantity": 10,
                "purchase_rate": 10,
            }],
            "products": [{
                "product_id": "PRD-001",
                "name": "Murukku 200g",
                "stock_qty": 4,
            }],
            "inventory_transactions": [{
                "reference_id": "PO-001",
                "transaction_type": "PRODUCTION_CONSUMPTION",
                "item_id": "RM-001",
                "item_name": "Flour",
                "quantity_change": -4,
                "unit_cost": 10,
                "timestamp": "2026-03-09T15:00:00",
            }],
            "expenses": [{
                "production_id": "PO-001",
                "expense_date": "2026-03-09",
                "labour_cost": 10,
                "utilities_cost": 0,
                "maintenance_cost": 0,
                "other_cost": 0,
            }],
        }

    def build(self, **overrides):
        return build_financial_reports(**{**self.data, **overrides})

    def test_gst_is_excluded_from_revenue_and_costed_profit(self):
        result = self.build()
        self.assertEqual(result["summaries"]["sales"], Decimal("100.00"))
        self.assertEqual(result["summaries"]["gst"], Decimal("5.00"))
        self.assertEqual(result["summaries"]["gross_profit"], Decimal("50.00"))
        self.assertEqual(result["summaries"]["gross_margin"], Decimal("50.00"))
        self.assertEqual(result["summaries"]["receivables"], Decimal("80.00"))
        self.assertEqual(result["production"][0]["Cost Per Packet"], Decimal("25.00"))

    def test_date_range_filters_reports_and_invalid_ranges_fail(self):
        result = self.build(start_date="2026-03-10", end_date="2026-03-10")
        self.assertEqual(len(result["sales"]), 1)
        self.assertEqual(result["production"], [])
        with self.assertRaises(ValueError):
            self.build(start_date="2026-03-11", end_date="2026-03-01")

    def test_customer_and_production_filters_are_applied(self):
        self.assertEqual(self.build(customer_name="Missing")["sales"], [])
        self.assertEqual(self.build(production_id="Missing")["production"], [])
        self.assertEqual(self.build(production_product_id="Missing")["production"], [])

    def test_reports_do_not_invent_production_cost_without_consumption(self):
        data = dict(self.data)
        data["inventory_transactions"] = []
        result = self.build(**data)
        self.assertEqual(result["production"][0]["Cost Per Packet"], "Not costed")
        self.assertEqual(result["profit_loss"][0]["Gross Profit"], "Not costed")

    def test_purchase_invoice_drives_payable_and_only_eligible_itc(self):
        result = self.build(purchase_invoices=[{
            "purchase_invoice_number": "PUR-001", "purchase_date": "2026-03-10",
            "supplier_name": "Supplier A", "material_name": "Flour", "quantity": 5,
            "unit_price": 10, "taxable_value": 50, "cgst": 1.25, "sgst": 1.25,
            "total_amount": 52.5, "amount_paid": 2.5, "itc_eligible": True,
        }])
        self.assertEqual(result["summaries"]["payables"], Decimal("50.00"))
        self.assertEqual(result["summaries"]["input_gst"], Decimal("2.50"))
        self.assertEqual(result["summaries"]["net_gst_payable"], Decimal("2.50"))
        self.assertEqual(result["payables"][0]["Status"], "Partially Paid")

    def test_exports_are_valid_for_populated_and_empty_reports(self):
        result = self.build()
        csv_bytes = render_csv("sales", result["sales"])
        self.assertIn(b"Invoice,Date,Customer", csv_bytes)

        xlsx_bytes = render_xlsx("sales", result["sales"], result["summaries"])
        with zipfile.ZipFile(BytesIO(xlsx_bytes)) as workbook:
            self.assertIn("xl/worksheets/sheet1.xml", workbook.namelist())

        pdf_bytes = render_pdf("sales", result["sales"], result["summaries"], result["date_range"])
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        empty_pdf = render_pdf("sales", [], result["summaries"], ("", ""))
        self.assertTrue(empty_pdf.startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()
