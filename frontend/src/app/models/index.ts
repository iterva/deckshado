export interface Card {
  id: number;
  myl_id: string;
  edid: string;
  slug: string;
  name: string;
  edition_slug: string;
  edition_title: string;
  rarity_name: string | null;
  race_name: string | null;
  race_slug: string | null;
  type_name: string | null;
  cost: string | null;
  damage: string | null;
  ability: string | null;
  flavour: string | null;
  is_unique: boolean;
  image_url: string;
}

export interface Edition {
  id: number;
  myl_id: string;
  slug: string;
  title: string;
  image: string | null;
  date_release: string | null;
  date_empire_valid: string | null;
  format_code: string | null;
  format_name: string | null;
  active: boolean;
}

export interface Format {
  id: number;
  code: string;
  name: string;
}

export interface Race {
  id: number;
  myl_id: string;
  slug: string;
  name: string;
}

export interface CardType {
  id: number;
  myl_id: string;
  slug: string;
  name: string;
}

export interface Rarity {
  id: number;
  myl_id: string;
  slug: string;
  name: string;
}

export interface Deck {
  id: number;
  name: string;
  description: string;
  is_public: boolean;
  shared_with_team?: boolean;
  owner_username: string;
  card_count: number;
  format?: string;
  sub_format?: string;
  race?: string;
  pb_edition?: string;
  starting_gold?: number | null;
  starting_gold_detail?: Card | null;
  cover_card?: number | null;
  cover_card_detail?: Card | null;
  cover_preview?: Card[];
  entries?: DeckEntry[];
  sideboard_entries?: DeckEntry[];
  created_at: string;
  updated_at: string;
  like_count?: number;
  user_liked?: boolean;
  comment_count?: number;
}

export interface DeckEntry {
  id: number;
  card: number;
  quantity: number;
  is_sideboard: boolean;
  card_detail: Card;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface BanlistEntry {
  id: number;
  card_name: string;
  card_id: number | null;
  card_image_url: string | null;
  format_code: string;
  sub_format: string;
  status: 'banned' | 'limited_1' | 'limited_2';
  max_copies: number;
  last_synced: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  league_code: string;
  avatar_url: string | null;
  is_admin?: boolean;
}

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  league_code: string;
  avatar_url: string | null;
  is_active: boolean;
  is_staff: boolean;
  is_admin: boolean;
  date_joined: string;
  last_login: string | null;
}

export interface TeamMember {
  id: number;
  username: string;
  role: 'captain' | 'member';
  role_display: string;
  joined_at: string;
}

export interface Team {
  id: number;
  name: string;
  description: string;
  member_count: number;
  logo_url?: string | null;
  members?: TeamMember[];
  my_role?: string;
  created_at: string;
}

export interface JoinRequest {
  id: number;
  username: string;
  status: 'pending' | 'accepted' | 'rejected';
  status_display: string;
  created_at: string;
}

export interface BinderProfile {
  id: number;
  username: string;
  binder_avatar_url: string | null;
  share_token: string;
  store_slug: string;
  is_store_public: boolean;
  display_name: string;
  bio: string;
  city: string;
  country: string;
  country_display?: string;
  whatsapp: string;
  instagram: string;
  discord: string;
  email_public: string;
  payment_methods: string;
  shipping_info: string;
  accepts_trades: boolean;
}

export interface PublicBinderProfile {
  username: string;
  store_slug: string;
  binder_avatar_url: string | null;
  user_avatar_url: string | null;
  display_name: string;
  bio: string;
  city: string;
  country: string;
  country_display?: string;
  whatsapp: string;
  instagram: string;
  discord: string;
  email_public: string;
  payment_methods: string;
  shipping_info: string;
  accepts_trades: boolean;
  last_active: string;
  selling_count: number;
  has_store?: boolean;
  has_wishlist?: boolean;
  wishlist_count?: number;
}

export type CardCondition = 'NM' | 'LP' | 'MP' | 'HP' | 'DMG';
export type CardLanguage = 'ES' | 'EN' | 'PT' | 'FR' | 'OT';

export interface CollectionEntry {
  id: number;
  card: number;
  quantity: number;
  price: number | null;
  selling_quantity: number;
  condition: CardCondition;
  condition_display?: string;
  language: CardLanguage;
  language_display?: string;
  is_foil: boolean;
  notes: string;
  photo_url?: string | null;
  photo_url_2?: string | null;
  card_detail: Card;
  in_my_wishlist?: boolean;
}

export interface WishlistEntry {
  id: number;
  card: number;
  desired_quantity: number;
  card_detail: Card;
}

export interface CarpetaIds {
  collection: { [cardId: number]: number };
  wishlist: number[];
}

export type StoreOrderStatus = 'pending' | 'accepted' | 'cancelled';

export interface StoreOrderItem {
  id: number;
  collection_entry: number | null;
  card: number;
  card_detail?: Card;
  quantity: number;
  unit_price: number | null;
  line_total: number | null;
  card_name: string;
  card_edid: string;
  language: CardLanguage;
  is_foil: boolean;
}

export interface StoreOrder {
  id: number;
  store_profile: number;
  store_owner: string;
  buyer_user: number | null;
  buyer_username?: string;
  buyer_name: string;
  buyer_whatsapp: string;
  buyer_note: string;
  seller_note: string;
  status: StoreOrderStatus;
  total_estimated: number | null;
  total_items: number;
  responded_at: string | null;
  created_at: string;
  updated_at: string;
  items: StoreOrderItem[];
}

export interface StoreOrderCreateItem {
  entry_id: number;
  quantity: number;
}

export interface StoreOrderCreatePayload {
  buyer_name: string;
  buyer_whatsapp: string;
  buyer_note?: string;
  items: StoreOrderCreateItem[];
}

export interface StoreOrderAssignedSummary {
  assigned_by_entry: Record<number, number>;
}
