import { Component, OnInit, ChangeDetectionStrategy, ChangeDetectorRef, inject, signal } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { RiftboundService } from '../../../services/riftbound.service';
import { AuthService } from '../../../services/auth.service';
import {
  RiftboundCollectionEntry, RiftboundCardLite, RiftboundPublicBinderProfile,
} from '../../../models/riftbound';

@Component({
  selector: 'app-riftbound-tienda',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, DecimalPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
  <div class="tienda-container">
    @if (loading() && !store()) { <div class="loading">Cargando tienda...</div> }
    @if (errorMsg()) {
      <div class="error-state">
        <h2>Tienda no encontrada</h2>
        <p>{{ errorMsg() }}</p>
        <a routerLink="/riftbound/tiendas" class="btn btn-primary">← Ver todas las tiendas</a>
      </div>
    }

    @if (store(); as s) {
      <div class="store-header">
        @if (s.binder_avatar_url || s.user_avatar_url) {
          <img class="store-avatar" [src]="s.binder_avatar_url || s.user_avatar_url" alt="avatar" />
        } @else {
          <div class="store-avatar-placeholder">🏪</div>
        }
        <div class="store-info">
          <h1>{{ s.display_name || s.username }}</h1>
          <p class="store-meta">
            @if (s.city) { <span>📍 {{ s.city }}</span> }
            <span>🌎 {{ s.country }}</span>
            <span>📦 {{ s.selling_count || 0 }} cartas en venta</span>
          </p>
          @if (s.bio) { <p class="store-bio">{{ s.bio }}</p> }
          <div class="contact-row">
            @if (s.whatsapp) { <a class="contact-chip wa" [href]="'https://wa.me/' + cleanWa(s.whatsapp)" target="_blank">📱 WhatsApp</a> }
            @if (s.instagram) { <a class="contact-chip ig" [href]="'https://instagram.com/' + cleanHandle(s.instagram)" target="_blank">📷 Instagram</a> }
            @if (s.discord) { <span class="contact-chip dc">💬 {{ s.discord }}</span> }
            @if (s.email_public) { <a class="contact-chip em" [href]="'mailto:' + s.email_public">✉️ Email</a> }
            @if (s.accepts_trades) { <span class="contact-chip tr">🔄 Acepta cambios</span> }
          </div>
          @if (s.payment_methods) { <p class="store-line"><strong>💳 Pago:</strong> {{ s.payment_methods }}</p> }
          @if (s.shipping_info) { <p class="store-line"><strong>🚚 Envío:</strong> {{ s.shipping_info }}</p> }
        </div>
      </div>

      <div class="filter-row">
        <input type="text" placeholder="Buscar..." [(ngModel)]="search" (keyup.enter)="reload()" />
        <select [(ngModel)]="ftype" (change)="reload()">
          <option value="">Todos los tipos</option>
          <option value="unit">Unit</option><option value="spell">Spell</option>
          <option value="champion">Champion</option><option value="legend">Legend</option>
          <option value="gear">Gear</option><option value="battlefield">Battlefield</option>
          <option value="rune">Rune</option>
        </select>
        <select [(ngModel)]="fcondition" (change)="reload()">
          <option value="">Toda condición</option>
          <option value="NM">NM</option><option value="LP">LP</option>
          <option value="MP">MP</option><option value="HP">HP</option><option value="DMG">DMG</option>
        </select>
        <select [(ngModel)]="ffoil" (change)="reload()">
          <option value="">Foil/Normal</option>
          <option value="1">Solo foil</option>
          <option value="0">Solo normal</option>
        </select>
        <input type="number" placeholder="Precio mín." [(ngModel)]="priceMin" (change)="reload()" min="0" />
        <input type="number" placeholder="Precio máx." [(ngModel)]="priceMax" (change)="reload()" min="0" />
        <select [(ngModel)]="ordering" (change)="reload()">
          <option value="-id">Más recientes</option>
          <option value="price">Precio ↑</option>
          <option value="-price">Precio ↓</option>
          <option value="card__name">Nombre A-Z</option>
        </select>
      </div>

      <p class="results-count">{{ count() }} cartas</p>

      <div class="cards-grid">
        @for (e of entries(); track e.id) {
          <div class="store-card">
            <div class="card-image" (click)="preview.set(e.card_data)">
              @if (e.card_data?.image) {
                <img [src]="e.card_data.image" [alt]="e.card_data.name" loading="lazy" />
              } @else { <div class="img-fallback">{{ e.card_data?.card_number }}</div> }
              @if (e.is_foil) { <div class="foil-badge">✨ FOIL</div> }
            </div>
            <div class="card-body">
              <h4>{{ e.card_data?.name }}</h4>
              <span class="card-meta">{{ e.card_data?.card_number }} · {{ e.condition }} · {{ e.language }}</span>
              <div class="price-row">
                <span class="price">{{ e.price != null ? ('$' + (e.price | number)) : 'Consultar' }}</span>
                <span class="qty">x{{ e.selling_quantity }}</span>
              </div>
            </div>
          </div>
        }
      </div>

      @if (totalPages() > 1) {
        <div class="pagination">
          <button class="btn btn-sm" (click)="prev()" [disabled]="page() === 1">← Anterior</button>
          <span>{{ page() }} / {{ totalPages() }}</span>
          <button class="btn btn-sm" (click)="next()" [disabled]="page() >= totalPages()">Siguiente →</button>
        </div>
      }
    }

    @if (preview(); as pc) {
      <div class="modal-overlay" (click)="preview.set(null)">
        <div class="modal" (click)="$event.stopPropagation()">
          <button class="close-btn" (click)="preview.set(null)">✕</button>
          @if (pc.image) { <img [src]="pc.image" [alt]="pc.name" class="detail-image" /> }
          <div class="detail-info">
            <h2>{{ pc.name }}</h2>
            <p class="card-meta">{{ pc.card_number }}</p>
            @if (pc.description) { <p>{{ pc.description }}</p> }
          </div>
        </div>
      </div>
    }
  </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; background: #0f0f23; color: #c8c8da; }
    .tienda-container { max-width: 1400px; margin: 0 auto; padding: 1.5rem; }
    .loading { padding: 2rem; text-align: center; color: #9ba3b4; }
    .error-state { padding: 3rem 1rem; text-align: center; }
    .error-state h2 { color: #e94560; }

    .store-header {
      display: flex; align-items: flex-start; gap: 1.2rem;
      padding: 1.5rem; margin-bottom: 1.5rem;
      background: linear-gradient(135deg, #16213e, #1a1a2e);
      border: 1px solid #2a3a4a; border-radius: 12px;
    }
    .store-avatar, .store-avatar-placeholder {
      width: 96px; height: 96px; border-radius: 14px;
      border: 2px solid #e94560; flex-shrink: 0;
    }
    .store-avatar { object-fit: cover; }
    .store-avatar-placeholder {
      background: #0f0f23; display: flex; align-items: center; justify-content: center; font-size: 2.6rem;
    }
    .store-info h1 { margin: 0; color: #fff;
      background: linear-gradient(90deg, #e94560, #fff); -webkit-background-clip: text;
      -webkit-text-fill-color: transparent; background-clip: text; }
    .store-meta { display: flex; gap: 1rem; flex-wrap: wrap; color: #9ba3b4; font-size: .9rem; margin: .35rem 0; }
    .store-bio { color: #c8c8da; margin: .35rem 0 .6rem; }
    .store-line { color: #9ba3b4; font-size: .85rem; margin: .2rem 0; }
    .store-line strong { color: #c8c8da; }
    .contact-row { display: flex; gap: .4rem; flex-wrap: wrap; margin: .5rem 0; }
    .contact-chip {
      padding: .35rem .7rem; border-radius: 6px; font-size: .82rem;
      background: #0f0f23; color: #c8c8da; border: 1px solid #2a3a4a;
      text-decoration: none;
    }
    .contact-chip.wa { color: #25d366; border-color: #25d366; }
    .contact-chip.ig { color: #e1306c; border-color: #e1306c; }
    .contact-chip.em { color: #4fc3f7; border-color: #4fc3f7; }
    .contact-chip.tr { color: #c89b3c; border-color: #c89b3c; }
    .contact-chip:hover { background: #16213e; }

    .filter-row { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 1rem; }
    .filter-row input, .filter-row select {
      padding: .5rem .7rem; background: #0f0f23; color: #c8c8da;
      border: 1px solid #2a3a4a; border-radius: 6px;
    }
    .filter-row input:focus, .filter-row select:focus { outline: none; border-color: #e94560; }

    .results-count { color: #9ba3b4; font-size: .9rem; margin-bottom: 1rem; }

    .cards-grid {
      display: grid; gap: 1rem;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    }
    .store-card { background: #16213e; border: 1px solid #2a3a4a; border-radius: 10px; overflow: hidden; }
    .card-image { position: relative; aspect-ratio: 5/7; background: #0f0f23; cursor: pointer; overflow: hidden; }
    .card-image img { width: 100%; height: 100%; object-fit: cover; transition: transform .2s; }
    .card-image:hover img { transform: scale(1.04); }
    .img-fallback {
      width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
      color: #6b7280; font-weight: 700;
    }
    .foil-badge {
      position: absolute; bottom: 8px; left: 8px;
      background: linear-gradient(135deg, #4fc3f7, #e94560);
      color: #fff; padding: .2rem .5rem; border-radius: 4px;
      font-size: .7rem; font-weight: 700;
    }
    .card-body { padding: .65rem .75rem .8rem; }
    .card-body h4 {
      margin: 0 0 .25rem; font-size: .95rem; color: #fff;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .card-meta { color: #9ba3b4; font-size: .78rem; }
    .price-row { display: flex; justify-content: space-between; align-items: center; margin-top: .5rem; }
    .price { color: #e94560; font-weight: 800; font-size: 1.05rem; }
    .qty { color: #4fc3f7; font-size: .85rem; }

    .btn { padding: .4rem .8rem; border: 1px solid #2a3a4a; background: transparent; color: #c8c8da;
      border-radius: 6px; cursor: pointer; font-weight: 600; text-decoration: none; display: inline-block; }
    .btn:hover:not(:disabled) { background: #1e2d3d; }
    .btn:disabled { opacity: .5; cursor: not-allowed; }
    .btn-sm { padding: .35rem .65rem; font-size: .85rem; }
    .btn-primary { background: #e94560; border-color: #e94560; color: #fff; }
    .pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 1.5rem; color: #9ba3b4; }

    .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.85);
      display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem; }
    .modal { background: #16213e; border: 1px solid #2a3a4a; border-radius: 14px;
      max-width: 720px; width: 100%; max-height: 90vh; overflow-y: auto;
      display: grid; grid-template-columns: 1fr 1.2fr; position: relative; }
    @media (max-width: 640px) { .modal { grid-template-columns: 1fr; } }
    .detail-image { width: 100%; height: auto; border-radius: 14px 0 0 14px; }
    .detail-info { padding: 1.4rem; color: #c8c8da; }
    .detail-info h2 { margin: 0 0 .5rem; color: #fff; }
    .close-btn { position: absolute; top: .5rem; right: .5rem;
      background: rgba(15,15,35,.85); border: 1px solid #2a3a4a; color: #fff;
      width: 32px; height: 32px; border-radius: 50%; cursor: pointer; z-index: 2; }
    .close-btn:hover { background: #e94560; border-color: #e94560; }
  `],
})
export class RiftboundTiendaComponent implements OnInit {
  private readonly rb = inject(RiftboundService);
  readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly cdr = inject(ChangeDetectorRef);

  token = '';
  loading = signal(false);
  errorMsg = signal<string | null>(null);
  store = signal<RiftboundPublicBinderProfile | null>(null);
  entries = signal<RiftboundCollectionEntry[]>([]);
  count = signal(0);
  page = signal(1);
  preview = signal<RiftboundCardLite | null>(null);

  search = '';
  ftype = '';
  fcondition = '';
  ffoil: '' | '0' | '1' = '';
  priceMin: number | null = null;
  priceMax: number | null = null;
  ordering = '-id';

  totalPages() { return Math.max(1, Math.ceil(this.count() / 20)); }

  ngOnInit() {
    this.token = this.route.snapshot.paramMap.get('token') || '';
    this.reload();
  }

  reload() {
    this.loading.set(true);
    this.errorMsg.set(null);
    this.rb.getPublicStore(this.token, {
      search: this.search || undefined,
      type: this.ftype || undefined,
      condition: this.fcondition || undefined,
      foil: this.ffoil || undefined,
      price_min: this.priceMin ?? undefined,
      price_max: this.priceMax ?? undefined,
      ordering: this.ordering,
      page: this.page(),
    }).subscribe({
      next: res => {
        this.entries.set(res.results);
        this.count.set(res.count);
        this.store.set(res.store);
        this.loading.set(false);
        this.cdr.markForCheck();
      },
      error: err => {
        this.loading.set(false);
        this.errorMsg.set(err?.error?.detail || 'No se pudo cargar la tienda.');
        this.cdr.markForCheck();
      },
    });
  }

  prev() { if (this.page() > 1) { this.page.update(p => p - 1); this.reload(); } }
  next() { if (this.page() < this.totalPages()) { this.page.update(p => p + 1); this.reload(); } }

  cleanWa(v: string): string { return v.replace(/[^0-9]/g, ''); }
  cleanHandle(v: string): string { return v.replace(/^@/, '').trim(); }
}
