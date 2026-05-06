import requests
import sys

BASE_URL = "http://127.0.0.1:5000/api/v1"

def test_admin_auth_flow():
    print("--- Testing Admin AUTH Flow (OTP) ---")
    
    email = "testadmin@urbanwear.com"
    password = "password123"
    
    # Step 1: Send OTP
    print(f"\n1. Sending OTP for {email}...")
    login_payload = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/admin-send-otp", json=login_payload)
        print(f"Status Code: {response.status_code}")
        resp_json = response.json()
        print(f"Response: {resp_json}")
        
        if response.status_code != 200:
            print("FAILED: /admin-send-otp did not return 200")
            return
            
        otp = resp_json.get("debug_otp")
        if not otp:
            print("FAILED: No debug_otp found in response. Is the server running the latest code?")
            return
            
        print(f"SUCCESS: Received debug OTP: {otp}")
        
    except Exception as e:
        print(f"ERROR calling /admin-send-otp: {e}")
        return

    # Step 2: Verify OTP
    print(f"\n2. Verifying OTP {otp} for {email}...")
    verify_payload = {
        "email": email,
        "otp": otp
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/admin-verify-otp", json=verify_payload)
        print(f"Status Code: {response.status_code}")
        resp_json = response.json()
        print(f"Response: {resp_json}")
        
        if response.status_code == 200 and resp_json.get("success"):
            print("SUCCESS: Admin login complete. JWT token received.")
            token = resp_json.get("data", {}).get("token")
            if token:
                print(f"Token (First 20 chars): {token[:20]}...")
        else:
            print(f"FAILED: Verification failed. Message: {resp_json.get('message')}")
            
    except Exception as e:
        print(f"ERROR calling /admin-verify-otp: {e}")

if __name__ == "__main__":
    test_admin_auth_flow()
