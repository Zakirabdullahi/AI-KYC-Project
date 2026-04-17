import urllib.request

req = urllib.request.Request("http://localhost:8000/api/auth/register", method="OPTIONS", headers={"Origin": "http://localhost:5174", "Access-Control-Request-Method": "POST"})
try:
    resp = urllib.request.urlopen(req)
    print(f"Status: {resp.status}")
    print("Headers:")
    for k, v in resp.getheaders():
        print(f"{k}: {v}")
except Exception as e:
    print(e)
