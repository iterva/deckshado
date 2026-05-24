// Genera dinámicamente la imagen Open Graph (1200x630 PNG) para los previews
// de Riftbound. Reemplaza el banner de Mitos y Leyendas con uno de Riftbound,
// e incluye opcionalmente el nombre de la tienda.
//
// Uso: /api/og-image-riftbound?store=NombreTienda&kind=store
// kind = "store" | "wishlist" | "index"
//
// Vercel ejecuta esto como Edge Function gracias a `export const config`.

import { ImageResponse } from '@vercel/og';

export const config = { runtime: 'edge' };

// Helper para crear "elementos" tipo React sin necesidad de import de React.
// Satori (que es lo que usa @vercel/og por debajo) acepta este shape.
function h(type, props = {}, ...children) {
  const flat = children.flat().filter((c) => c !== null && c !== undefined && c !== false);
  return {
    type,
    props: { ...props, children: flat.length === 1 ? flat[0] : flat },
    key: null,
  };
}

export default function handler(req) {
  const url = new URL(req.url);
  const store = (url.searchParams.get('store') || '').slice(0, 60);
  const kind = url.searchParams.get('kind') || 'index';

  const title =
    kind === 'wishlist'
      ? store
        ? `Wishlist de ${store}`
        : 'Wishlist Riftbound'
      : kind === 'store'
        ? store || 'Tienda Riftbound'
        : 'ShadowForge';

  const subtitle =
    kind === 'store' || kind === 'wishlist'
      ? 'Tienda Riftbound TCG'
      : 'Constructor de mazos Riftbound';

  const footer = 'Banlist · Mercado · Deck builder · 100% gratis';

  return new ImageResponse(
    h(
      'div',
      {
        style: {
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          padding: '70px 80px',
          background:
            'linear-gradient(135deg, #0f0c29 0%, #1a1147 35%, #2a1458 60%, #4a1d6e 100%)',
          fontFamily: 'sans-serif',
          color: '#fff',
          position: 'relative',
        },
      },
      // Decoración: aro brillante arriba-derecha
      h('div', {
        style: {
          position: 'absolute',
          top: '-160px',
          right: '-160px',
          width: '460px',
          height: '460px',
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(255,193,7,0.35) 0%, rgba(255,193,7,0) 70%)',
        },
      }),
      h('div', {
        style: {
          position: 'absolute',
          bottom: '-200px',
          left: '-160px',
          width: '500px',
          height: '500px',
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(233,69,96,0.35) 0%, rgba(233,69,96,0) 70%)',
        },
      }),
      // Encabezado: etiqueta "RIFTBOUND"
      h(
        'div',
        { style: { display: 'flex', alignItems: 'center', gap: '24px' } },
        h('div', {
          style: {
            width: '20px',
            height: '60px',
            background: '#ffc107',
            borderRadius: '4px',
            boxShadow: '0 0 30px rgba(255,193,7,0.7)',
          },
        }),
        h(
          'div',
          {
            style: {
              fontSize: '46px',
              fontWeight: 800,
              letterSpacing: '8px',
              color: '#ffc107',
              textShadow: '0 0 25px rgba(255,193,7,0.6)',
            },
          },
          'RIFTBOUND',
        ),
      ),
      // Cuerpo: título principal + ShadowForge
      h(
        'div',
        { style: { display: 'flex', flexDirection: 'column', gap: '14px' } },
        h(
          'div',
          {
            style: {
              fontSize: '108px',
              fontWeight: 900,
              lineHeight: 1.02,
              background:
                'linear-gradient(90deg, #ff6b9d 0%, #e94560 40%, #ffc107 100%)',
              backgroundClip: 'text',
              color: 'transparent',
              textShadow: '0 0 40px rgba(233,69,96,0.4)',
            },
          },
          title,
        ),
        h(
          'div',
          {
            style: {
              fontSize: '42px',
              fontWeight: 600,
              color: '#e0e0e0',
              marginTop: '8px',
            },
          },
          subtitle,
        ),
        h(
          'div',
          {
            style: {
              fontSize: '30px',
              fontWeight: 500,
              color: '#9b8bc4',
            },
          },
          'ShadowForge',
        ),
      ),
      // Footer: features + URL
      h(
        'div',
        {
          style: {
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderTop: '2px solid rgba(255,193,7,0.4)',
            paddingTop: '24px',
          },
        },
        h(
          'div',
          {
            style: {
              fontSize: '26px',
              color: '#d0d0d0',
              letterSpacing: '1px',
            },
          },
          footer,
        ),
        h(
          'div',
          {
            style: {
              fontSize: '24px',
              color: '#ffc107',
              fontWeight: 700,
              padding: '12px 22px',
              borderRadius: '999px',
              background: 'rgba(255,193,7,0.12)',
              border: '2px solid #ffc107',
            },
          },
          'shadow-forge-deck.vercel.app',
        ),
      ),
    ),
    {
      width: 1200,
      height: 630,
      headers: {
        'cache-control': 'public, max-age=600, s-maxage=86400, stale-while-revalidate=604800',
      },
    },
  );
}
