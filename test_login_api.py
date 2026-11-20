"""Test the login API endpoint directly"""
import urllib.request
import urllib.parse
import json

BASE_URL = "http://localhost:5000"

# Test login
def test_login(email, password):
    url = BASE_URL + "/api/auth/login"
    data = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
            print(f"Login {email}: SUCCESS - {body}")
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        print(f"Login {email}: FAIL {e.code} - {body}")

test_login("demo@blindguide.local", "Demo@123")
test_login("demo@blindguide.local", "wrongpassword")

# Test registration then login
print("\n--- Register new test user ---")
url = BASE_URL + "/api/auth/register"
data = json.dumps({"full_name": "Test User", "email": "logintest@test.com", "password": "Test@1234"}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
try:
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
        print(f"Register: {body}")
except urllib.error.HTTPError as e:
    body = json.loads(e.read())
    print(f"Register failed: {e.code} - {body}")

test_login("logintest@test.com", "Test@1234")
