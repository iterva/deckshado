import requests
import json

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

base = "https://blog.myl.cl"

# Fetch ALL media from WP API
all_media = []
page = 1
while page <= 100:
    url = f"{base}/wp-json/wp/v2/media?per_page=100&page={page}"
    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        break
    data = resp.json()
    if not data:
        break
    for item in data:
        src = item.get('source_url', '')
        if not src:
            continue
        all_media.append({
            'url': src,
            'title': item.get('title', {}).get('rendered', ''),
            'date': item.get('date', '')[:10],
            'mime': item.get('mime_type', ''),
            'width': item.get('media_details', {}).get('width', 0),
            'height': item.get('media_details', {}).get('height', 0),
            'sizes': item.get('media_details', {}).get('sizes', {}),
        })
    total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
    total_items = resp.headers.get('X-WP-Total', '?')
    print(f"Page {page}/{total_pages} (total: {total_items})")
    if page >= total_pages:
        break
    page += 1

# Dedup
seen = set()
unique = []
for m in all_media:
    if m['url'] not in seen:
        seen.add(m['url'])
        unique.append(m)

print(f"Total unique: {len(unique)}")

# Group by folder (year/month)
from collections import defaultdict
import re

folders = defaultdict(list)
for m in unique:
    # Extract path after /uploads/
    match = re.search(r'/uploads/(\d{4}/\d{2})/', m['url'])
    if match:
        folder = match.group(1)
    else:
        folder = 'other'
    
    fname = m['url'].split('/')[-1]
    # Get thumbnail URL if available
    thumb = ''
    if 'thumbnail' in m.get('sizes', {}):
        thumb = m['sizes']['thumbnail'].get('source_url', '')
    elif 'medium' in m.get('sizes', {}):
        thumb = m['sizes']['medium'].get('source_url', '')
    
    folders[folder].append({
        'url': m['url'],
        'thumb': thumb or m['url'],
        'name': fname,
        'title': m['title'],
        'date': m['date'],
        'mime': m['mime'],
    })

# Generate HTML
html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Blog MYL - Explorador de Imágenes</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #1a1a2e; color: #eee; }
h1 { text-align: center; padding: 20px; background: #16213e; border-bottom: 3px solid #0f3460; }
h1 span { color: #e94560; }

.controls { padding: 15px 20px; background: #16213e; display: flex; gap: 15px; align-items: center; flex-wrap: wrap; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid #0f3460; }
.controls input { padding: 8px 12px; border: 1px solid #0f3460; border-radius: 5px; background: #1a1a2e; color: #eee; width: 300px; font-size: 14px; }
.controls select { padding: 8px 12px; border: 1px solid #0f3460; border-radius: 5px; background: #1a1a2e; color: #eee; font-size: 14px; }
.controls label { font-size: 13px; color: #aaa; }
.controls .stats { margin-left: auto; color: #888; font-size: 13px; }

.sidebar { position: fixed; left: 0; top: 0; width: 220px; height: 100vh; background: #16213e; overflow-y: auto; padding-top: 10px; border-right: 1px solid #0f3460; z-index: 200; }
.sidebar h3 { padding: 10px 15px; color: #e94560; font-size: 14px; text-transform: uppercase; }
.sidebar a { display: block; padding: 6px 15px; color: #ccc; text-decoration: none; font-size: 13px; border-left: 3px solid transparent; }
.sidebar a:hover { background: #1a1a2e; color: #fff; border-left-color: #e94560; }
.sidebar a .count { float: right; color: #666; font-size: 11px; }
.sidebar a.active { background: #1a1a2e; color: #e94560; border-left-color: #e94560; }

.main { margin-left: 220px; }

.folder { padding: 20px; border-bottom: 1px solid #0f3460; }
.folder h2 { color: #e94560; margin-bottom: 15px; font-size: 18px; cursor: pointer; }
.folder h2:hover { color: #ff6b81; }
.folder h2 .badge { background: #0f3460; color: #aaa; font-size: 12px; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.card { background: #16213e; border-radius: 8px; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; cursor: pointer; }
.card:hover { transform: translateY(-3px); box-shadow: 0 5px 20px rgba(233,69,96,0.3); }
.card img { width: 100%; height: 200px; object-fit: contain; background: #0a0a1a; display: block; }
.card .info { padding: 8px 10px; }
.card .info .name { font-size: 11px; color: #ccc; word-break: break-all; line-height: 1.3; }
.card .info .date { font-size: 10px; color: #666; margin-top: 3px; }

/* Lightbox */
.lightbox { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 1000; justify-content: center; align-items: center; flex-direction: column; }
.lightbox.active { display: flex; }
.lightbox img { max-width: 90%; max-height: 80vh; object-fit: contain; }
.lightbox .lb-info { color: #fff; margin-top: 15px; text-align: center; }
.lightbox .lb-info a { color: #e94560; }
.lightbox .close { position: absolute; top: 20px; right: 30px; color: #fff; font-size: 30px; cursor: pointer; }
.lightbox .close:hover { color: #e94560; }
.lightbox .nav { position: absolute; top: 50%; font-size: 40px; color: #fff; cursor: pointer; padding: 20px; user-select: none; }
.lightbox .nav:hover { color: #e94560; }
.lightbox .nav.prev { left: 10px; }
.lightbox .nav.next { right: 10px; }

.hidden { display: none !important; }

/* Highlight matches */
.highlight { background: #e94560; color: #fff; padding: 0 2px; border-radius: 2px; }
</style>
</head>
<body>

<div class="sidebar" id="sidebar">
  <h3>📁 Carpetas</h3>
  <a href="#all" onclick="showAll()" class="active">Todas <span class="count" id="totalCount"></span></a>
</div>

<div class="main">
  <h1>Blog MYL - <span>Explorador de Imágenes</span></h1>
  
  <div class="controls">
    <input type="text" id="search" placeholder="🔍 Buscar archivo..." oninput="filterCards()">
    <select id="typeFilter" onchange="filterCards()">
      <option value="">Todos los tipos</option>
      <option value="chile-oscuro">Chile Oscuro</option>
      <option value="Toolkit-26-Imperio">Toolkit Imperio</option>
      <option value="reprint">Imperio Reprint</option>
      <option value="lootbox">Lootbox</option>
      <option value="MOCKUP">Mockups</option>
    </select>
    <label><input type="checkbox" id="hidedupes" onchange="filterCards()"> Ocultar duplicados (-1, -2)</label>
    <span class="stats" id="statsText"></span>
  </div>

  <div id="content"></div>
</div>

<div class="lightbox" id="lightbox" onclick="closeLightbox(event)">
  <span class="close" onclick="closeLightbox()">&times;</span>
  <span class="nav prev" onclick="navLightbox(-1, event)">&#10094;</span>
  <span class="nav next" onclick="navLightbox(1, event)">&#10095;</span>
  <img id="lb-img" src="">
  <div class="lb-info">
    <div id="lb-name"></div>
    <a id="lb-link" href="" target="_blank">Abrir original ↗</a>
  </div>
</div>

<script>
const DATA = JSONDATA;

let allCards = [];
let visibleCards = [];
let currentLbIndex = -1;

function init() {
  const sidebar = document.getElementById('sidebar');
  const content = document.getElementById('content');
  
  const sortedFolders = Object.keys(DATA).sort().reverse();
  
  sortedFolders.forEach(folder => {
    // Sidebar link
    const a = document.createElement('a');
    a.href = '#folder-' + folder;
    a.innerHTML = folder + ' <span class="count">' + DATA[folder].length + '</span>';
    a.onclick = () => { document.querySelectorAll('.sidebar a').forEach(x => x.classList.remove('active')); a.classList.add('active'); };
    sidebar.appendChild(a);
    
    // Folder section
    const section = document.createElement('div');
    section.className = 'folder';
    section.id = 'folder-' + folder;
    
    const h2 = document.createElement('h2');
    h2.innerHTML = '📁 ' + folder + ' <span class="badge">' + DATA[folder].length + ' archivos</span>';
    h2.onclick = () => { const g = section.querySelector('.grid'); g.classList.toggle('hidden'); };
    section.appendChild(h2);
    
    const grid = document.createElement('div');
    grid.className = 'grid';
    
    DATA[folder].sort((a, b) => a.name.localeCompare(b.name));
    
    DATA[folder].forEach((item, idx) => {
      const card = document.createElement('div');
      card.className = 'card';
      card.dataset.name = item.name.toLowerCase();
      card.dataset.folder = folder;
      card.dataset.url = item.url;
      
      const globalIdx = allCards.length;
      allCards.push({ ...item, folder, element: card });
      
      card.onclick = () => openLightbox(globalIdx);
      
      card.innerHTML = '<img src="' + item.thumb + '" loading="lazy" alt="' + item.name + '">' +
        '<div class="info"><div class="name">' + item.name + '</div><div class="date">' + item.date + '</div></div>';
      
      grid.appendChild(card);
    });
    
    section.appendChild(grid);
    content.appendChild(section);
  });
  
  document.getElementById('totalCount').textContent = allCards.length;
  updateStats();
}

function filterCards() {
  const q = document.getElementById('search').value.toLowerCase();
  const type = document.getElementById('typeFilter').value.toLowerCase();
  const hideDupes = document.getElementById('hidedupes').checked;
  
  let visible = 0;
  visibleCards = [];
  
  allCards.forEach(card => {
    const name = card.name.toLowerCase();
    let show = true;
    
    if (q && !name.includes(q)) show = false;
    if (type && !name.includes(type)) show = false;
    if (hideDupes && /-\\d+\\.(?:png|jpg|jpeg)$/i.test(card.name)) show = false;
    
    card.element.classList.toggle('hidden', !show);
    if (show) { visible++; visibleCards.push(card); }
  });
  
  // Hide empty folders
  document.querySelectorAll('.folder').forEach(folder => {
    const visCards = folder.querySelectorAll('.card:not(.hidden)');
    folder.classList.toggle('hidden', visCards.length === 0);
    const badge = folder.querySelector('.badge');
    if (badge) badge.textContent = visCards.length + ' archivos';
  });
  
  updateStats(visible);
}

function updateStats(count) {
  const c = count !== undefined ? count : allCards.length;
  document.getElementById('statsText').textContent = c + ' / ' + allCards.length + ' imágenes';
}

function openLightbox(idx) {
  currentLbIndex = idx;
  const item = allCards[idx];
  document.getElementById('lb-img').src = item.url;
  document.getElementById('lb-name').textContent = item.name + ' (' + item.date + ')';
  document.getElementById('lb-link').href = item.url;
  document.getElementById('lightbox').classList.add('active');
}

function closeLightbox(e) {
  if (!e || e.target.id === 'lightbox' || e.target.classList.contains('close'))
    document.getElementById('lightbox').classList.remove('active');
}

function navLightbox(dir, e) {
  e.stopPropagation();
  currentLbIndex = (currentLbIndex + dir + allCards.length) % allCards.length;
  openLightbox(currentLbIndex);
}

document.addEventListener('keydown', e => {
  if (!document.getElementById('lightbox').classList.contains('active')) return;
  if (e.key === 'Escape') closeLightbox();
  if (e.key === 'ArrowLeft') navLightbox(-1, e);
  if (e.key === 'ArrowRight') navLightbox(1, e);
});

init();
</script>
</body>
</html>"""

# Replace placeholder with actual data
html = html.replace('JSONDATA', json.dumps(dict(sorted(folders.items(), reverse=True)), ensure_ascii=False))

with open('explorador_blog.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\nGenerado: explorador_blog.html")
print(f"Total: {len(unique)} imágenes en {len(folders)} carpetas")
print(f"Carpetas: {', '.join(sorted(folders.keys(), reverse=True))}")
