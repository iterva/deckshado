import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, shareReplay, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  RiftboundCard, RiftboundCardLite, RiftboundDeck, RiftboundFormat,
  RiftboundBanlistEntry, RiftboundIcon, RiftboundSet, RiftboundCollectionEntry,
} from '../models/riftbound';

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
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
    type?: string;
    rarity?: string;
    colors?: string[];
    set?: string;
    energy?: number;
    page?: number;
    lite?: boolean;
  } = {}): Observable<PaginatedResponse<RiftboundCard | RiftboundCardLite>> {
    let params = new HttpParams();
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
    if (opts.lite) params = params.set('lite', '1');
    return this.http.get<PaginatedResponse<RiftboundCard | RiftboundCardLite>>(
      `${this.base}/cards/`, { params },
    );
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
  listCollection(): Observable<PaginatedResponse<RiftboundCollectionEntry>> {
    return this.http.get<PaginatedResponse<RiftboundCollectionEntry>>(
      `${this.base}/collection/`,
    );
  }

  upsertCollection(data: Partial<RiftboundCollectionEntry>): Observable<RiftboundCollectionEntry> {
    return this.http.post<RiftboundCollectionEntry>(`${this.base}/collection/`, data);
  }

  deleteCollection(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/collection/${id}/`);
  }
}
