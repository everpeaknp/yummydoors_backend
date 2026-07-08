import requests

print("Testing OPTIONS to production:")
res = requests.options(
    "https://yummydoorsapi.everacy.com/api/v1/favorites/menu-items/1",
    headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"}
)
print("Status:", res.status_code)
print("Headers:", dict(res.headers))
print("Body:", res.text)
