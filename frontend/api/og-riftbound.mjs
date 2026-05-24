// Vercel serverless function: inyecta meta tags Open Graph dinámicos para
// las URLs públicas de Riftbound (tiendas y wishlists). Devuelve el index.html
// del SPA con las metas reescritas para que WhatsApp/Discord/Twitter muestren
// el nombre de la tienda y que se trata de cartas Riftbound, en vez del
// preview genérico de Mitos y Leyendas.

const API_BASE = 'https://iterva.pythonanywhere.com/api';

function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

async function fetchStore(token) {
  try {
    const r = await fetch(`${API_BASE}/riftbound/store/${encodeURIComponent(token)}/?page_size=1`, {
      headers: { Accept: 'application/json' },
    });
    if (!r.ok) return null;
    const data = await r.json();
    return data && data.store ? { store: data.store, owner: data.store_owner } : null;
  } catch {
    return null;
  }
}

async function fetchIndexHtml(origin) {
  // Pedimos el index.html ya desplegado; Vercel sirve el asset estático
  // sin pasar por las reglas de rewrite porque es un path concreto.
  const r = await fetch(`${origin}/index.html`, { headers: { 'cache-control': 'no-cache' } });
  if (!r.ok) throw new Error(`index.html fetch failed: ${r.status}`);
  return r.text();
}

function buildMeta({ title, description, url, image }) {
  return {
    title,
    description,
    url,
    image: image || `${new URL(url).origin}/og-image.png`,
  };
}

function applyMeta(html, meta) {
  const t = escapeHtml(meta.title);
  const d = escapeHtml(meta.description);
  const u = escapeHtml(meta.url);
  const img = escapeHtml(meta.image);

  // <title>
  html = html.replace(/<title>[\s\S]*?<\/title>/i, `<title>${t}</title>`);
  // <meta name="description">
  html = html.replace(
    /<meta\s+name="description"[^>]*>/i,
    `<meta name="description" content="${d}">`,
  );
  // canonical
  html = html.replace(
    /<link\s+rel="canonical"[^>]*>/i,
    `<link rel="canonical" href="${u}">`,
  );
  // og:title
  html = html.replace(
    /<meta\s+property="og:title"[^>]*>/i,
    `<meta property="og:title" content="${t}">`,
  );
  // og:description
  html = html.replace(
    /<meta\s+property="og:description"[^>]*>/i,
    `<meta property="og:description" content="${d}">`,
  );
  // og:url
  html = html.replace(
    /<meta\s+property="og:url"[^>]*>/i,
    `<meta property="og:url" content="${u}">`,
  );
  // og:image (mantenemos dimensiones existentes)
  html = html.replace(
    /<meta\s+property="og:image"(?!:)[^>]*>/i,
    `<meta property="og:image" content="${img}">`,
  );
  // og:image:alt
  html = html.replace(
    /<meta\s+property="og:image:alt"[^>]*>/i,
    `<meta property="og:image:alt" content="${t}">`,
  );
  // og:site_name
  html = html.replace(
    /<meta\s+property="og:site_name"[^>]*>/i,
    `<meta property="og:site_name" content="ShadowForge · Riftbound">`,
  );
  // twitter:title / description / image (si existen)
  html = html.replace(
    /<meta\s+name="twitter:title"[^>]*>/i,
    `<meta name="twitter:title" content="${t}">`,
  );
  html = html.replace(
    /<meta\s+name="twitter:description"[^>]*>/i,
    `<meta name="twitter:description" content="${d}">`,
  );
  html = html.replace(
    /<meta\s+name="twitter:image"[^>]*>/i,
    `<meta name="twitter:image" content="${img}">`,
  );

  return html;
}

export default async function handler(req, res) {
  try {
    const host = req.headers['x-forwarded-host'] || req.headers.host;
    const proto = (req.headers['x-forwarded-proto'] || 'https').split(',')[0].trim();
    const origin = `${proto}://${host}`;

    // Los rewrites de vercel.json pasan kind y token por query string.
    const kind = (req.query && req.query.kind) || 'index';
    const token = (req.query && req.query.token) || '';

    let originalPath = '/riftbound/tiendas';
    if (kind === 'store' && token) originalPath = `/riftbound/tienda/${encodeURIComponent(token)}`;
    else if (kind === 'wishlist' && token) originalPath = `/riftbound/wishlist/${encodeURIComponent(token)}`;
    const fullUrl = `${origin}${originalPath}`;

    let title = 'Tiendas Riftbound · ShadowForge';
    let description =
      'Directorio de tiendas de cartas Riftbound TCG en ShadowForge. Encuentra coleccionistas y vendedores de cartas Riftbound.';
    let imageStoreName = '';

    if (kind === 'store' || kind === 'wishlist') {
      const info = await fetchStore(token);
      const storeName =
        (info && info.store && (info.store.display_name || info.owner)) || 'Tienda Riftbound';
      imageStoreName = storeName;
      const city = info && info.store && info.store.city;
      const country = info && info.store && info.store.country;
      const bio = info && info.store && info.store.bio;
      const sellingCount = info && info.store && info.store.selling_count;
      const ubicacion = [city, country].filter(Boolean).join(', ');

      if (kind === 'wishlist') {
        title = `Wishlist Riftbound de ${storeName} · ShadowForge`;
        description =
          (bio ? `${bio} · ` : '') +
          `Cartas Riftbound TCG que ${storeName} busca para su colección. Si tienes alguna, contáctalo a través de ShadowForge.`;
      } else {
        title = `${storeName} · Tienda Riftbound · ShadowForge`;
        const partes = [];
        if (sellingCount) partes.push(`${sellingCount} carta${sellingCount === 1 ? '' : 's'} Riftbound a la venta`);
        if (ubicacion) partes.push(ubicacion);
        if (bio) partes.push(bio);
        description = (partes.length
          ? partes.join(' · ')
          : `Tienda de cartas Riftbound TCG de ${storeName}.`) +
          ' Explora la colección y contacta al vendedor desde ShadowForge.';
      }
    }

    // Asegurar longitud razonable para previews
    if (description.length > 300) description = description.slice(0, 297) + '...';

    // Imagen OG generada dinámicamente con estética Riftbound
    const imageQs = new URLSearchParams({ kind });
    if (imageStoreName) imageQs.set('store', imageStoreName);
    const image = `${origin}/api/og-image-riftbound?${imageQs.toString()}`;

    const indexHtml = await fetchIndexHtml(origin);
    const meta = buildMeta({ title, description, url: fullUrl, image });
    const html = applyMeta(indexHtml, meta);

    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 'public, max-age=300, s-maxage=600, stale-while-revalidate=86400');
    res.status(200).send(html);
  } catch (e) {
    // Fallback: redirigir al SPA tradicional para no romper navegación.
    res.setHeader('Cache-Control', 'no-store');
    res.status(500).send(
      `<!doctype html><meta http-equiv="refresh" content="0;url=/"><title>ShadowForge</title>`,
    );
  }
}
