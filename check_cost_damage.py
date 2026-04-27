"""
Compare cost/damage from cards_data.json against the MYL API for all editions.
Reports any mismatches.
"""
import json
import requests
import time
import sys

API_BASE = "https://api.myl.cl/cards/edition/"

# Load fixture
with open("backend/cards_data.json", "r", encoding="utf-8") as f:
    fixture = json.load(f)

# Build lookup: edition_pk -> {myl_id, slug}
editions = {}
for item in fixture:
    if item["model"] == "cards.edition":
        editions[item["pk"]] = {
            "myl_id": item["fields"].get("myl_id", ""),
            "slug": item["fields"].get("slug", ""),
        }

# Build card lookup: (edition_slug, edid) -> {name, cost, damage, myl_id, pk}
cards_by_ed = {}
for item in fixture:
    if item["model"] == "cards.card":
        f = item["fields"]
        ed_pk = f["edition"]
        ed_info = editions.get(ed_pk, {})
        ed_slug = ed_info.get("slug", "unknown")
        edid = f["edid"]
        key = (ed_slug, edid)
        cards_by_ed[key] = {
            "name": f["name"],
            "cost": f["cost"],
            "damage": f["damage"],
            "myl_id": f["myl_id"],
            "pk": item["pk"],
        }

# Only check Imperio (imp) editions
IMP_EDITIONS = [
    "kvsm_titanes", "libertadores", "onyria", "toolkit_cenizas_de_fuego",
    "toolkit_hielo_inmortal", "lootbox_2024", "secretos_arcanos", "bestiarium",
    "escuadronmecha", "amenazakaiju", "zodiaco", "espiritu_samurai",
]

ed_slugs = sorted(IMP_EDITIONS)
print(f"Total editions to check: {len(ed_slugs)}")

mismatches = []
errors = []

for i, slug in enumerate(ed_slugs):
    print(f"[{i+1}/{len(ed_slugs)}] Checking {slug}...", end=" ", flush=True)
    try:
        resp = requests.get(f"{API_BASE}{slug}", timeout=15)
        if resp.status_code != 200:
            print(f"HTTP {resp.status_code}")
            errors.append((slug, f"HTTP {resp.status_code}"))
            continue
        data = resp.json()
        api_cards = data.get("cards", [])
        checked = 0
        ed_mismatches = 0
        for ac in api_cards:
            edid = ac["edid"]
            api_cost = ac.get("cost")
            api_damage = ac.get("damage")
            key = (slug, edid)
            local = cards_by_ed.get(key)
            if not local:
                continue
            checked += 1
            local_cost = local["cost"]
            local_damage = local["damage"]
            if str(api_cost or "") != str(local_cost or "") or str(api_damage or "") != str(local_damage or ""):
                ed_mismatches += 1
                mismatches.append({
                    "edition": slug,
                    "edid": edid,
                    "name": local["name"],
                    "pk": local["pk"],
                    "local_cost": local_cost,
                    "local_damage": local_damage,
                    "api_cost": api_cost,
                    "api_damage": api_damage,
                })
        print(f"{checked} cards, {ed_mismatches} mismatches")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append((slug, str(e)))
    time.sleep(0.3)  # Be nice to the API

print("\n" + "="*80)
print(f"TOTAL MISMATCHES: {len(mismatches)}")
print("="*80)
for m in mismatches:
    print(f"  [{m['edition']}] {m['name']} (edid={m['edid']}, pk={m['pk']})")
    print(f"    LOCAL:  cost={m['local_cost']}, damage={m['local_damage']}")
    print(f"    API:    cost={m['api_cost']}, damage={m['api_damage']}")

if errors:
    print(f"\nERRORS ({len(errors)}):")
    for slug, err in errors:
        print(f"  {slug}: {err}")

# Save results
with open("cost_damage_mismatches.json", "w", encoding="utf-8") as f:
    json.dump(mismatches, f, indent=2, ensure_ascii=False)
print(f"\nResults saved to cost_damage_mismatches.json")
