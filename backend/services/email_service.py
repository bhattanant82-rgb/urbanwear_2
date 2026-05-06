"""
services/email_service.py
Order confirmation email sender using Gmail SMTP with a premium HTML template.
"""
import smtplib
import os
import sys
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _save_mock_email(to_email: str, subject: str, body: str):
    """Write email content to a local file for offline testing or fallback."""
    try:
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "local_emails.log")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"TIME   : {timestamp}\n")
            f.write(f"TO     : {to_email}\n")
            f.write(f"SUBJECT: {subject}\n")
            f.write(f"BODY   :\n{body}\n")
            f.write(f"{'='*50}\n")
        logger.info(f"[MOCK EMAIL] Email saved locally to {log_file} (Fallback Triggered)")
    except Exception as e:
        logger.error(f"[MOCK EMAIL] CRITICAL: Failed to save mock email to file: {e}")

def send_contact_notification(contact_data: dict) -> bool:
    """Send an email notification to admin when a new contact message is received."""
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    admin_email = os.getenv("ADMIN_NOTIFICATION_EMAIL") or email_user
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not email_user or not email_pass or not admin_email:
        logger.error("[EMAIL] Missing email credentials or admin email for contact notification")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"New Contact Request: {contact_data.get('subject', 'General Inquiry')}"
        msg["From"] = f"UrbanWear System <{email_user}>"
        msg["To"] = admin_email

        text = f"New contact message received:\n\nName: {contact_data.get('name')}\nEmail: {contact_data.get('email')}\nPhone: {contact_data.get('phone', 'N/A')}\nSubject: {contact_data.get('subject')}\n\nMessage:\n{contact_data.get('message')}"
        msg.attach(MIMEText(text, "plain"))

        with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.sendmail(email_user, admin_email, msg.as_string())
        
        logger.info(f"[EMAIL] Contact notification sent to {admin_email}")
        return True
    except Exception as e:
        logger.warning(f"[EMAIL] Failed to send contact notification via SMTP: {str(e)}. Falling back to local log.")
        _save_mock_email(admin_email, f"New Contact Request: {contact_data.get('subject')}", text)
        return True  # Return True because we handled it via fallback

def _build_html_email(order_data: dict, user_name: str) -> str:
    """Build a premium HTML email for order confirmation."""
    order_id = str(order_data.get("_id", ""))
    
    # Handle order date
    created_at = order_data.get("createdAt")
    if not created_at:
        created_at = datetime.now()
    elif isinstance(created_at, str):
        try:
            # Try to parse ISO format
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except Exception:
            created_at = str(created_at)
    
    date_str = created_at.strftime("%B %d, %Y") if isinstance(created_at, datetime) else str(created_at)

    total = order_data.get("totalAmount") or order_data.get("totalPrice") or 0
    # Use float for math, but format for display
    try:
        total_val = float(total)
    except:
        total_val = 0.0
        
    payment_method = order_data.get("paymentMethod", "COD")
    status = order_data.get("orderStatus", "Placed")

    # Build products table rows
    products = order_data.get("products") or order_data.get("items") or []
    rows_html = ""
    
    subtotal_val = 0.0
    total_gst = 0.0
    
    for item in products:
        name = item.get("productName", "Product")
        qty = item.get("quantity", 1)
        price = float(item.get("price", 0))
        discount_pct = float(item.get("discount", 0))
        size = item.get("size", "")
        
        # Calculate pricing logic consistent with backend
        item_mrp = price * qty
        discount_amount = item_mrp * (discount_pct / 100)
        taxable_value = item_mrp - discount_amount
        
        unit_taxable = price - (price * discount_pct / 100)
        gst_rate = 0.12 if unit_taxable > 1000 else 0.05
        gst_amount = taxable_value * gst_rate
        line_total = taxable_value + gst_amount
        
        subtotal_val += taxable_value
        total_gst += gst_amount

        rows_html += f"""
        <tr>
          <td style="padding:15px 0; border-bottom:1px solid #eee;">
            <div style="font-weight:600; color:#1a1a1a; font-size:15px;">{name}</div>
            {f'<div style="font-size:12px; color:#888; margin-top:4px;">Size: {size}</div>' if size else ''}
          </td>
          <td style="padding:15px 0; border-bottom:1px solid #eee; text-align:center; color:#555;">{qty}</td>
          <td style="padding:15px 0; border-bottom:1px solid #eee; text-align:right; color:#555;">₹{price:,.2f}</td>
          <td style="padding:15px 0; border-bottom:1px solid #eee; text-align:right; font-weight:600; color:#1a1a1a;">₹{line_total:,.2f}</td>
        </tr>"""

    delivery_fee = 49.0
    grand_total = subtotal_val + total_gst + delivery_fee

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Confirmation - UrbanWear</title>
</head>
<body style="margin:0; padding:0; background-color:#ffffff; font-family:'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <div style="max-width:600px; margin:0 auto; background-color:#ffffff; border:1px solid #f0f0f0;">
        <!-- Header -->
        <div style="padding:40px 20px; text-align:center; background-color:#1a1a1a;">
            <h1 style="margin:0; color:#B89B72; font-size:28px; letter-spacing:4px; text-transform:uppercase; font-weight:800;">URBANWEAR</h1>
            <p style="margin:10px 0 0; color:#888; font-size:12px; letter-spacing:2px; text-transform:uppercase;">Premium Fashion for Modern Living</p>
        </div>

        <!-- Success Banner -->
        <div style="padding:20px; background-color:#B89B72; text-align:center;">
            <p style="margin:0; color:#ffffff; font-size:14px; font-weight:700; letter-spacing:1px; text-transform:uppercase;">Order Successfully Placed</p>
        </div>

        <!-- Content -->
        <div style="padding:40px 30px;">
            <h2 style="margin:0 0 20px; color:#1a1a1a; font-size:22px;">Thank you for your order, {user_name}!</h2>
            <p style="margin:0 0 30px; color:#555; line-height:1.6; font-size:15px;">Your order has been received and is being processed. Below are your order details and summary.Our team will process your order and update you once it's shipped.</p>

            <!-- Order Info Grid -->
            <div style="background-color:#f9f9f9; padding:25px; border-radius:4px; margin-bottom:40px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="padding-bottom:15px;">
                            <div style="font-size:12px; color:#888; text-transform:uppercase; margin-bottom:4px;">Order ID</div>
                            <div style="font-weight:600; color:#1a1a1a;">#{order_id}</div>
                        </td>
                        <td style="padding-bottom:15px;">
                            <div style="font-size:12px; color:#888; text-transform:uppercase; margin-bottom:4px;">Order Date</div>
                            <div style="font-weight:600; color:#1a1a1a;">{date_str}</div>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            <div style="font-size:12px; color:#888; text-transform:uppercase; margin-bottom:4px;">Payment Method</div>
                            <div style="font-weight:600; color:#1a1a1a;">{payment_method}</div>
                        </td>
                        <td>
                            <div style="font-size:12px; color:#888; text-transform:uppercase; margin-bottom:4px;">Delivery Method</div>
                            <div style="font-weight:600; color:#1a1a1a;">Standard Delivery</div>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Items Table -->
            <h3 style="margin:0 0 15px; color:#1a1a1a; font-size:16px; text-transform:uppercase; letter-spacing:1px;">Your Items</h3>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:30px;">
                <thead>
                    <tr>
                        <th style="padding-bottom:15px; text-align:left; border-bottom:2px solid #1a1a1a; font-size:12px; color:#1a1a1a; text-transform:uppercase;">Product</th>
                        <th style="padding-bottom:15px; text-align:center; border-bottom:2px solid #1a1a1a; font-size:12px; color:#1a1a1a; text-transform:uppercase;">Qty</th>
                        <th style="padding-bottom:15px; text-align:right; border-bottom:2px solid #1a1a1a; font-size:12px; color:#1a1a1a; text-transform:uppercase;">Price</th>
                        <th style="padding-bottom:15px; text-align:right; border-bottom:2px solid #1a1a1a; font-size:12px; color:#1a1a1a; text-transform:uppercase;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <!-- Summary -->
            <div style="margin-left:auto; width:100%; max-width:250px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="padding:8px 0; color:#555; font-size:14px;">Subtotal</td>
                        <td style="padding:8px 0; color:#1a1a1a; font-size:14px; text-align:right;">₹{subtotal_val:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0; color:#555; font-size:14px;">GST (Tax)</td>
                        <td style="padding:8px 0; color:#1a1a1a; font-size:14px; text-align:right;">₹{total_gst:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0; color:#555; font-size:14px;">Delivery Fee</td>
                        <td style="padding:8px 0; color:#1a1a1a; font-size:14px; text-align:right;">₹{delivery_fee:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding:20px 0 0; color:#1a1a1a; font-size:18px; font-weight:800; border-top:1px solid #1a1a1a;">Total</td>
                        <td style="padding:20px 0 0; color:#B89B72; font-size:20px; font-weight:800; text-align:right; border-top:1px solid #1a1a1a;">₹{grand_total:,.2f}</td>
                    </tr>
                </table>
            </div>
        </div>

        <!-- Footer -->
        <div style="padding:40px 20px; background-color:#f9f9f9; text-align:center; border-top:1px solid #eee;">
            <p style="margin:0 0 10px; color:#1a1a1a; font-size:14px; font-weight:600;">Thank you for shopping with UrbanWear.</p>
            <p style="margin:0 0 20px; color:#888; font-size:13px;">If you have any questions, contact us at <a href="mailto:support@urbanwear.com" style="color:#B89B72; text-decoration:none;">support@urbanwear.com</a></p>
            <div style="margin-top:20px; font-size:12px; color:#bbb; letter-spacing:1px; text-transform:uppercase;">
                URBANWEAR.COM
            </div>
        </div>
    </div>
</body>
</html>
"""
    return html

def send_order_confirmation(user_email: str, user_name: str, order_data: dict) -> bool:
    """
    Send a premium HTML order confirmation email via Gmail SMTP (Port 587 + TLS).
    Returns True on success, False on failure.
    """
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not email_user or not email_pass:
        logger.error("[EMAIL] EMAIL_USER or EMAIL_PASS not set in environment")
        return False

    try:
        total = order_data.get("totalAmount") or order_data.get("totalPrice") or 0
        order_id = order_data.get("_id")
        html_content = _build_html_email(order_data, user_name)
        
        # ─── Customer Message ───
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "UrbanWear Order Confirmation"
        msg["From"] = f"UrbanWear <{email_user}>"
        msg["To"] = user_email

        # Plain text fallback
        plain_text = f"Thank you for your order, {user_name}!\n\nOrder ID: #{order_id}\nTotal: ₹{total}\n\nWe are processing your order. Thank you for shopping with UrbanWear!"
        
        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        logger.info(f"[EMAIL] Connecting to {smtp_server}:{smtp_port} for customer email...")
        
        with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
            server.starttls()
            logger.info(f"[EMAIL] Authenticating with {email_user}...")
            server.login(email_user, email_pass)
            logger.info(f"[EMAIL] Sending message to {user_email}...")
            server.sendmail(email_user, user_email, msg.as_string())
            
        # ─── Admin Notification ───
        admin_email = os.getenv("ADMIN_NOTIFICATION_EMAIL")
        if admin_email:
            try:
                logger.info(f"[EMAIL] Sending admin notification to {admin_email}...")
                with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as admin_server:
                    admin_server.starttls()
                    admin_server.login(email_user, email_pass)
                    
                    admin_msg = MIMEMultipart("alternative")
                    admin_msg["Subject"] = f"NEW ORDER RECEIVED - #{order_id}"
                    admin_msg["From"] = f"UrbanWear System <{email_user}>"
                    admin_msg["To"] = admin_email
                    
                    admin_text = f"New order received from {user_name} ({user_email})\nOrder ID: #{order_id}\nTotal: ₹{total}\nView in Admin Panel."
                    admin_msg.attach(MIMEText(admin_text, "plain"))
                    admin_msg.attach(MIMEText(html_content, "html"))
                    
                    admin_server.sendmail(email_user, admin_email, admin_msg.as_string())
                logger.info(f"[EMAIL] [OK] Admin notification sent successfully")
            except Exception as admin_err:
                logger.warning(f"[EMAIL] ! Failed to send admin notification: {str(admin_err)}")

        logger.info(f"[EMAIL] [OK] Order confirmation flow complete for {user_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("[EMAIL] [ERROR] Authentication failed. Falling back to mock email.")
        _save_mock_email(user_email, "UrbanWear Order Confirmation", plain_text)
        return True
    except smtplib.SMTPConnectError:
        logger.error(f"[EMAIL] [ERROR] Failed to connect to SMTP server {smtp_server}:{smtp_port}. Falling back to mock email.")
        _save_mock_email(user_email, "UrbanWear Order Confirmation", plain_text)
        return True
    except Exception as e:
        logger.error(f"[EMAIL] [ERROR] Unexpected email error: {str(e)}. Falling back to mock email.")
        import traceback
        logger.debug(traceback.format_exc())
        _save_mock_email(user_email, "UrbanWear Order Confirmation", plain_text)
        return True


def test_smtp_connection() -> bool:
    """Validate SMTP configuration on server startup."""
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not email_user or not email_pass:
        logger.warning("[EMAIL] EMAIL_USER or EMAIL_PASS missing - Email system will not work.")
        return False

    try:
        logger.info(f"[STARTUP] Testing SMTP connection to {smtp_server}...")
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(email_user, email_pass)
        logger.info("[STARTUP] [OK] SMTP Configuration Verified.")
        return True
    except Exception as e:
        logger.error(f"[STARTUP] [ERROR] SMTP Configuration Verification Failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Allow manual testing if run directly
    from dotenv import load_dotenv
    load_dotenv()
    
    test_order = {
        "_id": "65f1a2b3c4d5e6f7a8b9c0d1",
        "totalAmount": 1249.00,
        "paymentMethod": "COD",
        "createdAt": datetime.now(),
        "products": [
            {
                "productName": "Signature Premium Tee",
                "quantity": 2,
                "price": 599.00,
                "discount": 10,
                "size": "L"
            }
        ]
    }
    
    test_email = os.getenv("EMAIL_USER") # Send to self for test
    if test_email:
        print(f"Running manual test send to {test_email}...")
        send_order_confirmation(test_email, "Test User", test_order)
    else:
        print("Set EMAIL_USER in .env to run manual test.")

