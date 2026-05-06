import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

# Color Scheme
DARK_HEADER = colors.HexColor("#2C2C2C")
BRAND_GOLD = colors.HexColor("#B89B72")
BORDER_COLOR = colors.HexColor("#CCCCCC")
LIGHT_ROW = colors.HexColor("#F9F9F9")
TEXT_DARK = colors.HexColor("#333333")
TEXT_GREY = colors.HexColor("#777777")
WHITE = colors.white

def amount_to_words(number):
    """Converts a number to Indian Rupees in words."""
    if number == 0:
        return "Zero Rupees Only"
    
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def fetch_words(n):
        if n < 20:
            return units[int(n)]
        elif n < 100:
            return tens[int(n // 10)] + (" " + units[int(n % 10)] if (n % 10 != 0) else "")
        elif n < 1000:
            return units[int(n // 100)] + " Hundred" + (" and " + fetch_words(n % 100) if (n % 100 != 0) else "")
        elif n < 100000: # Thousands
            return fetch_words(n // 1000) + " Thousand" + (" " + fetch_words(n % 1000) if (n % 1000 != 0) else "")
        elif n < 10000000: # Lakhs
            return fetch_words(n // 100000) + " Lakh" + (" " + fetch_words(n % 100000) if (n % 100000 != 0) else "")
        else: # Crores
            return fetch_words(n // 10000000) + " Crore" + (" " + fetch_words(n % 10000000) if (n % 10000000 != 0) else "")

    rupees = int(number)
    paise = int(round((number - rupees) * 100))
    
    res = fetch_words(rupees) + " Rupees"
    if paise > 0:
        res += " and " + fetch_words(paise) + " Paise"
    
    return res + " Only"

def generate_order_receipt(order_data: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=25,
        leftMargin=25,
        topMargin=25,
        bottomMargin=25,
        title=f"Tax Invoice - {order_data.get('_id', 'Order')}"
    )

    styles = getSampleStyleSheet()
    
    # Custom Styles
    styles.add(ParagraphStyle(
        name='BrandLogo',
        fontSize=32,
        textColor=BRAND_GOLD,
        fontName='Helvetica-Bold',
        leading=34,
        alignment=2, # Right
        spaceAfter=10
    ))
    
    styles.add(ParagraphStyle(
        name='InvoiceTitle',
        fontSize=10,
        textColor=TEXT_DARK,
        fontName='Helvetica-Bold',
        leading=12,
        alignment=2 # Right
    ))
    
    styles.add(ParagraphStyle(
        name='SupportText',
        fontSize=8,
        textColor=TEXT_DARK,
        alignment=2,
        spaceBefore=2
    ))

    styles.add(ParagraphStyle(
        name='HeaderLabel',
        fontSize=9,
        textColor=TEXT_DARK,
        fontName='Helvetica-Bold',
        spaceAfter=2
    ))

    styles.add(ParagraphStyle(
        name='HeaderText',
        fontSize=8,
        textColor=TEXT_DARK,
        leading=11
    ))

    styles.add(ParagraphStyle(
        name='BarText',
        fontSize=10,
        textColor=WHITE,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='TableHead',
        fontSize=8,
        textColor=WHITE,
        fontName='Helvetica-Bold',
        alignment=1 # Center
    ))

    styles.add(ParagraphStyle(
        name='TableCell',
        fontSize=8,
        textColor=TEXT_DARK,
        alignment=1 # Center
    ))

    styles.add(ParagraphStyle(
        name='ItemName',
        fontSize=8,
        textColor=TEXT_DARK,
        fontName='Helvetica-Bold',
        alignment=0 # Left
    ))

    styles.add(ParagraphStyle(
        name='ItemSub',
        fontSize=7,
        textColor=TEXT_GREY,
        alignment=0 # Left
    ))

    elements = []

    # --- 1. Header Section (Two Column Header) ---
    seller_info = [
        Paragraph("Seller/Consignor:", styles['HeaderLabel']),
        Paragraph("<b>URBANWEAR</b>", styles['HeaderText']),
        Paragraph("Shop No. 12, Fashion Street, Surat, Gujarat - 395003", styles['HeaderText']),
        Paragraph("GSTIN: 24AABCU1234F1ZX", styles['HeaderText'])
    ]
    
    brand_section = [
        Paragraph("URBANWEAR", styles['BrandLogo']),
        Paragraph("Tax Invoice — Original for Recipient", styles['InvoiceTitle']),
        Paragraph("Customer support: support@urbanwear.com", styles['SupportText'])
    ]

    header_table = Table([[seller_info, brand_section]], colWidths=[300, 245])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('RIGHTPADDING', (0,0), (0,0), 20),
        ('LEFTPADDING', (1,0), (1,0), 20),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    # --- 2. Recipient & Ship From Section ---
    shipping = order_data.get('shippingAddress') or order_data.get('shipping') or {}
    cust_name = shipping.get('fullName') or shipping.get('name', 'Customer')
    cust_addr = shipping.get('address', '')
    cust_city = shipping.get('city', '')
    cust_state = shipping.get('state', '')
    cust_pincode = shipping.get('zipCode') or shipping.get('postalCode', '')
    cust_mobile = shipping.get('phone', 'N/A')

    recipient_box = [
        Paragraph("Recipient Address:", styles['HeaderLabel']),
        Paragraph(f"<b>{cust_name}</b>", styles['HeaderText']),
        Paragraph(f"{cust_addr}, {cust_city},", styles['HeaderText']),
        Paragraph(f"{cust_state}, {cust_pincode}", styles['HeaderText']),
        Paragraph(f"Mobile: {cust_mobile}", styles['HeaderText'])
    ]

    ship_from_box = [
        Paragraph("Ship From Address:", styles['HeaderLabel']),
        Paragraph("<b>URBANWEAR WAREHOUSE</b>", styles['HeaderText']),
        Paragraph("Surat, Gujarat", styles['HeaderText'])
    ]

    addr_table = Table([[recipient_box, ship_from_box]], colWidths=[272, 272])
    addr_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEAFTER', (0,0), (0,0), 0.5, BORDER_COLOR),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(addr_table)

    # --- 3. Order Metadata Bar (Dark Bar) ---
    order_id = str(order_data.get('_id', 'N/A'))
    pay_method = order_data.get('paymentMethod', 'N/A').upper()
    
    order_bar_data = [[
        Paragraph(f"ORDER: {order_id}", styles['BarText']),
        Paragraph(f"Mode of Payment: {pay_method}", styles['BarText'])
    ]]
    order_bar = Table(order_bar_data, colWidths=[350, 195])
    order_bar.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_HEADER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(order_bar)
    elements.append(Spacer(1, 10))

    # --- 4. Item Details Table ---
    item_header = [
        Paragraph("Item Details", styles['TableHead']),
        Paragraph("HSN Code", styles['TableHead']),
        Paragraph("Item Qty", styles['TableHead']),
        Paragraph("Unit Price (Rs.)", styles['TableHead']),
        Paragraph("Discount (Rs.)", styles['TableHead']),
        Paragraph("Net Price", styles['TableHead']),
        Paragraph("Tax Amount", styles['TableHead']),
        Paragraph("Total (Rs.)", styles['TableHead'])
    ]
    
    items_table_data = [item_header]
    
    products = order_data.get('products') or order_data.get('items') or []
    total_tax_overall = 0
    total_invoice_value = 0
    
    for i, item in enumerate(products):
        p_name = item.get('productName', 'Product')
        size = item.get('size', 'N/A')
        qty = int(item.get('quantity', 1))
        original_price = float(item.get('originalPrice') or item.get('price', 0))
        net_price_unit = float(item.get('price', 0)) # Price after discount
        
        discount_total = (original_price - net_price_unit) * qty
        net_price_total = net_price_unit * qty
        tax_amount = net_price_total * 0.18 # 18% IGST
        line_total = net_price_total + tax_amount
        
        total_tax_overall += tax_amount
        total_invoice_value += line_total

        item_desc = [
            Paragraph(p_name, styles['ItemName']),
            Paragraph(f"Size: {size}", styles['ItemSub'])
        ]

        row = [
            item_desc,
            Paragraph("61091000", styles['TableCell']),
            Paragraph(str(qty), styles['TableCell']),
            Paragraph(f"{original_price:.2f}", styles['TableCell']),
            Paragraph(f"{discount_total:.2f}", styles['TableCell']),
            Paragraph(f"{net_price_total:.2f}", styles['TableCell']),
            Paragraph(f"{tax_amount:.2f}", styles['TableCell']),
            Paragraph(f"{line_total:.2f}", styles['TableCell'])
        ]
        items_table_data.append(row)

    # Styles for item table
    item_table_widths = [160, 60, 45, 65, 60, 60, 45, 50]
    items_table = Table(items_table_data, colWidths=item_table_widths, repeatRows=1)
    
    item_styles = [
        ('BACKGROUND', (0,0), (-1,0), DARK_HEADER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]
    
    # Alternating rows
    for i in range(1, len(items_table_data)):
        bg_color = WHITE if i % 2 != 0 else LIGHT_ROW
        item_styles.append(('BACKGROUND', (0, i), (-1, i), bg_color))
        
    items_table.setStyle(TableStyle(item_styles))
    elements.append(items_table)
    elements.append(Spacer(1, 15))

    # --- 5. Tax Summary Table ---
    tax_summary_head = [
        Paragraph("HSN Code", styles['TableHead']),
        Paragraph("CGST (Rate% + Amt)", styles['TableHead']),
        Paragraph("SGST (Rate% + Amt)", styles['TableHead']),
        Paragraph("IGST (Rate% + Amt)", styles['TableHead']),
        Paragraph("Cess", styles['TableHead']),
        Paragraph("Total Tax Value", styles['TableHead'])
    ]
    
    tax_summary_data = [
        tax_summary_head,
        [
            Paragraph("61091000", styles['TableCell']),
            Paragraph("0% (0.00)", styles['TableCell']),
            Paragraph("0% (0.00)", styles['TableCell']),
            Paragraph(f"18% ({total_tax_overall:.2f})", styles['TableCell']),
            Paragraph("0.00", styles['TableCell']),
            Paragraph(f"{total_tax_overall:.2f}", styles['TableCell'])
        ]
    ]
    
    tax_table = Table(tax_summary_data, colWidths=[100, 100, 100, 110, 50, 85])
    tax_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), DARK_HEADER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    
    elements.append(Paragraph("<b>Tax Summary</b>", styles['HeaderText']))
    elements.append(Spacer(1, 5))
    elements.append(tax_table)
    elements.append(Spacer(1, 15))

    # --- 6. Totals & Shipping Info ---
    total_words = amount_to_words(total_invoice_value)
    awb_number = order_id[-10:] if len(order_id) >= 10 else order_id.zfill(10)

    totals_data = [
        [Paragraph(f"Total Tax: <b>Rs. {total_tax_overall:.2f}</b>", styles['HeaderText']), ""],
        [Paragraph(f"Total Invoice Value: <b>Rs. {total_invoice_value:.2f}</b>", styles['HeaderText'].clone('TotalIn', fontSize=10, fontName='Helvetica-Bold')), ""],
        [Paragraph(f"Total in Words: {total_words}", styles['HeaderText']), ""],
        [Paragraph(f"Carrier Name: <b>ECOM</b>", styles['HeaderText']), Paragraph(f"AWB Number: <b>{awb_number}</b>", styles['InvoiceTitle'].clone('AWB', alignment=2))]
    ]
    
    totals_table = Table(totals_data, colWidths=[350, 195])
    totals_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('SPAN', (0,0), (1,0)),
        ('SPAN', (0,1), (1,1)),
        ('SPAN', (0,2), (1,2)),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 25))

    # --- 7. Footer (Terms & Signatory) ---
    terms = [
        Paragraph("1. Products are for personal consumption and not for re-sale.", styles['ItemSub']),
        Paragraph("E. & O.E.", styles['ItemSub'])
    ]
    
    # Signature image loading
    sig_path = os.path.join("backend", "static", "signature.png")
    auth_box = [Paragraph("<b>For URBANWEAR</b>", styles['HeaderText'])]
    
    if os.path.exists(sig_path):
        try:
            sig_img = Image(sig_path, width=80, height=40)
            auth_box.append(sig_img)
        except:
            pass
    
    auth_box.append(Paragraph("Authorised Signatory", styles['ItemSub']))

    footer_table = Table([[terms, auth_box]], colWidths=[350, 195])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(footer_table)
    
    # Regd Office & Page Info
    elements.append(Spacer(1, 40))
    regd_office = "Regd. Office: Shop No. 12, Fashion Street, Surat, Gujarat - 395003 | www.urbanwear.com"
    elements.append(Paragraph(regd_office, styles['ItemSub'].clone('Regd', alignment=1)))
    elements.append(Paragraph("Page 1 of 1", styles['ItemSub'].clone('Page', alignment=2)))

    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    return buffer
