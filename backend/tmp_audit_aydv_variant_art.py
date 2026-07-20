import os, hashlib, requests, unicodedata, re
os.environ.setdefault('DJANGO_SETTINGS_MODULE','backend.settings')
import django
django.setup()
from cards.models import Card, Edition

API_ENDPOINT='https://api.myl.cl/cards/edition/ayd_vigilantes'
API_CDN_BASE='https://api.myl.cl/static/cards/166'
TARGET={'legendaria','secreta','ultra-real','mega-real'}

def norm(t):
    v=(t or '').strip().replace('�','')
    v=unicodedata.normalize('NFKD', v)
    v=''.join(ch for ch in v if not unicodedata.combining(ch))
    v=v.lower()
    v=re.sub(r'[^a-z0-9]+',' ',v)
    return re.sub(r'\s+',' ',v).strip()

def h(url):
    r=requests.get(url,timeout=30)
    r.raise_for_status()
    return hashlib.sha256(r.content).hexdigest(), r.headers.get('content-type','')

payload=requests.get(API_ENDPOINT,timeout=40).json()
rarity_by_id={str(x.get('id')):str(x.get('slug') or '').strip().lower() for x in payload.get('rarities',[]) if isinstance(x,dict)}
api_cards=payload.get('cards',[])
api_idx={}
for c in api_cards:
    name=norm(c.get('name'))
    rslug=rarity_by_id.get(str(c.get('rarity')),'')
    edid=str(c.get('edid') or '').zfill(3)
    if name and rslug in TARGET and edid.isdigit():
        api_idx[(name,rslug)] = edid

edition=Edition.objects.get(slug='aydv')
cards=(Card.objects.filter(edition=edition, rarity__slug__in=list(TARGET))
       .select_related('rarity').order_by('name','id'))

rows=[]
errors=[]
for card in cards:
    key=(norm(card.name), (card.rarity.slug or '').strip().lower())
    exp=api_idx.get(key)
    if not exp:
        errors.append((card.name, card.edid, card.rarity.slug, 'sin_match_api'))
        continue
    cur_url=(card.custom_image_url or '').strip()
    if not cur_url:
        rows.append((card.name, card.edid, card.rarity.slug, exp, 'missing_url'))
        continue
    try:
        hc,_=h(cur_url)
        he,_=h(f"{API_CDN_BASE}/{exp}.png")
        if hc!=he:
            rows.append((card.name, card.edid, card.rarity.slug, exp, 'mismatch'))
    except Exception as e:
        rows.append((card.name, card.edid, card.rarity.slug, exp, f'error:{type(e).__name__}'))

print('TOTAL_TARGET=', cards.count())
print('MISMATCH_OR_ISSUE=', len(rows))
print('NO_API_MATCH=', len(errors))
for r in rows[:120]:
    print('|'.join(map(str,r)))
