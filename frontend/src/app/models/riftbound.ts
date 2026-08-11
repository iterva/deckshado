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
  image_url?: string;
  image_url_small?: string;
  cdn_image_url?: string;
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
  champion_unit?: number | null;
  champion_unit_data?: RiftboundCardLite | null;
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
  card_type?: RiftboundCardType;
  card_image?: string;
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

export type RiftboundCondition = 'NM' | 'LP' | 'MP' | 'HP' | 'DMG';
export type RiftboundLanguage = 'EN' | 'ZH';

export interface RiftboundCollectionEntry {
  id: number;
  card: number;
  card_data: RiftboundCardLite;
  quantity: number;
  price?: number | null;
  selling_quantity: number;
  condition: RiftboundCondition;
  language: RiftboundLanguage;
  is_foil: boolean;
  notes: string;
  photo_url?: string | null;
  photo_url_2?: string | null;
}

export interface RiftboundBinderProfile {
  id: number;
  username: string;
  share_token: string;
  binder_avatar: string;
  binder_avatar_url: string;
  user_avatar_url: string;
  store_slug: string;
  is_store_public: boolean;
  display_name: string;
  bio: string;
  city: string;
  country: string;
  whatsapp: string;
  instagram: string;
  discord: string;
  email_public: string;
  payment_methods: string;
  shipping_info: string;
  accepts_trades: boolean;
  last_active: string;
}

export interface RiftboundPublicBinderProfile extends RiftboundBinderProfile {
  selling_count?: number;
  has_store?: boolean;
  has_wishlist?: boolean;
  wishlist_count?: number;
}

export interface RiftboundStorePermissionFlags {
  view_collection: boolean;
  edit_collection: boolean;
  delete_collection: boolean;
  edit_market: boolean;
  remove_from_market: boolean;
  view_orders: boolean;
  view_history: boolean;
  accept_orders: boolean;
  reject_orders: boolean;
  manage_permissions: boolean;
}

export interface RiftboundWorkspace {
  store_profile_id: number;
  is_owner: boolean;
  owner_username: string;
  permissions: RiftboundStorePermissionFlags;
  profile: RiftboundBinderProfile;
}

export interface RiftboundStoreCollaboratorPermission {
  id: number;
  store_profile: number;
  user_id: number;
  username: string;
  granted_by?: number | null;
  granted_by_username?: string;
  permissions: RiftboundStorePermissionFlags;
  can_view_collection: boolean;
  can_edit_collection: boolean;
  can_delete_collection: boolean;
  can_edit_market: boolean;
  can_remove_from_market: boolean;
  can_view_orders: boolean;
  can_view_history: boolean;
  can_accept_orders: boolean;
  can_reject_orders: boolean;
  can_manage_permissions: boolean;
  created_at: string;
  updated_at: string;
}

export type RiftboundStoreOrderStatus = 'pending' | 'accepted' | 'cancelled';

export interface RiftboundStoreOrderItem {
  id: number;
  collection_entry: number | null;
  card: number;
  card_data?: RiftboundCardLite;
  quantity: number;
  unit_price: number | null;
  line_total: number | null;
  card_name: string;
  card_number: string;
  language: RiftboundLanguage;
  is_foil: boolean;
}

export interface RiftboundStoreOrder {
  id: number;
  store_profile: number;
  store_owner: string;
  buyer_user: number | null;
  buyer_username?: string;
  responded_by: number | null;
  responded_by_username?: string;
  buyer_name: string;
  buyer_whatsapp: string;
  buyer_note: string;
  seller_note: string;
  status: RiftboundStoreOrderStatus;
  total_estimated: number | null;
  total_items: number;
  responded_at: string | null;
  created_at: string;
  updated_at: string;
  items: RiftboundStoreOrderItem[];
}

export interface RiftboundStoreOrderCreateItem {
  entry_id: number;
  quantity: number;
}

export interface RiftboundStoreOrderCreatePayload {
  buyer_name?: string;
  buyer_whatsapp?: string;
  buyer_note?: string;
  items: RiftboundStoreOrderCreateItem[];
}

export interface RiftboundStoreOrderAssignedSummary {
  assigned_by_entry: Record<number, number>;
}

export interface RiftboundBulkImportResult {
  added: number;
  updated: number;
  not_found: number;
  ambiguous: number;
  not_found_lines: string[];
  ambiguous_lines: string[];
}

export interface RiftboundWishlistEntry {
  id: number;
  card: number;
  card_data: RiftboundCardLite;
  desired_quantity: number;
}

export interface RiftboundCarpetaIds {
  collection: { [cardId: number]: number };
  wishlist: number[];
}

export interface RiftboundCollectionStats {
  total_cards: number;
  unique_cards: number;
  total_value?: number;
  by_type: { key: string; count: number }[];
  by_rarity: { key: string; count: number }[];
  by_color: { key: string; count: number }[];
  by_set: { key: string; name: string; count: number }[];
  set_completeness: { set: string; name: string; owned: number; total: number; pct: number }[];
}

/** Cantidad esperada por zona (Standard).
 *  Para `main` es el MÍNIMO (puedes ir a más); para el resto es exacta.
 *  `side` sólo aplica en juego de torneo.
 */
export const RIFTBOUND_ZONE_RULES: Record<RiftboundZone, number> = {
  main: 40,
  side: 10,
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
