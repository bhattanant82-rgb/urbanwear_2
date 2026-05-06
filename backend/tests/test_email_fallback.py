import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.email_service import send_order_confirmation

def test_email_flow():
    load_dotenv()
    
    test_order = {
        "_id": "TEST_ORDER_123",
        "totalAmount": 1999.00,
        "paymentMethod": "COD",
        "createdAt": datetime.now(),
        "products": [
            {
                "productName": "Test Premium Tee",
                "quantity": 1,
                "price": 1999.00,
                "discount": 0,
                "size": "XL"
            }
        ]
    }
    
    test_email = os.getenv("EMAIL_USER") # Sending to self
    print(f"--- Starting Email Test to {test_email} ---")
    
    success = send_order_confirmation(test_email, "Test Developer", test_order)
    
    if success:
        print("\n[SUCCESS] Email function returned True.")
        print("Check your inbox (if SMTP worked) OR check backend/local_emails.log (if it fell back).")
    else:
        print("\n[FAILURE] Email function returned False.")

if __name__ == "__main__":
    test_email_flow()
