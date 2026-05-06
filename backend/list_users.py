from database import users_col
import json

def list_users():
    users = users_col.find().limit(5)
    for user in users:
        print(f"Email: {user.get('email')}, Role: {user.get('role')}")

if __name__ == "__main__":
    list_users()
