import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of, shareReplay, tap } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface TcgPlayerPrice {
  card_name: string;
  product_name?: string;
  market_price: number | null;
  low_price?: number | null;
  mid_price?: number | null;
  high_price?: number | null;
  product_url?: string | null;
  image_url?: string | null;
}

@Injectable({ providedIn: 'root' })
export class TcgPlayerService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/riftbound/tcgplayer`;

  /** Cache local para evitar requests repetidos en la misma sesión */
  private cache = new Map<string, { ts: number; data: TcgPlayerPrice }>();
  private readonly CACHE_TTL = 15 * 60 * 1000; // 15 minutos

  /** Requests en curso para dedup */
  private inflight = new Map<string, Observable<TcgPlayerPrice>>();

  /**
   * Obtiene precio de una carta por nombre.
   * Devuelve desde caché si es reciente.
   */
  getPrice(cardName: string): Observable<TcgPlayerPrice> {
    const key = cardName.toLowerCase().trim();
    const now = Date.now();

    // Check cache
    const cached = this.cache.get(key);
    if (cached && (now - cached.ts) < this.CACHE_TTL) {
      return of(cached.data);
    }

    // Check inflight dedup
    if (this.inflight.has(key)) {
      return this.inflight.get(key)!;
    }

    const params = new HttpParams().set('card_name', cardName);
    const req$ = this.http.get<TcgPlayerPrice>(`${this.base}/price/`, { params }).pipe(
      tap(data => {
        this.cache.set(key, { ts: Date.now(), data });
        this.inflight.delete(key);
      }),
      catchError(() => {
        this.inflight.delete(key);
        return of({ card_name: cardName, market_price: null });
      }),
      shareReplay(1),
    );

    this.inflight.set(key, req$);
    return req$;
  }

  /**
   * Obtiene precios para múltiples cartas de golpe (máx 20).
   */
  getPricesBatch(cardNames: string[]): Observable<TcgPlayerPrice[]> {
    if (!cardNames.length) return of([]);

    // Separar los que están en caché y los que no
    const now = Date.now();
    const fromCache: TcgPlayerPrice[] = [];
    const toFetch: string[] = [];

    for (const name of cardNames) {
      const key = name.toLowerCase().trim();
      const cached = this.cache.get(key);
      if (cached && (now - cached.ts) < this.CACHE_TTL) {
        fromCache.push(cached.data);
      } else {
        toFetch.push(name);
      }
    }

    if (!toFetch.length) {
      return of(fromCache);
    }

    return this.http.post<{ prices: TcgPlayerPrice[] }>(
      `${this.base}/prices-batch/`,
      { card_names: toFetch },
    ).pipe(
      map(res => {
        for (const p of res.prices) {
          this.cache.set(p.card_name.toLowerCase().trim(), { ts: Date.now(), data: p });
        }
        return [...fromCache, ...res.prices];
      }),
      catchError(() => of(fromCache)),
    );
  }

  clearCache(): void {
    this.cache.clear();
  }
}
