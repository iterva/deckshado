import { Component, ChangeDetectionStrategy, OnInit, signal, inject } from '@angular/core';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { CarpetaService } from '../../services/carpeta.service';
import { RiftboundService } from '../../services/riftbound.service';
import { AuthService } from '../../services/auth.service';
import { StoreOrder, StoreOrderStatus } from '../../models';
import { RiftboundStoreOrder, RiftboundStoreOrderStatus } from '../../models/riftbound';

type Game = 'myl' | 'riftbound';
type StatusFilter = '' | 'pending' | 'accepted' | 'cancelled';
type AnyOrder = StoreOrder | RiftboundStoreOrder;

@Component({
  selector: 'app-mis-compras',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mis-compras-page">
      <header class="page-header">
        <h1>📦 {{ storeToken() ? 'Mis pedidos en esta tienda' : 'Mis Pedidos' }}</h1>
        <p class="subtitle">
          @if (storeToken()) {
            Historial de lo que le has comprado a <strong>{{ storeToken() }}</strong>.
          } @else {
            Historial de compras que hiciste en tiendas de otros jugadores.
          }
        </p>
      </header>

      @if (!auth.isAuthenticated()) {
        <div class="empty-state">
          <p>Inicia sesión para ver tus pedidos.</p>
          <a routerLink="/login" class="btn-primary">Iniciar sesión</a>
        </div>
      } @else {
        @if (!storeToken()) {
          <div class="game-tabs" role="tablist">
            <button type="button" class="game-tab" [class.active]="game() === 'myl'" (click)="setGame('myl')">
              Mitos y Leyendas
            </button>
            <button type="button" class="game-tab" [class.active]="game() === 'riftbound'" (click)="setGame('riftbound')">
              Riftbound
            </button>
          </div>
        }

        <div class="status-chips" role="group" aria-label="Filtrar por estado">
          @for (opt of statusOptions; track opt.value) {
            <button type="button" class="status-chip" [class.active]="statusFilter() === opt.value"
                    (click)="setStatusFilter(opt.value)">
              {{ opt.label }}
            </button>
          }
        </div>

        @if (loading()) {
          <p class="hint">Cargando pedidos…</p>
        } @else if (orders().length === 0) {
          <p class="hint">No tienes pedidos {{ statusFilter() ? 'con ese estado' : 'todavía' }}.</p>
        } @else {
          <div class="orders-list">
            @for (order of orders(); track order.id) {
              <div class="order-card">
                <div class="order-head">
                  <div>
                    <span class="order-id">Pedido #{{ order.id }}</span>
                    <span class="order-store">Tienda de {{ order.store_owner }}</span>
                  </div>
                  <span class="status-badge" [class]="order.status">{{ statusLabel(order.status) }}</span>
                </div>
                <ul class="order-items">
                  @for (item of order.items; track item.id) {
                    <li>
                      <span class="item-qty">{{ item.quantity }}x</span>
                      <span class="item-name">{{ item.card_name }}</span>
                      @if (item.line_total !== null) {
                        <span class="item-total">{{ formatMoney(item.line_total) }}</span>
                      }
                    </li>
                  }
                </ul>
                @if (order.status === 'cancelled' && order.seller_note) {
                  <p class="cancel-reason">Motivo de cancelación: {{ order.seller_note }}</p>
                }
                <div class="order-footer">
                  <span class="order-date">{{ formatDate(order.created_at) }}</span>
                  @if (order.total_estimated !== null) {
                    <span class="order-total">Total: {{ formatMoney(order.total_estimated) }}</span>
                  }
                </div>
              </div>
            }
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .mis-compras-page {
      max-width: 900px; margin: 0 auto; padding: 1.5rem 1.25rem 3rem;
    }
    .page-header h1 { margin: 0 0 0.25rem; font-size: 1.5rem; color: var(--ui-text); }
    .subtitle { margin: 0 0 1.25rem; color: var(--ui-text-muted); font-size: 0.9rem; }

    .empty-state {
      display: flex; flex-direction: column; align-items: flex-start; gap: 0.75rem;
      padding: 2rem; border: 1px solid var(--ui-border); border-radius: 12px; background: var(--ui-surface);
    }
    .btn-primary {
      display: inline-block; padding: 0.55rem 1.1rem; border-radius: 8px;
      background: var(--ui-accent); color: #09090b; font-weight: 700; text-decoration: none;
    }

    .game-tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
    .game-tab {
      padding: 0.5rem 1rem; border-radius: 999px; border: 1px solid var(--ui-border);
      background: var(--ui-surface); color: var(--ui-text-secondary); font-weight: 600; cursor: pointer;
      transition: all 0.15s ease;
    }
    .game-tab.active { background: var(--ui-accent-glow); border-color: var(--ui-accent); color: var(--ui-accent); }

    .status-chips { display: flex; gap: 0.4rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
    .status-chip {
      padding: 0.35rem 0.8rem; border-radius: 999px; border: 1px solid var(--ui-border);
      background: transparent; color: var(--ui-text-muted); font-size: 0.8rem; cursor: pointer;
    }
    .status-chip.active { border-color: var(--ui-accent); color: var(--ui-accent); }

    .hint { color: var(--ui-text-muted); padding: 2rem 0; text-align: center; }

    .orders-list { display: flex; flex-direction: column; gap: 0.9rem; }
    .order-card {
      border: 1px solid var(--ui-border); border-radius: 12px; padding: 1rem 1.1rem;
      background: var(--ui-surface);
    }
    .order-head {
      display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem;
      margin-bottom: 0.6rem; padding-bottom: 0.6rem; border-bottom: 1px solid var(--ui-border);
    }
    .order-id { display: block; font-weight: 700; color: var(--ui-text); }
    .order-store { display: block; font-size: 0.8rem; color: var(--ui-text-muted); margin-top: 0.15rem; }

    .status-badge {
      flex-shrink: 0; padding: 0.25rem 0.65rem; border-radius: 999px; font-size: 0.72rem; font-weight: 700;
    }
    .status-badge.pending { background: rgba(245, 158, 11, 0.18); color: #f59e0b; }
    .status-badge.accepted { background: rgba(16, 185, 129, 0.18); color: #10b981; }
    .status-badge.cancelled { background: rgba(239, 68, 68, 0.18); color: #ef4444; }

    .order-items { list-style: none; margin: 0 0 0.6rem; padding: 0; display: flex; flex-direction: column; gap: 0.3rem; }
    .order-items li { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: var(--ui-text-secondary); }
    .item-qty { font-weight: 700; color: var(--ui-accent); min-width: 28px; }
    .item-name { flex: 1; }
    .item-total { color: var(--ui-text-muted); }

    .cancel-reason {
      margin: 0 0 0.6rem; padding: 0.5rem 0.7rem; border-radius: 8px; font-size: 0.8rem;
      background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; color: var(--ui-text-secondary);
    }

    .order-footer {
      display: flex; align-items: center; justify-content: space-between;
      font-size: 0.78rem; color: var(--ui-text-muted); padding-top: 0.5rem; border-top: 1px solid var(--ui-border);
    }
    .order-total { font-weight: 700; color: var(--ui-text); }
  `],
})
export class MisComprasComponent implements OnInit {
  private carpetaService = inject(CarpetaService);
  private riftboundService = inject(RiftboundService);
  private route = inject(ActivatedRoute);
  auth = inject(AuthService);

  game = signal<Game>('myl');
  storeToken = signal<string | null>(null);
  statusFilter = signal<StatusFilter>('');
  loading = signal(false);
  orders = signal<AnyOrder[]>([]);

  readonly statusOptions: { value: StatusFilter; label: string }[] = [
    { value: '', label: 'Todos' },
    { value: 'pending', label: 'Pendiente' },
    { value: 'accepted', label: 'Aceptado' },
    { value: 'cancelled', label: 'Cancelado' },
  ];

  ngOnInit() {
    const gameParam = this.route.snapshot.queryParamMap.get('game');
    if (gameParam === 'riftbound' || gameParam === 'myl') this.game.set(gameParam);
    const storeParam = this.route.snapshot.queryParamMap.get('store');
    if (storeParam) this.storeToken.set(storeParam);
    if (this.auth.isAuthenticated()) this.loadOrders();
  }

  setGame(game: Game) {
    if (this.game() === game) return;
    this.game.set(game);
    this.loadOrders();
  }

  setStatusFilter(status: StatusFilter) {
    if (this.statusFilter() === status) return;
    this.statusFilter.set(status);
    this.loadOrders();
  }

  private loadOrders() {
    this.loading.set(true);
    const opts: { status?: 'pending' | 'accepted' | 'cancelled'; store?: string } = {};
    if (this.statusFilter()) opts.status = this.statusFilter() as 'pending' | 'accepted' | 'cancelled';
    if (this.storeToken()) opts.store = this.storeToken()!;
    const onSuccess = (res: { results: AnyOrder[] }) => { this.orders.set(res.results || []); this.loading.set(false); };
    const onError = () => { this.orders.set([]); this.loading.set(false); };
    if (this.game() === 'myl') {
      this.carpetaService.listMyPurchaseOrders(opts).subscribe({ next: onSuccess, error: onError });
    } else {
      this.riftboundService.listMyPurchaseOrders(opts).subscribe({ next: onSuccess, error: onError });
    }
  }

  statusLabel(status: StoreOrderStatus | RiftboundStoreOrderStatus): string {
    if (status === 'pending') return 'Pendiente';
    if (status === 'accepted') return 'Aceptado';
    return 'Cancelado';
  }

  formatMoney(value: number): string {
    return `$${value.toLocaleString('es-CL')}`;
  }

  formatDate(value: string): string {
    return new Date(value).toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' });
  }
}
