import { Component, Input, OnChanges, SimpleChanges, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TcgPlayerService, TcgPlayerPrice } from '../../services/tcgplayer.service';
import { TcgmatchService, TcgmatchPrice } from '../../services/tcgmatch.service';

@Component({
  selector: 'app-tcg-price',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (!showMarketPrice) {
      @if (showLink) {
        <a class="tcg-btn"
           [href]="price()?.product_url || tcgSearchUrl"
           target="_blank" rel="noopener noreferrer">
          Ir a TCGPlayer
        </a>
      }
    } @else if (loading()) {
      <span class="tcg-price loading" [class.compact]="compact">
        <span class="tcg-spinner"></span>
      </span>
    } @else if (compact) {
      @if (price()?.market_price != null) {
        <div class="tcg-compact-row">
          <span class="tcg-price compact" [title]="'TCGPlayer: Precio de mercado $' + price()!.market_price!.toFixed(2)">
            <span class="tcg-icon">💲</span>
            <span class="tcg-label">Precio de mercado</span>
            <span class="tcg-amount">\${{ price()!.market_price!.toFixed(2) }}</span>
          </span>
          @if (showLink) {
            <a class="tcg-btn"
               [href]="price()!.product_url || tcgSearchUrl"
               target="_blank" rel="noopener noreferrer">
              Ir a TCGPlayer
            </a>
          }
        </div>
      } @else if (!hideIfEmpty) {
        <div class="tcg-compact-row">
          <span class="tcg-price no-price compact">
            <span class="tcg-icon">💲</span>
            <span class="tcg-label">Precio de mercado</span>
            <span class="tcg-na">N/A</span>
          </span>
          @if (showLink) {
            <a class="tcg-btn"
               [href]="tcgSearchUrl"
               target="_blank" rel="noopener noreferrer">
              Ir a TCGPlayer
            </a>
          }
        </div>
      }
    } @else if (price()?.market_price != null || !hideIfEmpty) {
      <div class="tcg-market-block">
        <div class="tcg-market-stack">
          <div class="tcg-price detailed">
            <div class="tcg-header">
              <span class="tcg-icon">💲</span>
              <span>TCGPlayer</span>
            </div>
            <div class="tcg-rows">
              <div class="tcg-row">
                <span>Precio de mercado</span>
                @if (price()?.market_price != null) {
                  <strong>\${{ price()!.market_price!.toFixed(2) }}</strong>
                } @else {
                  <strong class="tcg-na">N/A</strong>
                }
              </div>
              @if (price()?.low_price != null) {
                <div class="tcg-row">
                  <span>Low</span>
                  <span>\${{ price()!.low_price!.toFixed(2) }}</span>
                </div>
              }
              @if (price()?.mid_price != null) {
                <div class="tcg-row">
                  <span>Mid</span>
                  <span>\${{ price()!.mid_price!.toFixed(2) }}</span>
                </div>
              }
            </div>
          </div>

          @if (showExternalMarkets) {
            <div class="tcg-price detailed tcg-alt-card">
              <div class="tcg-header">
                <span class="tcg-icon">🇨🇱</span>
                <span>TCGMatch</span>
              </div>
              @if (tcgmatchLoading()) {
                <span class="tcg-price loading">
                  <span class="tcg-spinner"></span>
                </span>
              } @else {
                <div class="tcg-rows">
                  <div class="tcg-row">
                    <span>Precio de mercado</span>
                    <strong class="tcg-clp">{{ formatClp(tcgmatchPrice()?.market_price) }}</strong>
                  </div>
                  <div class="tcg-row">
                    <span>Desde</span>
                    <span class="tcg-clp">{{ formatClp(tcgmatchPrice()?.low_price) }}</span>
                  </div>
                </div>
              }
            </div>

            <div class="tcg-price detailed tcg-alt-card">
              <div class="tcg-header">
                <span class="tcg-icon">🇪🇺</span>
                <span>Cardmarket</span>
              </div>
              <div class="tcg-rows">
                <div class="tcg-row">
                  <span>Precio</span>
                  <strong class="tcg-na">N/A</strong>
                </div>
              </div>
            </div>
          }
        </div>

        @if (showLink) {
          <div class="tcg-actions">
            <a class="tcg-btn-full"
               [href]="price()?.product_url || tcgSearchUrl"
               target="_blank" rel="noopener noreferrer">
              Ir a TCGPlayer
            </a>
            @if (showExternalMarkets) {
              <a class="tcg-btn-full"
                 [href]="tcgmatchPrice()?.product_url || tcgmatchSearchUrl"
                 target="_blank" rel="noopener noreferrer">
                Ir a TCGMatch
              </a>
              <a class="tcg-btn-full"
                 [href]="cardmarketSearchUrl"
                 target="_blank" rel="noopener noreferrer">
                Buscar en Cardmarket
              </a>
            }
          </div>
        }
      </div>
    }
  `,
  styles: [`
    :host { display: block; max-width: 100%; min-width: 0; }

    .tcg-price { display: inline-flex; align-items: center; gap: 4px; font-size: .82rem; }
    .tcg-price.loading { color: #888; }
    .tcg-price.no-price { color: #666; }
    .tcg-compact-row {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 6px;
      width: 100%;
      max-width: 100%;
      min-width: 0;
    }

    .tcg-spinner {
      width: 12px; height: 12px; border: 2px solid #333;
      border-top-color: #1a9c5b; border-radius: 50%;
      animation: tcg-spin .7s linear infinite;
    }
    @keyframes tcg-spin { to { transform: rotate(360deg); } }

    .tcg-price.compact {
      color: #1a9c5b; font-weight: 600;
      padding: 2px 6px; border-radius: 4px;
      background: rgba(26, 156, 91, 0.08);
      border: 1px solid rgba(26, 156, 91, 0.2);
      transition: all .15s;
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) auto;
      align-items: center;
      gap: 5px;
      width: 100%;
      max-width: 100%;
      min-width: 0;
      overflow: hidden;
    }
    .tcg-icon { font-size: .9rem; }
    .tcg-label {
      font-size: .75rem;
      opacity: .95;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .tcg-amount { font-variant-numeric: tabular-nums; white-space: nowrap; }
    .tcg-na { color: #888; font-size: .75rem; }
    @media (max-width: 640px) {
      .tcg-price.compact { padding: 2px 5px; font-size: .76rem; }
      .tcg-label { display: none; }
    }

    .tcg-market-block {
      display: flex;
      flex-direction: column;
      gap: 10px;
      width: 100%;
      min-width: 0;
    }
    .tcg-price.detailed {
      display: flex; flex-direction: column; gap: 6px;
      background: #1a1a2e; border: 1px solid #2a2a4e;
      border-radius: 8px; padding: 8px 12px; min-width: 0;
      height: 100%;
      box-sizing: border-box;
    }
    .tcg-market-stack {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      align-items: stretch;
      gap: 8px;
      width: 100%;
      min-width: 0;
    }
    .tcg-market-stack .tcg-rows {
      flex: 1;
      min-height: 0;
    }
    .tcg-actions {
      display: flex;
      flex-direction: column;
      gap: 8px;
      width: 100%;
    }
    .tcg-alt-card {
      background: #17172a;
      border-color: #293255;
    }
    .tcg-header {
      display: flex; align-items: center; gap: 6px;
      font-size: .75rem; color: #aaa;
      border-bottom: 1px solid #2a2a4e; padding-bottom: 4px;
    }
    .tcg-rows { display: flex; flex-direction: column; gap: 2px; }
    .tcg-row {
      display: flex; justify-content: space-between;
      font-size: .8rem; padding: 2px 0;
      gap: 12px;
    }
    .tcg-row strong { color: #1a9c5b; }
    .tcg-row .tcg-clp { color: #3bc4ff; }

    .tcg-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: .75rem;
      color: #fff;
      text-decoration: none;
      background: linear-gradient(135deg, #2d79c7, #1f5d9e);
      border: 1px solid rgba(255, 255, 255, .16);
      border-radius: 6px;
      padding: 3px 8px;
      box-sizing: border-box;
      text-align: center;
      transition: transform .12s ease, filter .12s ease;
      width: 100%;
      min-height: 34px;
      white-space: normal;
    }
    .tcg-btn:hover { transform: translateY(-1px); filter: brightness(1.05); }
    .tcg-btn-full {
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: .82rem;
      font-weight: 600;
      color: #fff;
      text-decoration: none;
      background: linear-gradient(135deg, #2d79c7, #1f5d9e);
      border: 1px solid rgba(255, 255, 255, .16);
      border-radius: 8px;
      padding: 10px 14px;
      box-sizing: border-box;
      text-align: center;
      transition: transform .12s ease, filter .12s ease;
      width: 100%;
    }
    .tcg-btn-full:hover { transform: translateY(-1px); filter: brightness(1.05); }
    @media (max-width: 640px) {
      .tcg-btn { font-size: .72rem; padding: 3px 7px; }
      .tcg-btn-full { font-size: .78rem; padding: 9px 12px; }
      .tcg-price.detailed { padding: 6px 8px; }
      .tcg-header { font-size: .68rem; }
      .tcg-row {
        flex-direction: column;
        align-items: flex-start;
        font-size: .72rem;
        gap: 1px;
        padding: 1px 0;
      }
    }
  `],
})
export class TcgPriceComponent implements OnChanges {
  @Input({ required: true }) cardName!: string;
  @Input() compact = true;
  @Input() showLink = true;
  @Input() showMarketPrice = true;
  @Input() hideIfEmpty = false;
  @Input() showExternalMarkets = true;

  private tcg = inject(TcgPlayerService);
  private tcgmatch = inject(TcgmatchService);

  loading = signal(false);
  price = signal<TcgPlayerPrice | null>(null);
  tcgmatchLoading = signal(false);
  tcgmatchPrice = signal<TcgmatchPrice | null>(null);
  private retried = false;
  private tcgmatchRetried = false;

  get tcgSearchUrl(): string {
    return `https://www.tcgplayer.com/search/riftbound-league-of-legends-trading-card-game/product?q=${encodeURIComponent(this.cardName)}&view=grid`;
  }

  get tcgmatchSearchUrl(): string {
    return `https://tcgmatch.cl/cartas/busqueda/q=${encodeURIComponent(this.cardName)}`;
  }

  get cardmarketSearchUrl(): string {
    return `https://www.cardmarket.com/es/Riftbound/Products/Search?searchString=${encodeURIComponent(this.cardName)}`;
  }

  ngOnChanges(changes: SimpleChanges): void {
    if ((changes['cardName'] || changes['compact'] || changes['showExternalMarkets'] || changes['showMarketPrice']) && this.cardName) {
      if (!this.showMarketPrice) {
        this.loading.set(false);
        this.price.set(null);
        this.tcgmatchLoading.set(false);
        this.tcgmatchPrice.set(null);
        return;
      }
      this.retried = false;
      this.fetchPrice();

      if (!this.compact && this.showExternalMarkets) {
        this.tcgmatchRetried = false;
        this.fetchTcgmatch();
      } else {
        this.tcgmatchLoading.set(false);
        this.tcgmatchPrice.set(null);
      }
    }
  }

  formatClp(value: number | null | undefined): string {
    if (value == null || Number.isNaN(value)) {
      return 'N/A';
    }
    return '$' + Math.round(value).toLocaleString('es-CL');
  }

  private fetchPrice(force = false): void {
    this.loading.set(true);
    this.tcg.getPrice(this.cardName, force).subscribe(data => {
      this.price.set(data);
      this.loading.set(false);

      // Reintento breve para evitar N/A por fallos transitorios.
      if (data.market_price == null && !this.retried) {
        this.retried = true;
        setTimeout(() => this.fetchPrice(true), 350);
      }
    });
  }

  private fetchTcgmatch(force = false): void {
    this.tcgmatchLoading.set(true);
    this.tcgmatch.getPrice(this.cardName, force).subscribe(data => {
      this.tcgmatchPrice.set(data);
      this.tcgmatchLoading.set(false);

      if (data.market_price == null && data.low_price == null && !this.tcgmatchRetried) {
        this.tcgmatchRetried = true;
        setTimeout(() => this.fetchTcgmatch(true), 350);
      }
    });
  }
}
