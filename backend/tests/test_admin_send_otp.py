
import requests

url = "http://127.0.0.1:5001/api/v1/auth/admin-send-otp"
payload = {
    "email": "testadmin@example.com",
    "password": "admin123"
}

try:
    print(f"Calling {url}...")
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
