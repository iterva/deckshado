import requests
base = "https://iterva.pythonanywhere.com/api/cards/"
params_list = [
    {"edition": "aydv", "search": "lucifer", "page_size": 5},
    {"edition": "aydv", "search": "semyazza", "page_size": 5},
    {"edition": "aydv", "search": "fuego purificador", "page_size": 5},
]
for params in params_list:
    r = requests.get(base, params=params, timeout=30)
    print("QUERY", params, "status", r.status_code)
    data = r.json()
    items = data.get("results", data if isinstance(data, list) else [])
    for it in items[:3]:
        print(it.get("edid"), "|", it.get("name"), "|", it.get("image_url"))
    print("---")
