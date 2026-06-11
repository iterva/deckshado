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
    :host { display: block; min-height: 100vh; background: #0f0f23; color: #c8c8da; }
    .stores-container { max-width: 1300px; margin: 0 auto; padding: 1.5rem; }
    @media (max-width: 600px) { .stores-container { padding: 1rem 0.65rem 2rem; } }
    .hero { text-align: center; margin-bottom: 2rem; padding: 1.5rem 1rem;
      background: linear-gradient(135deg, #16213e, #1a1a2e);
      border: 1px solid #2a3a4a; border-radius: 12px; }
    .hero h1 { margin: 0; font-size: 2rem;
      background: linear-gradient(90deg, #e94560, #4fc3f7); -webkit-background-clip: text;
      -webkit-text-fill-color: transparent; background-clip: text; }
    .hero p { color: #9ba3b4; margin: .5rem 0 0; }

    .filter-row { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 1rem; align-items: center; }
    .filter-row input, .filter-row select {
      padding: .5rem .7rem; background: #0f0f23; color: #c8c8da;
      border: 1px solid #2a3a4a; border-radius: 6px;
    }
    .filter-row input { flex: 1; min-width: 200px; }
    .filter-row input:focus, .filter-row select:focus { outline: none; border-color: #e94560; }

    .results-count { color: #9ba3b4; font-size: .9rem; margin-bottom: 1rem; }
    .loading { padding: 2rem; text-align: center; color: #9ba3b4; }
    .empty-state { padding: 3rem 1rem; text-align: center; color: #9ba3b4;
      background: #16213e; border: 1px dashed #2a3a4a; border-radius: 12px; }

    .stores-grid {
      display: grid; gap: 1rem;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    }
    .store-card {
      display: flex; gap: 1rem; padding: 1rem;
      background: #16213e; border: 1px solid #2a3a4a; border-radius: 10px;
      text-decoration: none; color: inherit; transition: all .15s;
    }
    .store-card:hover { border-color: #e94560; transform: translateY(-2px); }
    .avatar {
      width: 64px; height: 64px; border-radius: 10px; flex-shrink: 0;
      border: 2px solid #e94560; object-fit: cover;
    }
    .avatar.placeholder {
      background: #0f0f23; display: flex; align-items: center; justify-content: center; font-size: 1.8rem;
    }
    .info { flex: 1; min-width: 0; }
    .info h3 { margin: 0; color: #fff; font-size: 1rem;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .meta { display: flex; gap: .6rem; flex-wrap: wrap; color: #9ba3b4; font-size: .82rem; margin: .25rem 0; }
    .count { color: #4fc3f7; font-size: .9rem; margin: .25rem 0; font-weight: 600; }
    .trade-badge { display: inline-block; background: #c89b3c30; color: #c89b3c;
      border: 1px solid #c89b3c; padding: .15rem .45rem; border-radius: 4px; font-size: .72rem; }

    .btn { padding: .4rem .8rem; border: 1px solid #2a3a4a; background: transparent; color: #c8c8da;
      border-radius: 6px; cursor: pointer; font-weight: 600; }
    .btn:hover:not(:disabled) { background: #1e2d3d; }
    .btn:disabled { opacity: .5; cursor: not-allowed; }
    .btn-sm { padding: .35rem .65rem; font-size: .85rem; }
    .btn-primary { background: #e94560; border-color: #e94560; color: #fff; }
    .pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 1.5rem; color: #9ba3b4; }
  `],
})
export class RiftboundStoresIndexComponent implements OnInit {
  private readonly rb = inject(RiftboundService);
  private readonly cdr = inject(ChangeDetectorRef);

  loading = signal(false);
  stores = signal<RiftboundPublicBinderProfile[]>([]);
  count = signal(0);
  page = signal(1);

  search = '';
  country = '';
  ordering = '-last_active';

  totalPages() { return Math.max(1, Math.ceil(this.count() / 20)); }

  ngOnInit() { this.reload(); }

  reload() {
    this.loading.set(true);
    this.rb.listStores({
      search: this.search || undefined,
      country: this.country || undefined,
      ordering: this.ordering,
      page: this.page(),
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
