from main import app
import traceback

client = app.test_client()
try:
    response = client.options('/api/auth/register', headers={'Origin': 'http://localhost:5174', 'Access-Control-Request-Method': 'POST'})
    print(f"Status: {response.status_code}")
    print(f"Headers: {response.headers}")
except Exception as e:
    print("CRASH REASON ============================")
    traceback.print_exc()

print("\n\nTESTING POST...")
try:
    response = client.post('/api/auth/register', json={"email": "test@test.com"})
    print(f"Status: {response.status_code}")
except Exception as e:
    print("CRASH REASON ============================")
    traceback.print_exc()
