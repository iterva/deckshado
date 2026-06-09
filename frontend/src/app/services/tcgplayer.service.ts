import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of, shareReplay, tap } from 'rxjs';
import { catchError } from 'rxjs/operators';
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
   * Obtiene precio de una carta por nombre via backend proxy.
   */
  getPrice(cardName: string, force = false): Observable<TcgPlayerPrice> {
    const key = cardName.toLowerCase().trim();
    const now = Date.now();

    if (!force) {
      const cached = this.cache.get(key);
      if (cached && (now - cached.ts) < this.CACHE_TTL) {
        return of(cached.data);
      }
    }

    if (!force && this.inflight.has(key)) {
      return this.inflight.get(key)!;
    }

    if (force) {
      this.inflight.delete(key);
    }

    const params = new HttpParams().set('card_name', cardName);
    const req$ = this.http.get<TcgPlayerPrice>(`${this.base}/price/`, { params }).pipe(
      tap(data => {
        // No cachear N/A para no “pegar” fallos transitorios de red/backend.
        if (data.market_price != null) {
          this.cache.set(key, { ts: Date.now(), data });
        }
        this.inflight.delete(key);
      }),
      catchError(() => {
        this.inflight.delete(key);
        const fallback: TcgPlayerPrice = { card_name: cardName, market_price: null };
        return of(fallback);
      }),
      shareReplay(1),
    );

    this.inflight.set(key, req$);
    return req$;
  }

  clearCache(): void {
    this.cache.clear();
  }
}
