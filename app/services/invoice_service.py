import io

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

GREEN = colors.HexColor("#1F6D3C")
GREEN_DEEP = colors.HexColor("#123420")
RED = colors.HexColor("#B3261E")
INK = colors.HexColor("#22261F")
MUTED = colors.HexColor("#565C51")
LINE = colors.HexColor("#E3E0D2")
PAPER = colors.HexColor("#FBF8F0")


def generate_invoice_pdf(order):
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                          leftMargin=16 * mm, rightMargin=16 * mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=GREEN_DEEP, fontSize=20, spaceAfter=2)
    small = ParagraphStyle("small", parent=styles["Normal"], textColor=MUTED, fontSize=9, leading=13)
    right = ParagraphStyle("right", parent=small, alignment=TA_RIGHT)
    label = ParagraphStyle("label", parent=styles["Normal"], textColor=GREEN_DEEP, fontSize=10, leading=14,
                           fontName="Helvetica-Bold")
    body = ParagraphStyle("body", parent=styles["Normal"], textColor=INK, fontSize=10, leading=14)

    company = current_app.config
    story = []

    header_tbl = Table([[
        Paragraph(f"<b>{company['COMPANY_NAME'].upper()}</b><br/><font size=8 color='#565C51'>"
                 f"The True Taste of Tradition</font>", h1),
        Paragraph(f"<b>TAX INVOICE</b><br/>Invoice #: {order.invoice_number or '—'}<br/>"
                 f"Date: {order.updated_at.strftime('%d %b %Y')}<br/>Order #: {order.order_number}", right),
    ]], colWidths=[100 * mm, 74 * mm])
    header_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(header_tbl)
    story.append(Spacer(1, 4))
    story.append(Table([[""]], colWidths=[174 * mm], rowHeights=[1],
                       style=TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1.2, GREEN)])))
    story.append(Spacer(1, 10))

    company_block = Paragraph(
        f"<b>{company['COMPANY_NAME']}</b><br/>Manufactured by Prashanth Home Industries<br/>"
        f"{company['COMPANY_ADDRESS']}<br/>Phone: {company['COMPANY_PHONE']} | Email: {company['COMPANY_EMAIL']}"
        + (f"<br/>GSTIN: {company['COMPANY_GSTIN']}" if company.get("COMPANY_GSTIN") else ""), small)

    bill_to = Paragraph(
        f"<b>BILL TO / SHIP TO</b><br/>{order.customer_name}<br/>"
        f"{(order.shipping_address or '').replace(chr(10), '<br/>')}<br/>"
        f"Phone: {order.customer_phone or '—'}"
        + (f"<br/>Company: {order.company_name}" if order.company_name else "")
        + (f"<br/>GSTIN: {order.gst_number}" if order.gst_number else ""), small)

    info_tbl = Table([[company_block, bill_to]], colWidths=[87 * mm, 87 * mm])
    info_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                  ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                                  ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                                  ("PADDING", (0, 0), (-1, -1), 8)]))
    story.append(info_tbl)
    story.append(Spacer(1, 14))

    data = [["Product", "SKU", "Pack", "Qty", "Unit Price", "GST", "Total"]]
    for item in order.items:
        data.append([
            Paragraph(item.product_name, body), item.sku, item.variant_label, str(item.quantity),
            f"Rs {item.unit_price:.2f}", f"{item.gst_percentage}%", f"Rs {(item.subtotal + item.tax):.2f}",
        ])
    items_tbl = Table(data, colWidths=[52 * mm, 24 * mm, 16 * mm, 12 * mm, 24 * mm, 14 * mm, 32 * mm], repeatRows=1)
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN_DEEP),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 10))

    totals = [
        ["Subtotal", f"Rs {order.subtotal:.2f}"],
        ["Discount", f"- Rs {order.discount:.2f}"],
        ["GST", f"Rs {order.tax:.2f}"],
        ["Shipping", f"Rs {order.shipping_charge:.2f}"],
        ["Grand Total", f"Rs {order.total_amount:.2f}"],
    ]
    totals_tbl = Table(totals, colWidths=[40 * mm, 34 * mm])
    totals_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, GREEN),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), GREEN_DEEP),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    wrapper = Table([[None, totals_tbl]], colWidths=[100 * mm, 74 * mm])
    story.append(wrapper)
    story.append(Spacer(1, 14))

    status_color = "#1F6D3C" if order.is_paid else "#B3261E"
    status_text = "PAID" if order.is_paid else ("PAY ON DELIVERY" if order.payment_method == "COD" else "PAYMENT PENDING")
    story.append(Paragraph(f"<b>Payment Status:</b> <font color='{status_color}'>{status_text}</font> "
                           f"&nbsp;|&nbsp; <b>Payment Method:</b> {order.payment_method}", body))
    story.append(Spacer(1, 24))
    story.append(Paragraph("Thank you for choosing Maagi Pickle.", ParagraphStyle(
        "thanks", parent=styles["Normal"], alignment=1, textColor=GREEN_DEEP, fontSize=12, fontName="Helvetica-Bold")))
    story.append(Paragraph("This is a computer-generated invoice and does not require a signature.", small))

    doc.build(story)
    buf.seek(0)
    return buf
