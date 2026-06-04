import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of, tap, shareReplay, catchError } from 'rxjs';
import { environment } from '../../environments/environment';
import { Card, Edition, Format, Race, CardType, Rarity, BanlistEntry, PaginatedResponse } from '../models';

@Injectable({ providedIn: 'root' })
export class CardService {
  private readonly apiUrl = `${environment.apiUrl}/cards`;

  private editions$: Observable<Edition[]> | null = null;
  private formats$: Observable<Format[]> | null = null;
  private types$: Observable<CardType[]> | null = null;
  private races$: Observable<Race[]> | null = null;
  private rarities$: Observable<Rarity[]> | null = null;
  private cardsCache = new Map<string, { data: PaginatedResponse<Card>; ts: number }>();
  private readonly cacheTtl = 5 * 60 * 1000; // 5 min

  constructor(private http: HttpClient) {}

  getCards(filters: {
    edition?: string;
    type?: string;
    race?: string;
    rarity?: string;
    search?: string;
    ability_search?: string;
    format?: string;
    page?: number;
    deck_race?: string;
    sub_fmt?: string;
    cost?: string;
    exclude_editions?: string;
  } = {}): Observable<PaginatedResponse<Card>> {
    const key = JSON.stringify(filters);
    const cached = this.cardsCache.get(key);
    if (cached && Date.now() - cached.ts < this.cacheTtl) {
      return of(cached.data);
    }
    let params = new HttpParams();
    if (filters.edition) params = params.set('edition', filters.edition);
    if (filters.type) params = params.set('type', filters.type);
    if (filters.race) params = params.set('race', filters.race);
    if (filters.rarity) params = params.set('rarity', filters.rarity);
    if (filters.search) params = params.set('search', filters.search);
    if (filters.ability_search) params = params.set('ability_search', filters.ability_search);
    if (filters.format) params = params.set('fmt', filters.format);
    if (filters.page) params = params.set('page', filters.page.toString());
    if (filters.deck_race) params = params.set('deck_race', filters.deck_race);
    if (filters.sub_fmt) params = params.set('sub_fmt', filters.sub_fmt);
    if (filters.cost) params = params.set('cost', filters.cost);
    if (filters.exclude_editions) params = params.set('exclude_editions', filters.exclude_editions);
    return this.http.get<PaginatedResponse<Card>>(this.apiUrl + '/', { params }).pipe(
      tap(data => this.cardsCache.set(key, { data, ts: Date.now() })),
      catchError(err => {
        this.cardsCache.delete(key);
        throw err;
      }),
    );
  }

  getCard(id: number): Observable<Card> {
    return this.http.get<Card>(`${this.apiUrl}/${id}/`);
  }

  getEditions(): Observable<Edition[]> {
    if (!this.editions$) {
      this.editions$ = this.http.get<Edition[]>(`${this.apiUrl}/editions/`).pipe(shareReplay(1));
    }
    return this.editions$;
  }

  getFormats(): Observable<Format[]> {
    if (!this.formats$) {
      this.formats$ = this.http.get<Format[]>(`${this.apiUrl}/formats/`).pipe(shareReplay(1));
    }
    return this.formats$;
  }

  getRaces(): Observable<Race[]> {
    if (!this.races$) {
      this.races$ = this.http.get<Race[]>(`${this.apiUrl}/races/`).pipe(shareReplay(1));
    }
    return this.races$;
  }

  getTypes(): Observable<CardType[]> {
    if (!this.types$) {
      this.types$ = this.http.get<CardType[]>(`${this.apiUrl}/types/`).pipe(shareReplay(1));
    }
    return this.types$;
  }

  getRarities(): Observable<Rarity[]> {
    if (!this.rarities$) {
      this.rarities$ = this.http.get<Rarity[]>(`${this.apiUrl}/rarities/`).pipe(shareReplay(1));
    }
    return this.rarities$;
  }

  private banlistCache = new Map<string, { data: BanlistEntry[]; ts: number }>();

  getBanlist(fmt: string, sub?: string): Observable<BanlistEntry[]> {
    const key = `${fmt}|${sub || ''}`;
    const cached = this.banlistCache.get(key);
    if (cached && Date.now() - cached.ts < this.cacheTtl) {
      return of(cached.data);
    }
    let params = new HttpParams().set('fmt', fmt);
    if (sub) params = params.set('sub', sub);
    return this.http.get<BanlistEntry[]>(`${this.apiUrl}/banlist/`, { params }).pipe(
      tap(data => this.banlistCache.set(key, { data, ts: Date.now() })),
    );
  }

  clearCache() {
    this.cardsCache.clear();
    this.banlistCache.clear();
    this.editions$ = null;
    this.formats$ = null;
    this.types$ = null;
    this.races$ = null;
    this.rarities$ = null;
  }
}
