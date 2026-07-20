import unicodedata
from collections import defaultdict

from cards.models import Card, Edition


def norm(s):
    s = (s or '').strip().lower()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return ' '.join(s.split())


ed = Edition.objects.filter(slug='aydv').first()
if not ed:
    print('ERROR: no existe edicion aydv')
    raise SystemExit(1)

rows = []
for c in Card.objects.filter(edition=ed).select_related('rarity').order_by('name', 'id'):
    rslug = c.rarity.slug if c.rarity else ''
    if rslug in {'secreta', 'ultra-real', 'mega-real', 'legendaria'}:
        rows.append({
            'id': c.id,
            'name': c.name,
            'name_norm': norm(c.name),
            'rarity': rslug,
            'edid': c.edid,
            'myl_id': c.myl_id,
            'url': c.custom_image_url or '',
        })

by = defaultdict(list)
for r in rows:
    by[r['name_norm']].append(r)

focus = []
for k, vals in sorted(by.items()):
    rar = {v['rarity'] for v in vals}
    if 'secreta' in rar and ('ultra-real' in rar or 'mega-real' in rar or 'legendaria' in rar):
        focus.append((k, vals))

print(f'Total grupos secreta + no-secreta: {len(focus)}')
for k, vals in focus:
    print(f"\n== {k} ==")
    for v in sorted(vals, key=lambda x: (x['rarity'], str(x['edid']))):
        print(f" - {v['rarity']:11} | edid={v['edid']:<12} | name={v['name']:<24} | myl_id={v['myl_id']}")
        print(f"   url={v['url']}")

print('\nCheck puntual satanas/semyazza:')
for k in ['satanas', 'semyazza']:
    vals = by.get(k, [])
    print(f'[{k}] {len(vals)} filas')
    for v in sorted(vals, key=lambda x: (x['rarity'], str(x['edid']))):
        print(f" - {v['rarity']:11} | edid={v['edid']:<12} | name={v['name']:<24} | myl_id={v['myl_id']}")
        print(f"   url={v['url']}")
