import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, shareReplay } from 'rxjs';
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

export interface RiftcodexSyncStatus {
  provider: string;
  key: string;
  configured: boolean;
  status: 'ok' | 'error' | 'never_run' | string;
  message?: string;
  last_cursor?: string | null;
  last_started_at?: string | null;
  last_success_at?: string | null;
  last_success_age_hours?: number | null;
  last_stats?: Record<string, any>;
  last_error?: string;
  updated_at?: string | null;
}

export interface RiftcodexIndexPayload {
  type: string;
  total: number;
  values: Array<string | number>;
  source?: 'cache' | 'remote' | 'local-fallback' | string;
  generated_at?: string;
  upstream_error?: string;
}

export interface RiftcodexAuditStatus {
  provider: string;
  key: string;
  configured: boolean;
  status: 'ok' | 'error' | 'never_run' | string;
  message?: string;
  last_started_at?: string | null;
  last_success_at?: string | null;
  last_stats?: Record<string, any>;
  last_error?: string;
  updated_at?: string | null;
}

export interface RiftcodexOperationResult {
  ok: boolean;
  command: string;
  output: string;
  error?: string;
  run_id?: number;
  rerun_of?: number;
}

export interface RiftcodexOpsRunItem {
  id: number;
  kind: 'sync' | 'audit' | string;
  command: string;
  status: 'running' | 'success' | 'error' | string;
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
  requested_by?: string | null;
  args?: Record<string, any>;
  error?: string;
  output?: string;
  output_excerpt?: string;
}

export interface RiftcodexOpsPagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
  kind?: string | null;
  status?: string | null;
  q?: string | null;
}

export interface RiftcodexOpsOverview {
  sync: {
    provider?: string;
    key?: string;
    configured?: boolean;
    status: string;
    last_cursor?: string | null;
    last_success_at?: string | null;
    last_started_at?: string | null;
    last_success_age_hours?: number | null;
    last_stats?: Record<string, any>;
    last_error?: string;
  };
  audit: {
    provider?: string;
    key?: string;
    configured?: boolean;
    status: string;
    last_success_at?: string | null;
    last_started_at?: string | null;
    last_stats?: Record<string, any>;
    last_error?: string;
  };
  runs: RiftcodexOpsRunItem[];
  runs_pagination?: RiftcodexOpsPagination;
}

@Injectable({ providedIn: 'root' })
export class RiftboundService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/riftbound`;

  private formats$: Observable<RiftboundFormat[]> | null = null;
  private sets$: Observable<RiftboundSet[]> | null = null;
  private icons$: Observable<RiftboundIcon[]> | null = null;

  // ── Cartas ──
  listCards(opts: {
    search?: string;
    searchMode?: 'name' | 'ability' | 'all';
    hybrid?: boolean;
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
    return this.fetchCardsHttp(opts);
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
    if (opts.search) {
      const mode = opts.searchMode ?? 'all';
      if (mode === 'name') params = params.set('name_search', opts.search);
      else if (mode === 'ability') params = params.set('ability_search', opts.search);
      else {
        params = params.set('search', opts.search);
        if (opts.hybrid) params = params.set('hybrid', '1');
      }
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

  getCard(numberOrId: string | number): Observable<RiftboundCard> {
    return this.http.get<RiftboundCard>(`${this.base}/cards/${numberOrId}/`);
  }

  // ── Sets / formatos / iconos (caché en memoria) ──
  listSets(): Observable<RiftboundSet[]> {
    if (!this.sets$) {
      this.sets$ = this.http.get<PaginatedResponse<RiftboundSet> | RiftboundSet[]>(
        `${this.base}/sets/`,
      ).pipe(
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

  /** Sube una foto real de la carta via backend y la asocia a la entrada Riftbound.
   *  `slot` indica en qué campo guardar (1 = photo_url, 2 = photo_url_2). */
  uploadCollectionPhoto(
    cardId: number, file: File, slot: 1 | 2 = 1, isFoil: boolean = false,
  ): Observable<RiftboundCollectionEntry> {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('card', String(cardId));
    fd.append('slot', String(slot));
    fd.append('is_foil', isFoil ? '1' : '0');
    return this.http.post<RiftboundCollectionEntry>(`${this.base}/collection/upsert/`, fd);
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
    return this.http.post<RiftboundBinderProfile>(`${this.base}/profile/avatar/`, fd);
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

  getSyncStatus(): Observable<RiftcodexSyncStatus> {
    return this.http.get<RiftcodexSyncStatus>(`${this.base}/sync/status/`);
  }

  getRiftcodexIndex(indexType: string): Observable<RiftcodexIndexPayload> {
    return this.http.get<RiftcodexIndexPayload>(`${this.base}/index/${encodeURIComponent(indexType)}/`);
  }

  getAuditStatus(): Observable<RiftcodexAuditStatus> {
    return this.http.get<RiftcodexAuditStatus>(`${this.base}/audit/status/`);
  }

  runSyncOperation(opts: {
    full?: boolean;
    dry_run?: boolean;
    skip_fixes?: boolean;
    size?: number;
    since?: string;
  } = {}): Observable<RiftcodexOperationResult> {
    return this.http.post<RiftcodexOperationResult>(`${this.base}/ops/run-sync/`, opts);
  }

  runAuditOperation(opts: { limit?: number } = {}): Observable<RiftcodexOperationResult> {
    return this.http.post<RiftcodexOperationResult>(`${this.base}/ops/run-audit/`, opts);
  }

  getOpsOverview(opts: {
    kind?: 'sync' | 'audit' | '';
    status?: 'running' | 'success' | 'error' | '';
    q?: string;
    page?: number;
    page_size?: number;
  } = {}): Observable<RiftcodexOpsOverview> {
    let params = new HttpParams();
    if (opts.kind) params = params.set('kind', opts.kind);
    if (opts.status) params = params.set('status', opts.status);
    if (opts.q) params = params.set('q', opts.q);
    if (opts.page) params = params.set('page', String(opts.page));
    if (opts.page_size) params = params.set('page_size', String(opts.page_size));
    return this.http.get<RiftcodexOpsOverview>(`${this.base}/ops/overview/`, { params });
  }

  getOpsRun(runId: number): Observable<RiftcodexOpsRunItem> {
    return this.http.get<RiftcodexOpsRunItem>(`${this.base}/ops/runs/${runId}/`);
  }

  rerunOpsRun(runId: number, overrides: Record<string, any> = {}): Observable<RiftcodexOperationResult> {
    return this.http.post<RiftcodexOperationResult>(`${this.base}/ops/runs/${runId}/rerun/`, overrides);
  }

  downloadAuditCsv(): Observable<Blob> {
    return this.http.get(`${this.base}/audit/export.csv`, { responseType: 'blob' });
  }
}
