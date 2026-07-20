import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from cards.models import Edition, Card

edition = Edition.objects.get(slug='aydv')
rows = list(Card.objects.filter(edition=edition).values('id','name','edid','myl_id','custom_image_url'))

total = len(rows)
missing_url = [r for r in rows if not (r['custom_image_url'] or '').strip()]
non_ik = [r for r in rows if (r['custom_image_url'] or '').strip() and 'ik.imagekit.io' not in (r['custom_image_url'] or '').lower()]

candidates = [r for r in rows if (r['custom_image_url'] or '').strip() and 'ik.imagekit.io' in (r['custom_image_url'] or '').lower()]

def check(r):
    url = r['custom_image_url']
    try:
        resp = requests.get(url, timeout=20, stream=True)
        status = resp.status_code
        ctype = (resp.headers.get('Content-Type') or '').lower()
        resp.close()
        return (r, status, ctype, None)
    except Exception as exc:
        return (r, None, '', str(exc))

bad = []
ok = 0
img_ok = 0

with ThreadPoolExecutor(max_workers=24) as ex:
    futs = [ex.submit(check, r) for r in candidates]
    for fut in as_completed(futs):
        r, status, ctype, err = fut.result()
        if status == 200:
            ok += 1
            if ctype.startswith('image/'):
                img_ok += 1
            else:
                bad.append((r, status, ctype, 'content-type no image'))
        else:
            bad.append((r, status, ctype, err or 'status != 200'))

print('AYDV_TOTAL=', total)
print('MISSING_URL=', len(missing_url))
print('NON_IMAGEKIT_URL=', len(non_ik))
print('IMAGEKIT_URLS=', len(candidates))
print('HTTP_200=', ok)
print('IMAGE_CONTENT_TYPE_OK=', img_ok)
print('BROKEN_OR_NON_IMAGE=', len(bad))

if bad:
    print('---BROKEN_SAMPLE_START---')
    for item in sorted(bad, key=lambda x: (str(x[0]['edid']), str(x[0]['name'])))[:80]:
        r, status, ctype, err = item
        print(f"{r['edid']} | {r['name']} | status={status} | ctype={ctype} | err={err} | url={r['custom_image_url']}")
    print('---BROKEN_SAMPLE_END---')
