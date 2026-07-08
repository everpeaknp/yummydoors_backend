import requests
res = requests.options(
    "http://127.0.0.1:8002/api/v1/favorites/menu-items/1",
    headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"}
)
print(res.status_code)
print(res.headers)
print(res.text)
