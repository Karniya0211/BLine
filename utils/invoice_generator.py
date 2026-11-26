"""
ReportLab Professional Tax Invoice Generator for FactoryFlow Phase 2.
Generates compliant, print-ready Indian GST Tax Invoices in PDF format:
- Factory details, GSTIN, State Code (33 - Tamil Nadu)
- Customer details, Bill-to & Ship-to addresses, Customer GSTIN
- Sequential invoice number & date
- Table of goods with HSN codes, quantity, rate, taxable value, CGST, SGST, IGST
- Total invoice amount in figures and words
- Authorised signatory block & payment status banner
"""

import io
from typing import Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from utils.helpers import format_currency


def generate_invoice_pdf(invoice_data: Dict[str, Any]) -> bytes:
    """
    Builds a professional GST Tax Invoice PDF using ReportLab and returns raw bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    
    # Custom industrial styles
    style_title = ParagraphStyle(
        "InvTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=18,
        textColor=colors.HexColor("#141e28"),
    )
    style_sub = ParagraphStyle(
        "InvSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#4b5563"),
    )
    style_bold = ParagraphStyle(
        "InvBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#111827"),
    )
    style_cell = ParagraphStyle(
        "InvCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor("#111827"),
    )
    style_cell_right = ParagraphStyle(
        "InvCellRight",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
        alignment=2,
        textColor=colors.HexColor("#111827"),
    )

    story = []

    # 1. Header: Factory Brand & Tax Invoice Banner
    header_data = [
        [
            Paragraph("<b>BLINE</b><br/><font size='8'>SNACKS MANUFACTURING ERP</font>", style_title),
            Paragraph(
                "<font size='14'><b>TAX INVOICE</b></font><br/>"
                f"<font size='8.5'>Invoice No: <b>{invoice_data.get('invoice_number', 'N/A')}</b><br/>"
                f"Date: <b>{invoice_data.get('invoice_date', 'N/A')}</b><br/>"
                f"Place of Supply: <b>{invoice_data.get('customer_state', 'Tamil Nadu')}</b></font>",
                style_cell_right,
            ),
        ]
    ]
    t_header = Table(header_data, colWidths=[3.5 * inch, 4.0 * inch])
    t_header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t_header)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d1d5db"), spaceAfter=10))

    # 2. Parties: Factory Details vs Customer Details
    factory_info = (
        "<b>FACTORY DETAILS:</b><br/>"
        "BLine Snacks Unit 1<br/>"
        "Plot 14-B, SIDCO Industrial Estate, Guindy<br/>"
        "Chennai, Tamil Nadu - 600032<br/>"
        "GSTIN: <b>33AAAAF0000A1Z5</b><br/>"
        "State: Tamil Nadu (Code: 33)"
    )
    customer_info = (
        "<b>BILLED & SHIPPED TO:</b><br/>"
        f"<b>{invoice_data.get('customer_name', 'Customer')}</b><br/>"
        f"{invoice_data.get('customer_address', 'Address')}<br/>"
        f"State: {invoice_data.get('customer_state', 'Tamil Nadu')}<br/>"
        f"GSTIN: <b>{invoice_data.get('customer_gstin') or 'Unregistered / Composition'}</b><br/>"
        f"Order Ref: {invoice_data.get('order_id', 'N/A')}"
    )

    parties_table = Table(
        [[Paragraph(factory_info, style_sub), Paragraph(customer_info, style_sub)]],
        colWidths=[3.75 * inch, 3.75 * inch],
    )
    parties_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(parties_table)
    story.append(Spacer(1, 12))

    # 3. Line Items Table
    is_intra = invoice_data.get("is_intra_state", True)

    if is_intra:
        table_headers = [
            Paragraph("<b>#</b>", style_bold),
            Paragraph("<b>Item Description</b>", style_bold),
            Paragraph("<b>HSN</b>", style_bold),
            Paragraph("<b>Qty</b>", style_bold),
            Paragraph("<b>Rate</b>", style_bold),
            Paragraph("<b>Taxable</b>", style_bold),
            Paragraph("<b>CGST (2.5%)</b>", style_bold),
            Paragraph("<b>SGST (2.5%)</b>", style_bold),
            Paragraph("<b>Total (INR)</b>", style_bold),
        ]
        col_widths = [0.3 * inch, 2.0 * inch, 0.7 * inch, 0.5 * inch, 0.6 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 1.0 * inch]
    else:
        table_headers = [
            Paragraph("<b>#</b>", style_bold),
            Paragraph("<b>Item Description</b>", style_bold),
            Paragraph("<b>HSN</b>", style_bold),
            Paragraph("<b>Qty</b>", style_bold),
            Paragraph("<b>Rate</b>", style_bold),
            Paragraph("<b>Taxable</b>", style_bold),
            Paragraph("<b>IGST (5.0%)</b>", style_bold),
            Paragraph("<b>Total (INR)</b>", style_bold),
        ]
        col_widths = [0.3 * inch, 2.5 * inch, 0.8 * inch, 0.6 * inch, 0.7 * inch, 0.9 * inch, 0.8 * inch, 1.1 * inch]

    table_rows = [table_headers]

    items = invoice_data.get("items", [])
    for idx, it in enumerate(items, start=1):
        name_desc = f"<b>{it.get('name', 'Product')}</b> ({it.get('pack_size', '200g')})"
        hsn = str(it.get("hsn_code", "19059040"))
        qty = str(it.get("quantity", 0))
        rate = f"{it.get('unit_price', 0.0):.2f}"
        taxable = f"{it.get('taxable_value', 0.0):.2f}"
        total = f"{it.get('total_amount', 0.0):.2f}"

        if is_intra:
            cgst = f"{it.get('cgst_amount', 0.0):.2f}"
            sgst = f"{it.get('sgst_amount', 0.0):.2f}"
            row = [
                Paragraph(str(idx), style_cell),
                Paragraph(name_desc, style_cell),
                Paragraph(hsn, style_cell),
                Paragraph(qty, style_cell_right),
                Paragraph(rate, style_cell_right),
                Paragraph(taxable, style_cell_right),
                Paragraph(cgst, style_cell_right),
                Paragraph(sgst, style_cell_right),
                Paragraph(total, style_cell_right),
            ]
        else:
            igst = f"{it.get('igst_amount', 0.0):.2f}"
            row = [
                Paragraph(str(idx), style_cell),
                Paragraph(name_desc, style_cell),
                Paragraph(hsn, style_cell),
                Paragraph(qty, style_cell_right),
                Paragraph(rate, style_cell_right),
                Paragraph(taxable, style_cell_right),
                Paragraph(igst, style_cell_right),
                Paragraph(total, style_cell_right),
            ]
        table_rows.append(row)

    items_table = Table(table_rows, colWidths=col_widths)
    items_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#141e28")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, 0), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    # Fix header text colors to white
    for c in range(len(table_headers)):
        items_table.setStyle(TableStyle([("TEXTCOLOR", (c, 0), (c, 0), colors.white)]))

    story.append(items_table)
    story.append(Spacer(1, 10))

    # 4. Summary / Total Block
    taxable_sum = f"INR {invoice_data.get('total_taxable_value', 0.0):,.2f}"
    cgst_sum = f"INR {invoice_data.get('total_cgst', 0.0):,.2f}"
    sgst_sum = f"INR {invoice_data.get('total_sgst', 0.0):,.2f}"
    igst_sum = f"INR {invoice_data.get('total_igst', 0.0):,.2f}"
    grand_total = f"INR {invoice_data.get('total_amount', 0.0):,.2f}"

    if is_intra:
        summary_data = [
            ["Total Taxable Value:", taxable_sum],
            ["Central GST (CGST 2.5%):", cgst_sum],
            ["State GST (SGST 2.5%):", sgst_sum],
            ["Total Invoice Amount (INR):", grand_total],
        ]
    else:
        summary_data = [
            ["Total Taxable Value:", taxable_sum],
            ["Integrated GST (IGST 5.0%):", igst_sum],
            ["Total Invoice Amount (INR):", grand_total],
        ]

    summary_table = Table(summary_data, colWidths=[2.5 * inch, 1.8 * inch])
    summary_table.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#141e28")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
        ])
    )

    # Place summary right-aligned
    wrapper_table = Table([["", summary_table]], colWidths=[3.2 * inch, 4.3 * inch])
    story.append(wrapper_table)
    story.append(Spacer(1, 20))

    # 5. Statutory Notes and Signatory
    legal_text = (
        "<b>Statutory Declarations:</b><br/>"
        "1. We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.<br/>"
        "2. All disputes are subject to Chennai jurisdiction.<br/>"
        f"3. Payment Status: <b>{invoice_data.get('payment_status', 'Pending')}</b>"
    )
    sig_text = (
        "For <b>BLine Snacks Unit 1</b><br/><br/><br/>"
        "____________________________________<br/>"
        "Authorised Signatory"
    )
    footer_table = Table(
        [[Paragraph(legal_text, style_sub), Paragraph(sig_text, style_cell_right)]],
        colWidths=[4.8 * inch, 2.7 * inch],
    )
    footer_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(footer_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
