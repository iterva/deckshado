import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of, shareReplay, tap, map, switchMap, forkJoin, catchError, finalize } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  RiftboundCard, RiftboundCardLite, RiftboundDeck, RiftboundFormat,
  RiftboundBanlistEntry, RiftboundIcon, RiftboundSet, RiftboundCollectionEntry,
  RiftboundWishlistEntry, RiftboundCarpetaIds, RiftboundCollectionStats,
  RiftboundBinderProfile, RiftboundPublicBinderProfile, RiftboundBulkImportResult,
} from '../models/riftbound';

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

interface RiftboundCatalogCachePayload {
  version: number;
  savedAt: number;
  total: number;
  cards: RiftboundCard[];
}

const RB_CATALOG_CACHE_KEY = 'rb_catalog_cards_v3';
const RB_CATALOG_CACHE_VERSION = 3;
const RB_CATALOG_CACHE_TTL_MS = 1000 * 60 * 60 * 6;
const RB_DEFAULT_PAGE_SIZE = 20;
const RB_MAX_PAGE_SIZE = 100;

@Injectable({ providedIn: 'root' })
export class RiftboundService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/riftbound`;

  private formats$: Observable<RiftboundFormat[]> | null = null;
  private sets$: Observable<RiftboundSet[]> | null = null;
  private icons$: Observable<RiftboundIcon[]> | null = null;
  private catalogCards = signal<RiftboundCard[] | null>(null);
  private catalogTotal = signal<number>(0);
  private catalogLoadedAt = signal<number>(0);
  private catalogWarmup$: Observable<RiftboundCard[]> | null = null;

  preloadCardsCatalog(force = false): Observable<number> {
    return this.ensureCatalogReady(force).pipe(map(cards => cards.length));
  }

  hasUsableCatalogSnapshot(): boolean {
    if (this.catalogTotal() > 0) {
      return true;
    }
    const inMemory = this.catalogCards();
    if (inMemory?.length) {
      return true;
    }
    const fromStorage = this.readCatalogFromStorage();
    return (fromStorage?.total ?? 0) > 0 || !!fromStorage?.cards?.length;
  }

  cachedCatalogCountSnapshot(): number {
    if (this.catalogTotal() > 0) {
      return this.catalogTotal();
    }
    const inMemory = this.catalogCards();
    if (inMemory?.length) {
      return inMemory.length;
    }
    const fromStorage = this.readCatalogFromStorage();
    return fromStorage?.total ?? fromStorage?.cards?.length ?? 0;
  }

  // ── Cartas ──
  listCards(opts: {
    search?: string;
    searchMode?: 'name' | 'ability' | 'all';
    type?: string;
    rarity?: string;
    colors?: string[];
    set?: string;
    energy?: number;
    page?: number;
    pageSize?: number;
    lite?: boolean;
    subtype?: string;
    excludeBattlefields?: boolean;
  } = {}): Observable<PaginatedResponse<RiftboundCard | RiftboundCardLite>> {
    return this.ensureCatalogReady().pipe(
      switchMap(cards => {
        if (cards.length > 0) {
          return of(this.buildCatalogResponse(cards, opts));
        }
        return this.fetchCardsHttp(opts);
      }),
    );
  }

  private fetchCardsHttp(opts: {
    search?: string;
    searchMode?: 'name' | 'ability' | 'all';
    type?: string;
    rarity?: string;
    colors?: string[];
    set?: string;
    energy?: number;
    page?: number;
    pageSize?: number;
    lite?: boolean;
    subtype?: string;
    excludeBattlefields?: boolean;
  }): Observable<PaginatedResponse<RiftboundCard | RiftboundCardLite>> {
    let params = new HttpParams();
    params = params.set('source', 'riftcodex');
    if (opts.search) {
      const mode = opts.searchMode ?? 'all';
      if (mode === 'name') params = params.set('name_search', opts.search);
      else if (mode === 'ability') params = params.set('ability_search', opts.search);
      else params = params.set('search', opts.search);
    }
    if (opts.type) params = params.set('type', opts.type);
    if (opts.rarity) params = params.set('rarity', opts.rarity);
    if (opts.colors?.length) params = params.set('colors', opts.colors.join(','));
    if (opts.set) params = params.set('set', opts.set);
    if (opts.energy !== undefined) params = params.set('energy', String(opts.energy));
    if (opts.page) params = params.set('page', String(opts.page));
    if (opts.pageSize) params = params.set('page_size', String(opts.pageSize));
    if (opts.lite) params = params.set('lite', '1');
    if (opts.subtype) params = params.set('subtype', opts.subtype);
    if (opts.excludeBattlefields) params = params.set('exclude_battlefields', '1');
    return this.http.get<PaginatedResponse<RiftboundCard | RiftboundCardLite>>(`${this.base}/cards/`, { params });
  }

  private ensureCatalogReady(force = false): Observable<RiftboundCard[]> {
    if (!force) {
      const inMemory = this.catalogCards();
      const loadedAt = this.catalogLoadedAt();
      if (inMemory?.length && this.isCacheFresh(loadedAt)) {
        if (this.catalogTotal() <= 0) {
          this.catalogTotal.set(inMemory.length);
        }
        return of(inMemory);
      }

      const fromStorage = this.readCatalogFromStorage();
      if (fromStorage?.cards?.length) {
        this.catalogCards.set(fromStorage.cards);
        this.catalogTotal.set(fromStorage.total || fromStorage.cards.length);
        this.catalogLoadedAt.set(fromStorage.savedAt);
        return of(fromStorage.cards);
      }
    }

    if (this.catalogWarmup$) {
      return this.catalogWarmup$;
    }

    this.catalogWarmup$ = this.fetchAllCardsFromApi().pipe(
      tap(cards => this.saveCatalog(cards)),
      catchError(() => of(this.catalogCards() ?? [])),
      finalize(() => {
        this.catalogWarmup$ = null;
      }),
      shareReplay({ bufferSize: 1, refCount: false }),
    );
    return this.catalogWarmup$;
  }

  private fetchCardsPage(page: number, pageSize: number): Observable<PaginatedResponse<RiftboundCard>> {
    let params = new HttpParams();
    params = params.set('source', 'riftcodex');
    params = params.set('page', String(page));
    params = params.set('page_size', String(pageSize));
    return this.http.get<PaginatedResponse<RiftboundCard>>(`${this.base}/cards/`, { params });
  }

  private fetchAllCardsFromApi(): Observable<RiftboundCard[]> {
    const pageSize = RB_MAX_PAGE_SIZE;
    return this.fetchCardsPage(1, pageSize).pipe(
      switchMap(first => {
        const firstResults = Array.isArray(first.results) ? first.results : [];
        const total = first.count || firstResults.length;
        const effectivePageSize = Math.max(1, firstResults.length || pageSize);
        const pages = Math.max(1, Math.ceil(total / effectivePageSize));
        if (pages === 1) {
          return of(this.normalizeCatalog(firstResults));
        }

        const restRequests: Observable<PaginatedResponse<RiftboundCard>>[] = [];
        for (let p = 2; p <= pages; p += 1) {
          restRequests.push(this.fetchCardsPage(p, pageSize));
        }

        return forkJoin(restRequests).pipe(
          map(rest => {
            const all = [...firstResults];
            for (const chunk of rest) {
              if (Array.isArray(chunk.results)) {
                all.push(...chunk.results);
              }
            }
            return this.normalizeCatalog(all);
          }),
        );
      }),
    );
  }

  private normalizeCatalog(cards: RiftboundCard[]): RiftboundCard[] {
    const byId = new Map<number, RiftboundCard>();
    for (const card of cards) {
      if (!card || !card.id) continue;
      byId.set(card.id, card);
    }
    return Array.from(byId.values()).sort((a, b) => {
      const an = (a.card_number || '').toLowerCase();
      const bn = (b.card_number || '').toLowerCase();
      return an.localeCompare(bn);
    });
  }

  private isCacheFresh(savedAt: number): boolean {
    if (!savedAt) return false;
    return Date.now() - savedAt < RB_CATALOG_CACHE_TTL_MS;
  }

  private readCatalogFromStorage(): RiftboundCatalogCachePayload | null {
    try {
      const raw = localStorage.getItem(RB_CATALOG_CACHE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as RiftboundCatalogCachePayload;
      if (!parsed || parsed.version !== RB_CATALOG_CACHE_VERSION) return null;
      if (!Array.isArray(parsed.cards)) return null;
      if (!this.isCacheFresh(parsed.savedAt)) return null;
      return parsed;
    } catch {
      return null;
    }
  }

  private saveCatalog(cards: RiftboundCard[]): void {
    const now = Date.now();
    const total = cards.length;
    this.catalogCards.set(cards);
    this.catalogTotal.set(total);
    this.catalogLoadedAt.set(now);
    try {
      const payload: RiftboundCatalogCachePayload = {
        version: RB_CATALOG_CACHE_VERSION,
        savedAt: now,
        total,
        cards,
      };
      localStorage.setItem(RB_CATALOG_CACHE_KEY, JSON.stringify(payload));
    } catch {
      // localStorage can fail in private mode or when quota is full.
    }
  }

  private buildCatalogResponse(
    cards: RiftboundCard[],
    opts: {
      search?: string;
      searchMode?: 'name' | 'ability' | 'all';
      type?: string;
      rarity?: string;
      colors?: string[];
      set?: string;
      energy?: number;
      page?: number;
      pageSize?: number;
      lite?: boolean;
      subtype?: string;
      excludeBattlefields?: boolean;
    },
  ): PaginatedResponse<RiftboundCard | RiftboundCardLite> {
    const filtered = this.filterCatalog(cards, opts);
    const pageSize = Math.max(1, Math.min(RB_MAX_PAGE_SIZE, opts.pageSize ?? RB_DEFAULT_PAGE_SIZE));
    const page = Math.max(1, opts.page ?? 1);
    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    const pageResults = filtered.slice(start, end);

    const results: (RiftboundCard | RiftboundCardLite)[] = opts.lite
      ? pageResults.map(card => this.toLite(card))
      : pageResults;

    return {
      count: filtered.length,
      next: end < filtered.length ? 'cache' : null,
      previous: page > 1 ? 'cache' : null,
      results,
    };
  }

  private filterCatalog(
    cards: RiftboundCard[],
    opts: {
      search?: string;
      searchMode?: 'name' | 'ability' | 'all';
      type?: string;
      rarity?: string;
      colors?: string[];
      set?: string;
      energy?: number;
      subtype?: string;
      excludeBattlefields?: boolean;
    },
  ): RiftboundCard[] {
    const q = (opts.search || '').trim().toLowerCase();
    const mode = opts.searchMode ?? 'all';
    const selectedColors = new Set((opts.colors || []).map(c => c.toLowerCase()));
    const subtype = (opts.subtype || '').trim().toLowerCase();

    return cards.filter(card => {
      if (opts.type) {
        if (opts.type === 'champion') {
          const namePart = (card.name || '').includes(',')
            ? (card.name || '').split(',')[0].trim().toLowerCase()
            : '';
          const hasChampionSubtype = (card.subtypes || []).some(s => (s || '').toLowerCase() === namePart);
          if (!(card.card_type === 'unit' && !!namePart && hasChampionSubtype)) {
            return false;
          }
        } else if (card.card_type !== opts.type) {
          return false;
        }
      }

      if (opts.rarity && card.rarity !== opts.rarity) return false;
      if (opts.set && (card.set?.code || '').toUpperCase() !== opts.set.toUpperCase()) return false;
      if (opts.energy !== undefined && card.energy !== opts.energy) return false;

      if (subtype) {
        const hasSubtype = (card.subtypes || []).some(s => (s || '').toLowerCase() === subtype);
        if (!hasSubtype) return false;
      }

      if (opts.excludeBattlefields && card.card_type === 'battlefield') return false;
      if (selectedColors.size > 0) {
        if (card.card_type === 'battlefield' && !opts.excludeBattlefields) {
          // Keep battlefields visible when filtering by colors, same as backend.
        } else {
          const hasAnyColor = (card.colors || []).some(c => selectedColors.has((c || '').toLowerCase()));
          if (!hasAnyColor) return false;
        }
      }

      if (!q) return true;
      const name = (card.name || '').toLowerCase();
      const number = (card.card_number || '').toLowerCase();
      const text = (card.description || '').toLowerCase();

      if (mode === 'name') return name.includes(q) || number.includes(q);
      if (mode === 'ability') return text.includes(q);
      return name.includes(q) || number.includes(q) || text.includes(q);
    });
  }

  private toLite(card: RiftboundCard): RiftboundCardLite {
    return {
      id: card.id,
      card_number: card.card_number,
      name: card.name,
      card_type: card.card_type,
      rarity: card.rarity,
      colors: card.colors,
      energy: card.energy,
      power: card.power,
      might: card.might,
      image: card.image,
      description: card.description,
      subtypes: card.subtypes,
    };
  }

  getCard(numberOrId: string | number): Observable<RiftboundCard> {
    const params = new HttpParams().set('source', 'riftcodex');
    return this.http.get<RiftboundCard>(`${this.base}/cards/${numberOrId}/`, { params });
  }

  // ── Sets / formatos / iconos (caché en memoria) ──
  listSets(): Observable<RiftboundSet[]> {
    if (!this.sets$) {
      this.sets$ = this.http.get<PaginatedResponse<RiftboundSet> | RiftboundSet[]>(
        `${this.base}/sets/`,
      ).pipe(
        tap(),
        shareReplay({ bufferSize: 1, refCount: false }),
        // normaliza paginado
      ) as unknown as Observable<RiftboundSet[]>;
    }
    return this.sets$;
  }

  listFormats(): Observable<RiftboundFormat[]> {
    if (!this.formats$) {
      this.formats$ = this.http
        .get<PaginatedResponse<RiftboundFormat> | RiftboundFormat[]>(`${this.base}/formats/`)
        .pipe(shareReplay({ bufferSize: 1, refCount: false })) as unknown as Observable<RiftboundFormat[]>;
    }
    return this.formats$;
  }

  listIcons(kind?: string): Observable<RiftboundIcon[]> {
    let params = new HttpParams();
    if (kind) params = params.set('kind', kind);
    return this.http.get<PaginatedResponse<RiftboundIcon> | RiftboundIcon[]>(
      `${this.base}/icons/`, { params },
    ) as unknown as Observable<RiftboundIcon[]>;
  }

  // ── Banlist ──
  listBanlist(format: string = 'standard'): Observable<PaginatedResponse<RiftboundBanlistEntry>> {
    // 'format' es reservado por DRF, usar 'fmt'
    return this.http.get<PaginatedResponse<RiftboundBanlistEntry>>(
      `${this.base}/banlist/`, { params: new HttpParams().set('fmt', format) },
    );
  }

  // ── Mazos ──
  listDecks(opts: { mine?: boolean; search?: string; page?: number } = {}):
    Observable<PaginatedResponse<RiftboundDeck>> {
    let params = new HttpParams();
    if (opts.mine) params = params.set('mine', '1');
    if (opts.search) params = params.set('search', opts.search);
    if (opts.page) params = params.set('page', String(opts.page));
    return this.http.get<PaginatedResponse<RiftboundDeck>>(`${this.base}/decks/`, { params });
  }

  getDeck(id: number): Observable<RiftboundDeck> {
    return this.http.get<RiftboundDeck>(`${this.base}/decks/${id}/`);
  }

  createDeck(data: Partial<RiftboundDeck>): Observable<RiftboundDeck> {
    return this.http.post<RiftboundDeck>(`${this.base}/decks/`, data);
  }

  updateDeck(id: number, data: Partial<RiftboundDeck>): Observable<RiftboundDeck> {
    return this.http.put<RiftboundDeck>(`${this.base}/decks/${id}/`, data);
  }

  patchDeck(id: number, data: Partial<RiftboundDeck>): Observable<RiftboundDeck> {
    return this.http.patch<RiftboundDeck>(`${this.base}/decks/${id}/`, data);
  }

  deleteDeck(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/decks/${id}/`);
  }

  validateDeck(id: number) {
    return this.http.get(`${this.base}/decks/${id}/validate/`);
  }

  // ── Carpeta ──
  listCollection(opts: { search?: string; page?: number; selling?: boolean; page_size?: number } = {}): Observable<PaginatedResponse<RiftboundCollectionEntry>> {
    let params = new HttpParams();
    if (opts.search) params = params.set('search', opts.search);
    if (opts.page) params = params.set('page', String(opts.page));
    if (opts.selling) params = params.set('selling', '1');
    if (opts.page_size) params = params.set('page_size', String(opts.page_size));
    return this.http.get<PaginatedResponse<RiftboundCollectionEntry>>(
      `${this.base}/collection/`, { params },
    );
  }

  batchUpsertCollection(items: Partial<RiftboundCollectionEntry>[]): Observable<{ updated: number }> {
    // El backend espera el array directamente, no envuelto en {items}.
    return this.http.post<{ updated: number }>(`${this.base}/collection/batch-upsert/`, items);
  }

  bulkImport(text: string, mode: 'add' | 'set' = 'add'): Observable<RiftboundBulkImportResult> {
    return this.http.post<RiftboundBulkImportResult>(`${this.base}/collection/bulk-import/`, { text, mode });
  }

  upsertCollection(data: Partial<RiftboundCollectionEntry>): Observable<RiftboundCollectionEntry | { deleted: true; card: number }> {
    return this.http.post<any>(`${this.base}/collection/upsert/`, data);
  }

  /** Sube una foto real de la carta a Cloudinary y la asocia a la entrada Riftbound.
   *  `slot` indica en qué campo guardar (1 = photo_url, 2 = photo_url_2). */
  uploadCollectionPhoto(
    cardId: number, file: File, slot: 1 | 2 = 1, isFoil: boolean = false,
  ): Observable<RiftboundCollectionEntry> {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('upload_preset', environment.cloudinaryUploadPreset);
    fd.append('folder', 'deckshado/riftbound/store_card_photos');
    const field = slot === 2 ? 'photo_url_2' : 'photo_url';
    return this.http.post<any>(
      `https://api.cloudinary.com/v1_1/${environment.cloudinaryCloudName}/image/upload`, fd,
    ).pipe(
      switchMap(res => this.http.post<RiftboundCollectionEntry>(
        `${this.base}/collection/upsert/`,
        { card: cardId, is_foil: isFoil, [field]: res.secure_url },
      )),
    );
  }

  deleteCollection(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/collection/${id}/`);
  }

  carpetaIds(): Observable<RiftboundCarpetaIds> {
    return this.http.get<RiftboundCarpetaIds>(`${this.base}/collection/ids/`);
  }

  collectionStats(): Observable<RiftboundCollectionStats> {
    return this.http.get<RiftboundCollectionStats>(`${this.base}/collection/stats/`);
  }

  // ── Wishlist ──
  listWishlist(opts: { search?: string; page?: number } = {}): Observable<PaginatedResponse<RiftboundWishlistEntry>> {
    let params = new HttpParams();
    if (opts.search) params = params.set('search', opts.search);
    if (opts.page) params = params.set('page', String(opts.page));
    return this.http.get<PaginatedResponse<RiftboundWishlistEntry>>(
      `${this.base}/wishlist/`, { params },
    );
  }

  toggleWishlist(cardId: number): Observable<{ wishlisted: boolean; card: number }> {
    return this.http.post<{ wishlisted: boolean; card: number }>(
      `${this.base}/wishlist/toggle/`, { card: cardId },
    );
  }

  updateWishlistQty(cardId: number, qty: number): Observable<RiftboundWishlistEntry> {
    return this.http.post<RiftboundWishlistEntry>(
      `${this.base}/wishlist/set-quantity/`, { card: cardId, desired_quantity: qty },
    );
  }

  // ── Binder profile / tienda ──
  getBinderProfile(): Observable<RiftboundBinderProfile> {
    return this.http.get<RiftboundBinderProfile>(`${this.base}/profile/`);
  }

  updateBinderProfile(patch: Partial<RiftboundBinderProfile>): Observable<RiftboundBinderProfile> {
    return this.http.patch<RiftboundBinderProfile>(`${this.base}/profile/`, patch);
  }

  uploadBinderAvatar(file: File): Observable<RiftboundBinderProfile> {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('upload_preset', environment.cloudinaryUploadPreset);
    fd.append('folder', 'deckshado/binder_avatars');
    return this.http.post<any>(
      `https://api.cloudinary.com/v1_1/${environment.cloudinaryCloudName}/image/upload`, fd,
    ).pipe(
      switchMap(res => this.http.post<RiftboundBinderProfile>(
        `${this.base}/profile/avatar/`, { avatar_url: res.secure_url },
      )),
    );
  }

  myShareToken(): Observable<{ share_token: string; store_slug: string; is_store_public: boolean }> {
    return this.http.get<{ share_token: string; store_slug: string; is_store_public: boolean }>(`${this.base}/share-token/`);
  }

  regenerateShareToken(): Observable<{ share_token: string }> {
    return this.http.post<{ share_token: string }>(`${this.base}/share-token/regenerate/`, {});
  }

  listStores(opts: { search?: string; country?: string; ordering?: string; page?: number } = {}):
    Observable<PaginatedResponse<RiftboundPublicBinderProfile>> {
    let params = new HttpParams();
    if (opts.search) params = params.set('search', opts.search);
    if (opts.country) params = params.set('country', opts.country);
    if (opts.ordering) params = params.set('ordering', opts.ordering);
    if (opts.page) params = params.set('page', String(opts.page));
    return this.http.get<PaginatedResponse<RiftboundPublicBinderProfile>>(`${this.base}/stores/`, { params });
  }

  getPublicStore(token: string, opts: {
    search?: string; set?: string; type?: string; rarity?: string;
    condition?: string; foil?: '0' | '1'; price_min?: number; price_max?: number;
    only_priced?: '1'; ordering?: string; page?: number;
  } = {}): Observable<PaginatedResponse<RiftboundCollectionEntry> & {
    store: RiftboundPublicBinderProfile; store_owner: string; store_avatar: string; store_binder_avatar: string;
  }> {
    let params = new HttpParams();
    for (const [k, v] of Object.entries(opts)) {
      if (v !== undefined && v !== null && v !== '') params = params.set(k, String(v));
    }
    return this.http.get<any>(`${this.base}/store/${token}/`, { params });
  }

  getPublicWishlist(token: string, opts: { search?: string; ordering?: string; page?: number } = {})
    : Observable<PaginatedResponse<RiftboundWishlistEntry> & { store: RiftboundPublicBinderProfile }> {
    let params = new HttpParams();
    for (const [k, v] of Object.entries(opts)) {
      if (v !== undefined && v !== null && v !== '') params = params.set(k, String(v));
    }
    return this.http.get<any>(`${this.base}/wishlist-public/${token}/`, { params });
  }
}
