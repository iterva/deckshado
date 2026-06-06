import requests
import json

body = {
    "algorithm": "",
    "from": 0,
    "size": 10,
    "filters": {
        "term": {
            "productLineName": ["riftbound-league-of-legends-trading-card-game"],
        },
        "range": {},
        "match": {},
    },
    "listingSearch": {
        "filters": {
            "term": {"sellerStatus": "Live", "channelId": 0},
            "range": {"quantity": {"gte": 1}},
            "exclude": {"channelExclusion": 0},
        },
    },
    "context": {"cart": {}, "shippingCountry": "US"},
    "settings": {"useFuzzySearch": True, "didYouMean": {}},
    "sort": {},
}

headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

for card in ["Brazen Buccaneer", "Pouty Poro", "Yasuo, Unforgiven"]:
    url = f"https://mp-search-api.tcgplayer.com/v1/search/request?q={card.replace(' ', '+')}&isList=false"
    resp = requests.post(url, json=body, headers=headers, timeout=10)
    data = resp.json()
    results = data.get("results", [{}])[0].get("results", [])
    print(f"\n=== {card} === ({len(results)} results)")
    for r in results[:3]:
        print(f"  {r.get('productName')} | mkt=${r.get('marketPrice')} | low=${r.get('lowPrice')} | id={r.get('productId')}")
