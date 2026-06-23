import { Component, Input, OnChanges, SimpleChanges, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TcgPlayerService, TcgPlayerPrice } from '../../services/tcgplayer.service';
import { TcgmatchService, TcgmatchPrice } from '../../services/tcgmatch.service';

@Component({
  selector: 'app-tcg-price',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (loading()) {
      <span class="tcg-price loading" [class.compact]="compact">
        <span class="tcg-spinner"></span>
      </span>
    } @else if (price()?.market_price != null) {
      @if (compact) {
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
      } @else {
        <div class="tcg-market-stack">
          <div class="tcg-price detailed">
            <div class="tcg-header">
              <span class="tcg-icon">💲</span>
              <span>TCGPlayer</span>
            </div>
            <div class="tcg-rows">
              <div class="tcg-row">
                <span>Precio de mercado</span>
                <strong>\${{ price()!.market_price!.toFixed(2) }}</strong>
              </div>
              @if (price()!.low_price != null) {
                <div class="tcg-row">
                  <span>Low</span>
                  <span>\${{ price()!.low_price!.toFixed(2) }}</span>
                </div>
              }
              @if (price()!.mid_price != null) {
                <div class="tcg-row">
                  <span>Mid</span>
                  <span>\${{ price()!.mid_price!.toFixed(2) }}</span>
                </div>
              }
            </div>
            @if (showLink) {
              <a class="tcg-btn"
                 [href]="price()!.product_url || tcgSearchUrl"
                 target="_blank" rel="noopener noreferrer">
                Ir a TCGPlayer
              </a>
            }
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
              @if (showLink) {
                <a class="tcg-btn"
                   [href]="tcgmatchPrice()?.product_url || tcgmatchSearchUrl"
                   target="_blank" rel="noopener noreferrer">
                  Ir a TCGMatch
                </a>
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
              @if (showLink) {
                <a class="tcg-btn"
                   [href]="cardmarketSearchUrl"
                   target="_blank" rel="noopener noreferrer">
                  Buscar en Cardmarket
                </a>
              }
            </div>
          }
        </div>
      }
    } @else if (!hideIfEmpty) {
      @if (compact) {
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
      } @else {
        <div class="tcg-market-stack">
          <div class="tcg-price detailed">
            <div class="tcg-header">
              <span class="tcg-icon">💲</span>
              <span>TCGPlayer</span>
            </div>
            <div class="tcg-rows">
              <div class="tcg-row">
                <span>Precio de mercado</span>
                <strong class="tcg-na">N/A</strong>
              </div>
            </div>
            @if (showLink) {
              <a class="tcg-btn"
                 [href]="tcgSearchUrl"
                 target="_blank" rel="noopener noreferrer">
                Ir a TCGPlayer
              </a>
            }
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
              @if (showLink) {
                <a class="tcg-btn"
                   [href]="tcgmatchPrice()?.product_url || tcgmatchSearchUrl"
                   target="_blank" rel="noopener noreferrer">
                  Ir a TCGMatch
                </a>
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
              @if (showLink) {
                <a class="tcg-btn"
                   [href]="cardmarketSearchUrl"
                   target="_blank" rel="noopener noreferrer">
                  Buscar en Cardmarket
                </a>
              }
            </div>
          }
        </div>
      }
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

    .tcg-price.detailed {
      display: flex; flex-direction: column; gap: 6px;
      background: #1a1a2e; border: 1px solid #2a2a4e;
      border-radius: 8px; padding: 8px 12px; min-width: 150px;
    }
    .tcg-market-stack {
      display: flex;
      flex-direction: row;
      flex-wrap: nowrap;
      align-items: stretch;
      gap: 8px;
      width: 100%;
      min-width: 0;
      overflow-x: auto;
      overscroll-behavior-x: contain;
      padding-bottom: 2px;
    }
    .tcg-market-stack .tcg-price.detailed {
      flex: 1 1 0;
      min-width: 190px;
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
      font-size: .75rem;
      color: #fff;
      text-decoration: none;
      background: linear-gradient(135deg, #2d79c7, #1f5d9e);
      border: 1px solid rgba(255, 255, 255, .16);
      border-radius: 6px;
      padding: 3px 8px;
      transition: transform .12s ease, filter .12s ease;
      max-width: 100%;
      white-space: nowrap;
    }
    .tcg-btn:hover { transform: translateY(-1px); filter: brightness(1.05); }
    @media (max-width: 640px) {
      .tcg-market-stack .tcg-price.detailed { min-width: 165px; }
      .tcg-btn { font-size: .72rem; padding: 3px 7px; }
    }
  `],
})
export class TcgPriceComponent implements OnChanges {
  @Input({ required: true }) cardName!: string;
  @Input() compact = true;
  @Input() showLink = true;
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
    if ((changes['cardName'] || changes['compact'] || changes['showExternalMarkets']) && this.cardName) {
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
