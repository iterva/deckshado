import requests, time, json

all_cards = []
page = 1
while True:
    resp = requests.get('https://api.riftcodex.com/cards', params={'page': page, 'size': 50}, timeout=30)
    data = resp.json()
    all_cards.extend(data['items'])
    print(f"  Pagina {page}/{data['pages']}")
    if page >= data['pages']:
        break
    page += 1
    time.sleep(0.3)

with open('riftcodex_all_cards.json', 'w', encoding='utf-8') as f:
    json.dump(all_cards, f, ensure_ascii=False)
print(f"Guardado: {len(all_cards)} cartas en riftcodex_all_cards.json")
