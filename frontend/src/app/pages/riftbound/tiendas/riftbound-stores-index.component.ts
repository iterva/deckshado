import { Component, OnInit, ChangeDetectionStrategy, ChangeDetectorRef, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundPublicBinderProfile } from '../../../models/riftbound';

@Component({
  selector: 'app-riftbound-stores-index',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
  <div class="stores-container">
    <header class="hero">
      <h1>🏪 Tiendas Riftbound</h1>
      <p>Compra y vende cartas con la comunidad.</p>
    </header>

    <div class="filter-row">
      <input type="text" placeholder="Buscar usuario, nombre o ciudad..."
             [(ngModel)]="search" (keyup.enter)="reload()" />
      <select [(ngModel)]="country" (change)="reload()">
        <option value="">Todos los países</option>
        <option value="CL">Chile</option><option value="AR">Argentina</option>
        <option value="PE">Perú</option><option value="MX">México</option>
        <option value="CO">Colombia</option><option value="UY">Uruguay</option>
        <option value="EC">Ecuador</option><option value="BO">Bolivia</option>
        <option value="VE">Venezuela</option><option value="PY">Paraguay</option>
        <option value="ES">España</option><option value="US">USA</option>
        <option value="OT">Otro</option>
      </select>
      <select [(ngModel)]="ordering" (change)="reload()">
        <option value="-last_active">Más recientes</option>
        <option value="-selling_count">Más cartas</option>
        <option value="user__username">Nombre A-Z</option>
      </select>
      <button class="btn btn-primary btn-sm" (click)="reload()">Buscar</button>
    </div>

    <p class="results-count">{{ count() }} tiendas</p>

    @if (loading()) { <div class="loading">Cargando...</div> }
    @if (!loading() && stores().length === 0) {
      <div class="empty-state">
        <p>No se encontraron tiendas. ¡Sé el primero! Ve a tu Carpeta → Mercado y activa "Tienda pública".</p>
      </div>
    }

    <div class="stores-grid">
      @for (s of stores(); track s.share_token) {
        <a class="store-card" [routerLink]="['/riftbound/tienda', s.store_slug || s.share_token]">
          @if (s.binder_avatar_url || s.user_avatar_url) {
            <img class="avatar" [src]="s.binder_avatar_url || s.user_avatar_url" [alt]="s.display_name || s.username" />
          } @else {
            <div class="avatar placeholder">🏪</div>
          }
          <div class="info">
            <h3>{{ s.display_name || s.username }}</h3>
            <p class="meta">
              @if (s.city) { <span>📍 {{ s.city }}</span> }
              <span>🌎 {{ s.country }}</span>
            </p>
            <p class="count">📦 {{ s.selling_count || 0 }} cartas en venta</p>
            @if (s.accepts_trades) { <span class="trade-badge">🔄 Acepta cambios</span> }
          </div>
        </a>
      }
    </div>

    @if (totalPages() > 1) {
      <div class="pagination">
        <button class="btn btn-sm" (click)="prev()" [disabled]="page() === 1">← Anterior</button>
        <span>{{ page() }} / {{ totalPages() }}</span>
        <button class="btn btn-sm" (click)="next()" [disabled]="page() >= totalPages()">Siguiente →</button>
      </div>
    }
  </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; background: var(--ui-bg); color: var(--ui-text-muted); }
    .stores-container { max-width: 1300px; margin: 0 auto; padding: 1.5rem; }
    @media (max-width: 600px) { .stores-container { padding: 1rem 0.65rem 2rem; } }
    .hero { text-align: center; margin-bottom: 2rem; padding: 1.5rem 1rem;
      background: color-mix(in srgb, var(--ui-surface) 94%, #ffffff 6%);
      border: 1px solid var(--ui-border); border-radius: 12px; }
    .hero h1 { margin: 0; font-size: 2rem;
      color: var(--ui-text); display: inline-block; }
    .hero p { color: var(--ui-text-muted); margin: .5rem 0 0; }

    .filter-row { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 1rem; align-items: center; }
    .filter-row input, .filter-row select {
      padding: .5rem .7rem; background: var(--ui-surface); color: var(--ui-text);
      border: 1px solid var(--ui-border); border-radius: 6px;
    }
    .filter-row input { flex: 1; min-width: 200px; }
    .filter-row input:focus, .filter-row select:focus { outline: none; border-color: var(--ui-accent); }

    .results-count { color: var(--ui-text-muted); font-size: .9rem; margin-bottom: 1rem; }
    .loading { padding: 2rem; text-align: center; color: var(--ui-text-muted); }
    .empty-state { padding: 3rem 1rem; text-align: center; color: var(--ui-text-muted);
      background: color-mix(in srgb, var(--ui-surface) 94%, #ffffff 6%); border: 1px dashed var(--ui-border); border-radius: 12px; }

    .stores-grid {
      display: grid; gap: 1rem;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    }
    .store-card {
      display: flex; gap: 1rem; padding: 1rem;
      background: color-mix(in srgb, var(--ui-surface) 94%, #ffffff 6%); border: 1px solid var(--ui-border); border-radius: 10px;
      text-decoration: none; color: inherit; transition: all .15s;
    }
    .store-card:hover { border-color: var(--ui-accent); transform: translateY(-2px); }
    .avatar {
      width: 64px; height: 64px; border-radius: 10px; flex-shrink: 0;
      border: 2px solid var(--ui-accent); object-fit: cover;
    }
    .avatar.placeholder {
      background: var(--ui-bg-soft); display: flex; align-items: center; justify-content: center; font-size: 1.8rem;
    }
    .info { flex: 1; min-width: 0; }
    .info h3 { margin: 0; color: var(--ui-text); font-size: 1rem;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .meta { display: flex; gap: .6rem; flex-wrap: wrap; color: var(--ui-text-muted); font-size: .82rem; margin: .25rem 0; }
    .count { color: var(--ui-accent); font-size: .9rem; margin: .25rem 0; font-weight: 600; }
    .trade-badge { display: inline-block; background: color-mix(in srgb, var(--ui-accent) 18%, transparent); color: var(--ui-accent);
      border: 1px solid var(--ui-accent); padding: .15rem .45rem; border-radius: 4px; font-size: .72rem; }

    .btn { padding: .4rem .8rem; border: 1px solid var(--ui-border); background: transparent; color: var(--ui-text);
      border-radius: 6px; cursor: pointer; font-weight: 600; }
    .btn:hover:not(:disabled) { background: color-mix(in srgb, var(--ui-surface-elevated) 92%, #ffffff 8%); }
    .btn:disabled { opacity: .5; cursor: not-allowed; }
    .btn-sm { padding: .35rem .65rem; font-size: .85rem; }
    .btn-primary { background: var(--ui-accent); border-color: var(--ui-accent); color: #fff; }
    .pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 1.5rem; color: var(--ui-text-muted); }
  `],
})
export class RiftboundStoresIndexComponent implements OnInit {
  private readonly rb = inject(RiftboundService);
  private readonly cdr = inject(ChangeDetectorRef);
  readonly pageSize = 20;

  loading = signal(false);
  stores = signal<RiftboundPublicBinderProfile[]>([]);
  count = signal(0);
  page = signal(1);

  search = '';
  country = '';
  ordering = '-last_active';

  totalPages() { return Math.max(1, Math.ceil(this.count() / this.pageSize)); }

  ngOnInit() { this.reload(); }

  reload() {
    this.loading.set(true);
    this.rb.listStores({
      search: this.search || undefined,
      country: this.country || undefined,
      ordering: this.ordering,
      page: this.page(),
      page_size: this.pageSize,
    }).subscribe({
      next: res => {
        this.stores.set(res.results);
        this.count.set(res.count);
        this.loading.set(false);
        this.cdr.markForCheck();
      },
      error: () => { this.loading.set(false); this.cdr.markForCheck(); },
    });
  }

  prev() { if (this.page() > 1) { this.page.update(p => p - 1); this.reload(); } }
  next() { if (this.page() < this.totalPages()) { this.page.update(p => p + 1); this.reload(); } }
}
