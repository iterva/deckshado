import { Component, Input, OnChanges, SimpleChanges, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TcgPlayerService, TcgPlayerPrice } from '../../services/tcgplayer.service';

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
        <a class="tcg-price compact"
           [href]="price()!.product_url || tcgSearchUrl"
           target="_blank" rel="noopener noreferrer"
           [title]="'TCGPlayer: Market $' + price()!.market_price!.toFixed(2)">
          <span class="tcg-icon">💲</span>
          <span class="tcg-amount">\${{ price()!.market_price!.toFixed(2) }}</span>
        </a>
      } @else {
        <div class="tcg-price detailed">
          <div class="tcg-header">
            <span class="tcg-icon">💲</span>
            <span>TCGPlayer</span>
          </div>
          <div class="tcg-rows">
            <div class="tcg-row">
              <span>Market</span>
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
            <a class="tcg-link"
               [href]="price()!.product_url || tcgSearchUrl"
               target="_blank" rel="noopener noreferrer">
              Ver en TCGPlayer →
            </a>
          }
        </div>
      }
    } @else if (!hideIfEmpty) {
      <span class="tcg-price no-price" [class.compact]="compact">
        <span class="tcg-icon">💲</span>
        <span class="tcg-na">N/A</span>
      </span>
    }
  `,
  styles: [`
    :host { display: inline-block; }

    .tcg-price { display: inline-flex; align-items: center; gap: 4px; font-size: .82rem; }
    .tcg-price.loading { color: #888; }
    .tcg-price.no-price { color: #666; }

    .tcg-spinner {
      width: 12px; height: 12px; border: 2px solid #333;
      border-top-color: #1a9c5b; border-radius: 50%;
      animation: tcg-spin .7s linear infinite;
    }
    @keyframes tcg-spin { to { transform: rotate(360deg); } }

    .tcg-price.compact {
      text-decoration: none; color: #1a9c5b; font-weight: 600;
      padding: 2px 6px; border-radius: 4px;
      background: rgba(26, 156, 91, 0.08);
      border: 1px solid rgba(26, 156, 91, 0.2);
      transition: all .15s;
    }
    .tcg-price.compact:hover {
      background: rgba(26, 156, 91, 0.15);
      border-color: rgba(26, 156, 91, 0.4);
    }
    .tcg-icon { font-size: .9rem; }
    .tcg-amount { font-variant-numeric: tabular-nums; }
    .tcg-na { color: #888; font-size: .75rem; }

    .tcg-price.detailed {
      display: flex; flex-direction: column; gap: 6px;
      background: #1a1a2e; border: 1px solid #2a2a4e;
      border-radius: 8px; padding: 8px 12px; min-width: 150px;
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
    }
    .tcg-row strong { color: #1a9c5b; }
    .tcg-link {
      font-size: .75rem; color: #5b9bd5; text-decoration: none; margin-top: 4px;
    }
    .tcg-link:hover { text-decoration: underline; }
  `],
})
export class TcgPriceComponent implements OnChanges {
  @Input({ required: true }) cardName!: string;
  @Input() compact = true;
  @Input() showLink = true;
  @Input() hideIfEmpty = false;

  private tcg = inject(TcgPlayerService);

  loading = signal(false);
  price = signal<TcgPlayerPrice | null>(null);

  get tcgSearchUrl(): string {
    return `https://www.tcgplayer.com/search/riftbound-league-of-legends-trading-card-game/product?q=${encodeURIComponent(this.cardName)}&view=grid`;
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['cardName'] && this.cardName) {
      this.fetchPrice();
    }
  }

  private fetchPrice(): void {
    this.loading.set(true);
    this.tcg.getPrice(this.cardName).subscribe(data => {
      this.price.set(data);
      this.loading.set(false);
    });
  }
}
