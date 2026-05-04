export type RiftboundCardType =
  | 'champion' | 'legend' | 'unit' | 'spell' | 'gear' | 'battlefield' | 'rune' | 'other';

export type RiftboundColor = 'fury' | 'calm' | 'mind' | 'body' | 'chaos' | 'order' | 'neutral';

export type RiftboundRarity =
  | 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary' | 'champion' | 'promo' | 'other';

export type RiftboundZone = 'main' | 'side' | 'rune' | 'champion' | 'bg';

export interface RiftboundSet {
  id: number;
  code: string;
  name: string;
  release_date: string | null;
}

export interface RiftboundCard {
  id: number;
  card_number: string;
  external_id: string;
  name: string;
  slug: string;
  set: RiftboundSet | null;
  card_type: RiftboundCardType;
  supertype: string;
  subtypes: string[];
  rarity: RiftboundRarity;
  variant: string;
  colors: RiftboundColor[];
  energy: number | null;
  power: number | null;
  might: number | null;
  description: string;
  flavor: string;
  image_url: string;
  image_url_small: string;
  cdn_image_url: string;
  image: string;
  is_active: boolean;
}

export interface RiftboundCardLite {
  id: number;
  card_number: string;
  name: string;
  card_type: RiftboundCardType;
  rarity: RiftboundRarity;
  colors: RiftboundColor[];
  energy: number | null;
  power: number | null;
  might: number | null;
  image: string;
  description?: string;
  subtypes?: string[];
}

export interface RiftboundDeckEntry {
  id?: number;
  card: number;
  card_data?: RiftboundCardLite;
  quantity: number;
  zone: RiftboundZone;
}

export interface RiftboundDeckValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
  counts: Partial<Record<RiftboundZone, number>>;
  rules: Record<RiftboundZone, number>;
}

export interface RiftboundDeck {
  id: number;
  name: string;
  description: string;
  format: number | null;
  is_public: boolean;
  primary_colors: RiftboundColor[];
  cover_card: number | null;
  cover_card_data: RiftboundCardLite | null;
  owner: number;
  owner_username: string;
  entries: RiftboundDeckEntry[];
  validation: RiftboundDeckValidation;
  created_at: string;
  updated_at: string;
}

export interface RiftboundFormat {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
}

export interface RiftboundBanlistEntry {
  id: number;
  card: number;
  card_name: string;
  card_number: string;
  format: number;
  format_code: string;
  status: 'banned' | 'limited_1' | 'limited_2';
  max_copies: number;
  note: string;
  effective_from: string | null;
}

export interface RiftboundIcon {
  id: number;
  kind: 'color' | 'keyword' | 'stat' | 'type' | 'other';
  code: string;
  label: string;
  image_url: string;
  cdn_image_url: string;
  image: string;
}

export interface RiftboundCollectionEntry {
  id: number;
  card: number;
  card_data: RiftboundCardLite;
  quantity: number;
  is_foil: boolean;
  notes: string;
}

/** Cantidad esperada por zona (Standard).
 *  Para `main` es el MÍNIMO (puedes ir a más); para el resto es exacta.
 *  `side` sólo aplica en juego de torneo.
 */
export const RIFTBOUND_ZONE_RULES: Record<RiftboundZone, number> = {
  main: 40,
  side: 8,
  rune: 12,
  champion: 1,
  bg: 3,
};

export const RIFTBOUND_ZONE_LABELS: Record<RiftboundZone, string> = {
  main: 'Mazo principal',
  side: 'Sideboard',
  rune: 'Runas',
  champion: 'Champion Legend',
  bg: 'Battlefields',
};
