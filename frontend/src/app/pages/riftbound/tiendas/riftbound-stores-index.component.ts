import { Component, OnInit, ChangeDetectionStrategy, ChangeDetectorRef, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundPublicBinderProfile } from '../../../models/riftbound';
import { IconComponent } from '../../../components/icon/icon.component';

@Component({
  selector: 'app-riftbound-stores-index',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, IconComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
  <div class="stores-page">

    <!-- Page Header -->
    <div class="page-header">
      <div class="header-text">
        <h1><app-icon name="store" [size]="22"></app-icon> Tiendas Riftbound</h1>
        <p>Compra y vende cartas de Riftbound con la comunidad.</p>
      </div>
    </div>

    <!-- Filters Bar -->
    <div class="filters-bar">
      <div class="search-wrap">
        <app-icon name="search" [size]="15"></app-icon>
        <input type="text" placeholder="Buscar por usuario o ciudad..."
               [(ngModel)]="search" (keyup.enter)="reload()" class="search-input" />
      </div>
      <select [(ngModel)]="country" (change)="reload()">
        <option value="">Todos los países</option>
        <option value="CL">Chile</option>
        <option value="AR">Argentina</option>
        <option value="PE">Perú</option>
        <option value="MX">México</option>
        <option value="CO">Colombia</option>
        <option value="UY">Uruguay</option>
        <option value="EC">Ecuador</option>
        <option value="BO">Bolivia</option>
        <option value="VE">Venezuela</option>
        <option value="PY">Paraguay</option>
        <option value="ES">España</option>
        <option value="US">USA</option>
        <option value="OT">Otro</option>
      </select>
      <select [(ngModel)]="ordering" (change)="reload()">
        <option value="-last_active">Más activas</option>
        <option value="-selling_count">Más cartas en venta</option>
        <option value="user__username">Nombre A-Z</option>
      </select>
    </div>

    @if (loading()) {
      <div class="loading-state">
        <app-icon name="refresh-cw" [size]="18"></app-icon>
        <span>Cargando tiendas...</span>
      </div>
    }

    @if (!loading() && stores().length === 0) {
      <div class="empty-state">
        <app-icon name="store" [size]="32"></app-icon>
        <p>No hay tiendas que coincidan.<br /><strong>¡Sé el primero!</strong> Activa tu tienda en la pestaña Mercado de tu carpeta Riftbound.</p>
      </div>
    }

    <!-- Bento Grid -->
    <div class="stores-grid">
      @for (s of stores(); track s.share_token) {
        <a class="store-card" [routerLink]="['/riftbound/tienda', s.store_slug || s.share_token]">
          <div class="store-card-header">
            <div class="store-avatar">
              @if (s.binder_avatar_url || s.user_avatar_url) {
                <img [src]="s.binder_avatar_url || s.user_avatar_url" [alt]="s.display_name || s.username" />
              } @else {
                <div class="avatar-placeholder">
                  <app-icon name="store" [size]="20"></app-icon>
                </div>
              }
              <div class="online-dot"></div>
            </div>
            <div class="store-identity">
              <h3>{{ s.display_name || s.username }}</h3>
              <span class="handle">&#64;{{ s.username }}</span>
            </div>
            <div class="external-link-btn" title="Ver tienda">
              <app-icon name="external-link" [size]="14"></app-icon>
            </div>
          </div>

          @if (s.city || s.country) {
            <div class="store-location">
              <app-icon name="map-pin" [size]="12"></app-icon>
              <span>{{ s.city }}{{ s.city && s.country ? ', ' : '' }}{{ s.country }}</span>
            </div>
          }

          @if (s.bio) {
            <p class="store-bio">{{ s.bio }}</p>
          }

          <div class="store-badges">
            <span class="badge badge-cards">
              <app-icon name="layers" [size]="11"></app-icon>
              {{ s.selling_count || 0 }} en venta
            </span>
            @if (s.accepts_trades) {
              <span class="badge badge-trades">
                <app-icon name="refresh-cw" [size]="11"></app-icon>
                Cambios
              </span>
            }
            @if (s.whatsapp) {
              <span class="badge badge-wa">
                <app-icon name="message-circle" [size]="11"></app-icon>
                WhatsApp
              </span>
            }
          </div>
        </a>
      }
    </div>

    @if (totalPages() > 1) {
      <div class="pagination">
        <button class="btn btn-sm" (click)="prev()" [disabled]="page() === 1">
          <app-icon name="chevron-left" [size]="15"></app-icon> Anterior
        </button>
        <span>{{ page() }} / {{ totalPages() }}</span>
        <button class="btn btn-sm" (click)="next()" [disabled]="page() >= totalPages()">
          Siguiente <app-icon name="chevron-right" [size]="15"></app-icon>
        </button>
      </div>
    }

  </div>
  `,
  styles: [`
    .stores-page {
      max-width: 1400px;
      margin: 0 auto;
      padding: 1.25rem 1.5rem;
    }

    .page-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.5rem;

      .header-text {
        h1 {
          margin: 0;
          font-size: 1.4rem;
          font-weight: 700;
          color: #ffffff;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          letter-spacing: -0.02em;

          app-icon { color: var(--ui-accent, #06b6d4); }
        }
        p {
          margin: 0.2rem 0 0;
          color: var(--ui-text-muted);
          font-size: 0.85rem;
        }
      }
    }

    .filters-bar {
      display: flex;
      gap: 0.6rem;
      flex-wrap: wrap;
      margin-bottom: 1.25rem;

      .search-wrap {
        flex: 1 1 220px;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0 0.75rem;
        background: var(--ui-surface);
        border: 1px solid var(--ui-border);
        border-radius: 8px;
        transition: border-color 0.15s ease;

        &:focus-within {
          border-color: var(--ui-accent, #06b6d4);
        }

        app-icon { color: var(--ui-text-muted); flex-shrink: 0; }

        .search-input {
          flex: 1;
          border: none;
          background: transparent;
          color: #ffffff;
          font-size: 0.875rem;
          padding: 0.6rem 0;
          outline: none;

          &::placeholder { color: var(--ui-text-muted); }
        }
      }

      select {
        padding: 0.55rem 0.75rem;
        border-radius: 8px;
        border: 1px solid var(--ui-border);
        background: var(--ui-surface);
        color: var(--ui-text-muted);
        font-size: 0.85rem;
        cursor: pointer;
        outline: none;
        transition: border-color 0.15s ease;

        &:focus { border-color: var(--ui-accent, #06b6d4); }
        option { background: #18181b; }
      }
    }

    .loading-state {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      padding: 3rem 1rem;
      color: var(--ui-text-muted);
      font-size: 0.9rem;
    }

    .empty-state {
      text-align: center;
      padding: 3.5rem 1rem;
      color: var(--ui-text-muted);

      app-icon {
        color: rgba(255, 255, 255, 0.1);
        display: block;
        margin: 0 auto 1rem;
      }

      p {
        font-size: 0.9rem;
        line-height: 1.6;
        max-width: 380px;
        margin: 0 auto;

        strong { color: var(--ui-accent, #06b6d4); }
      }
    }

    .stores-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
      gap: 1rem;
    }

    .store-card {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      background: var(--ui-surface);
      border: 1px solid var(--ui-border);
      border-radius: 14px;
      padding: 1rem 1.1rem;
      text-decoration: none;
      color: inherit;
      transition: border-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
      cursor: pointer;

      &:hover {
        border-color: var(--ui-accent, #06b6d4);
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);

        .external-link-btn { opacity: 1; }
      }

      .store-card-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;

        .store-avatar {
          position: relative;
          width: 46px;
          height: 46px;
          flex-shrink: 0;

          img {
            width: 100%;
            height: 100%;
            border-radius: 10px;
            object-fit: cover;
            border: 2px solid var(--ui-accent, #06b6d4);
          }

          .avatar-placeholder {
            width: 100%;
            height: 100%;
            border-radius: 10px;
            background: rgba(39, 39, 42, 0.7);
            border: 1px solid var(--ui-border);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--ui-text-muted);
          }

          .online-dot {
            position: absolute;
            bottom: -2px;
            right: -2px;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #10b981;
            border: 2px solid #09090b;
          }
        }

        .store-identity {
          flex: 1;
          min-width: 0;

          h3 {
            margin: 0;
            font-size: 0.95rem;
            font-weight: 700;
            color: #ffffff;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }

          .handle {
            display: block;
            font-size: 0.75rem;
            color: var(--ui-text-muted);
            margin-top: 1px;
          }
        }

        .external-link-btn {
          flex-shrink: 0;
          width: 28px;
          height: 28px;
          border-radius: 7px;
          background: rgba(255, 255, 255, 0.05);
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--ui-text-muted);
          opacity: 0;
          transition: opacity 0.15s ease, color 0.15s ease;

          &:hover { color: var(--ui-accent, #06b6d4); }
        }
      }

      .store-location {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.78rem;
        color: var(--ui-text-muted);

        app-icon { flex-shrink: 0; }
      }

      .store-bio {
        margin: 0;
        font-size: 0.78rem;
        color: var(--ui-text-muted);
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }

      .store-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
        margin-top: auto;

        .badge {
          display: inline-flex;
          align-items: center;
          gap: 0.3rem;
          font-size: 0.7rem;
          font-weight: 600;
          padding: 0.2rem 0.55rem;
          border-radius: 999px;
          border: 1px solid transparent;

          &.badge-cards {
            background: rgba(6, 182, 212, 0.12);
            border-color: rgba(6, 182, 212, 0.3);
            color: var(--ui-accent, #06b6d4);
          }

          &.badge-trades {
            background: rgba(16, 185, 129, 0.1);
            border-color: rgba(16, 185, 129, 0.3);
            color: #10b981;
          }

          &.badge-wa {
            background: rgba(34, 197, 94, 0.1);
            border-color: rgba(34, 197, 94, 0.3);
            color: #22c55e;
          }
        }
      }
    }

    .pagination {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 1rem;
      padding: 1.5rem 0;
      color: var(--ui-text-muted);
      font-size: 0.85rem;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.45rem 0.85rem;
      border: 1px solid var(--ui-border);
      background: var(--ui-surface);
      color: var(--ui-text-muted);
      border-radius: 8px;
      font-size: 0.82rem;
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover:not(:disabled) {
        border-color: var(--ui-accent, #06b6d4);
        color: var(--ui-accent, #06b6d4);
      }

      &:disabled {
        opacity: 0.35;
        cursor: default;
      }
    }
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
