import urllib.request
import json

base_url = "http://localhost:8002/api"

try:
    req = urllib.request.Request(f"{base_url}/auth/register", data=json.dumps({
        "email": "test99@test.com",
        "password": "password123",
        "full_name": "Test User"
    }).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    res = urllib.request.urlopen(req)
    print("Register:", res.getcode(), res.read().decode())
except Exception as e:
    print("Register err:", e)

try:
    req = urllib.request.Request(f"{base_url}/auth/token", data=json.dumps({
        "email": "test99@test.com",
        "password": "password123"
    }).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    res = urllib.request.urlopen(req)
    data = json.loads(res.read().decode())
    print("Login OK")
    token = data.get("access_token")
    
    req2 = urllib.request.Request(f"{base_url}/users/me", headers={'Authorization': f'Bearer {token}'}, method='GET')
    try:
        res2 = urllib.request.urlopen(req2)
        print("Fetch Me:", res2.getcode(), res2.read().decode())
    except urllib.error.HTTPError as e:
        print("Fetch Me ERROR:", e.code, e.read().decode())
except Exception as e:
    print("Login err:", e)
