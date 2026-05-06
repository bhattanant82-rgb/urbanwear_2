import sys
import os
import io

# Add backend to sys.path
sys.path.append(os.getcwd())

from backend.services.pdf_service import generate_order_receipt

# Dummy order data
order_data = {
    "_id": "643a2b3c4d5e6f7a8b9c0d1e",
    "paymentMethod": "Credit Card",
    "shippingAddress": {
        "fullName": "Ishan Sharma",
        "address": "R1 Umiyakrupa Society, Navnirman School Road",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "zipCode": "382480",
        "phone": "8000158080"
    },
    "products": [
        {
            "productName": "Genuine Leather Round-Toe Slip-Ons, Black",
            "size": "8",
            "quantity": 1,
            "originalPrice": 2984.95,
            "price": 2078.02
        },
        {
            "productName": "Urban Tech T-Shirt",
            "size": "L",
            "quantity": 2,
            "originalPrice": 1500.00,
            "price": 1200.00
        }
    ]
}

def test_generate_pdf():
    print("Generating PDF...")
    try:
        buffer = generate_order_receipt(order_data)
        output_path = "test_invoice.pdf"
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())
        print(f"PDF generated successfully at {output_path}")
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generate_pdf()
