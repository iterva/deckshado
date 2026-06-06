import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, shareReplay, tap } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

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

const TCG_SEARCH_URL = 'https://mp-search-api.tcgplayer.com/v1/search/request';
const PRODUCT_LINE = 'riftbound-league-of-legends-trading-card-game';

@Injectable({ providedIn: 'root' })
export class TcgPlayerService {
  private http = inject(HttpClient);

  /** Cache local para evitar requests repetidos en la misma sesión */
  private cache = new Map<string, { ts: number; data: TcgPlayerPrice }>();
  private readonly CACHE_TTL = 15 * 60 * 1000; // 15 minutos

  /** Requests en curso para dedup */
  private inflight = new Map<string, Observable<TcgPlayerPrice>>();

  /**
   * Obtiene precio de una carta por nombre directamente desde TCGPlayer.
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

    const body = {
      algorithm: '',
      from: 0,
      size: 10,
      filters: {
        term: { productLineName: [PRODUCT_LINE] },
        range: {},
        match: {},
      },
      listingSearch: {
        filters: {
          term: { sellerStatus: 'Live', channelId: 0 },
          range: { quantity: { gte: 1 } },
          exclude: { channelExclusion: 0 },
        },
      },
      context: { cart: {}, shippingCountry: 'US' },
      settings: { useFuzzySearch: true, didYouMean: {} },
      sort: {},
    };

    const url = `${TCG_SEARCH_URL}?q=${encodeURIComponent(cardName)}&isList=false`;

    const req$ = this.http.post<any>(url, body).pipe(
      map(data => this.extractPrice(cardName, data)),
      tap(price => {
        this.cache.set(key, { ts: Date.now(), data: price });
        this.inflight.delete(key);
      }),
      catchError(() => {
        this.inflight.delete(key);
        const fallback: TcgPlayerPrice = { card_name: cardName, market_price: null };
        // Cache negativo corto (2 min)
        this.cache.set(key, { ts: Date.now() - this.CACHE_TTL + 120_000, data: fallback });
        return of(fallback);
      }),
      shareReplay(1),
    );

    this.inflight.set(key, req$);
    return req$;
  }

  private extractPrice(cardName: string, data: any): TcgPlayerPrice {
    const results = data?.results?.[0]?.results ?? [];
    const nameLower = cardName.toLowerCase().trim();

    // Buscar match exacto primero, luego parcial
    let best: any = null;
    for (const item of results) {
      const productName = (item.productName || '').toLowerCase();
      if (productName === nameLower) {
        best = item;
        break;
      }
      if (productName.includes(nameLower) && !best) {
        best = item;
      }
    }

    // Si no hay match por nombre, tomar el primero
    if (!best && results.length > 0) {
      best = results[0];
    }

    if (!best) {
      return { card_name: cardName, market_price: null };
    }

    return {
      card_name: cardName,
      product_name: best.productName || '',
      market_price: best.marketPrice ?? null,
      low_price: best.lowPrice ?? null,
      mid_price: best.midPrice ?? null,
      high_price: best.highPrice ?? null,
      product_url: best.productId
        ? `https://www.tcgplayer.com/product/${best.productId}`
        : null,
      image_url: best.imageUrl || null,
    };
  }

  clearCache(): void {
    this.cache.clear();
  }
}
    this.cache.clear();
  }
}
