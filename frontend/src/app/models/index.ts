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
  race?: string;
  entries?: DeckEntry[];
  sideboard_entries?: DeckEntry[];
  created_at: string;
  updated_at: string;
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
