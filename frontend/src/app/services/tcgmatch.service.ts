import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of, shareReplay, tap } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface TcgmatchPrice {
  card_name: string;
  product_name?: string;
  market_price: number | null;
  low_price?: number | null;
  currency?: string;
  product_url?: string | null;
  image_url?: string | null;
}

@Injectable({ providedIn: 'root' })
export class TcgmatchService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/riftbound/tcgmatch`;

  private cache = new Map<string, { ts: number; data: TcgmatchPrice }>();
  private readonly CACHE_TTL = 15 * 60 * 1000;

  private inflight = new Map<string, Observable<TcgmatchPrice>>();

  getPrice(cardName: string, force = false): Observable<TcgmatchPrice> {
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
    const req$ = this.http.get<TcgmatchPrice>(`${this.base}/price/`, { params }).pipe(
      tap(data => {
        if (data.market_price != null || data.low_price != null) {
          this.cache.set(key, { ts: Date.now(), data });
        }
        this.inflight.delete(key);
      }),
      catchError(() => {
        this.inflight.delete(key);
        const fallback: TcgmatchPrice = {
          card_name: cardName,
          market_price: null,
          low_price: null,
          currency: 'CLP',
        };
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
