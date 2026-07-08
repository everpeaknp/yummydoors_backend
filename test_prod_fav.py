import requests
import string
import random

def random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

base_url = "https://yummydoorsapi.everacy.com/api/v1"
email = f"test_{random_string()}@example.com"
password = "TestPassword123!"

print(f"Signing up {email}...")
res = requests.post(
    f"{base_url}/auth/register",
    json={
        "email": email,
        "password": password,
        "full_name": "Test User",
        "phone_number": "9800000000"
    }
)
if res.status_code >= 400:
    print("Signup failed:", res.status_code, res.text)
    exit(1)

print("Logging in...")
res = requests.post(
    f"{base_url}/auth/login",
    json={
        "identifier": email,
        "password": password
    }
)
if res.status_code >= 400:
    print("Login failed:", res.status_code, res.text)
    exit(1)

token = res.json()["data"]["tokens"]["access_token"]
headers = {
    "Authorization": f"Bearer {token}",
    "Origin": "http://localhost:3000"
}

print("Adding favorite...")
res = requests.post(
    f"{base_url}/favorites/menu-items/1",
    headers=headers
)
print("Status:", res.status_code)
print("Headers:", dict(res.headers))
print("Body:", res.text)
