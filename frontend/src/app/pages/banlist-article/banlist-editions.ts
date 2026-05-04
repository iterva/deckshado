/**
 * Lista de ediciones publicadas del artículo de banlist.
 * Para añadir una banlist nueva: agrega una entrada al array y registra la ruta
 * en app.routes.ts (también añade la URL en frontend/public/sitemap.xml).
 *
 * `slug` es la parte que va en la URL: /banlist/<slug>
 * Si la banlist NO cambia respecto a la versión anterior, deja el array igual y
 * solo crea una nueva entrada apuntando a los mismos datos del backend.
 */

export interface BanlistEdition {
  /** parte de la URL: /banlist/<slug> */
  slug: string;
  /** mes en español, en minúsculas, ej. "mayo" */
  month: string;
  /** año, ej. 2026 */
  year: number;
  /** fecha en formato ISO YYYY-MM-DD */
  publishedDate: string;
  /** última actualización (para JSON-LD) */
  modifiedDate: string;
  /** etiqueta de "Vigente" / "Histórica" */
  current: boolean;
}

export const BANLIST_EDITIONS: BanlistEdition[] = [
  {
    slug: 'mayo-2026',
    month: 'mayo',
    year: 2026,
    publishedDate: '2026-05-03',
    modifiedDate: '2026-05-03',
    current: true,
  },
  // Para añadir junio: copia la entrada de arriba, cambia slug/month/publishedDate
  // y pon current=true aquí + current=false en mayo.
];

export function getCurrentBanlistEdition(): BanlistEdition {
  return BANLIST_EDITIONS.find(e => e.current) || BANLIST_EDITIONS[0];
}

export function getBanlistEditionBySlug(slug: string): BanlistEdition | null {
  return BANLIST_EDITIONS.find(e => e.slug === slug) || null;
}
