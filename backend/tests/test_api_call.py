
import requests

url = "http://127.0.0.1:5001/api/v1/auth/admin-send-otp"
data = {
    "email": "invalidadmin@urbanwear.com",
    "password": "wrongpassword"
}

try:
    print(f"Calling {url} with invalid admin credentials...")
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
