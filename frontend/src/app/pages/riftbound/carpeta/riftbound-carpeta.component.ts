import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RiftboundService } from '../../../services/riftbound.service';
import { AuthService } from '../../../services/auth.service';
import { RiftboundCardLite, RiftboundCollectionEntry } from '../../../models/riftbound';

@Component({
  selector: 'app-riftbound-carpeta',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="carpeta-container">
      <div class="carpeta-header">
        <div class="binder-avatar-placeholder">📁</div>
        <div class="binder-info">
          <h1>Mi Carpeta · Riftbound</h1>
          <p class="binder-user">{{ auth.user()?.username || 'Invitado' }}</p>
        </div>
      </div>

      <div class="tabs">
        <button class="tab" [class.active]="activeTab() === 'collection'" (click)="activeTab.set('collection')">
          📁 COLECCIÓN
        </button>
        <button class="tab" [class.active]="activeTab() === 'add'" (click)="activeTab.set('add')">
          ➕ AÑADIR
        </button>
        <button class="tab" [class.active]="activeTab() === 'stats'" (click)="activeTab.set('stats')">
          📊 STATS
        </button>
      </div>

      <!-- ═══ COLLECTION ═══ -->
      @if (activeTab() === 'collection') {
        <div class="tab-content">
          <div class="tab-toolbar">
            <input type="search" class="search-input"
                   placeholder="Filtrar tu colección…"
                   [(ngModel)]="filterText" />
          </div>

          @if (loading()) {
            <p class="muted">Cargando…</p>
          }

          <p class="results-count">{{ filtered().length }} cartas en tu colección · {{ totalCopies() }} copias</p>

          <div class="card-grid">
            @for (e of filtered(); track e.id) {
              <div class="entry-card">
                @if (e.card_data?.image) {
                  <img [src]="e.card_data!.image" [alt]="e.card_data!.name" loading="lazy" />
                } @else {
                  <div class="img-fallback">{{ e.card_data?.card_number }}</div>
                }
                <div class="entry-meta">
                  <strong>{{ e.card_data?.name }}</strong>
                  <small>{{ e.card_data?.card_number }}</small>
                  <div class="qty-controls">
                    <button class="ctrl" (click)="changeQty(e, -1)">−</button>
                    <input type="number" min="0" [ngModel]="e.quantity" (ngModelChange)="setQty(e, $event)" />
                    <button class="ctrl" (click)="changeQty(e, 1)">+</button>
                    <button class="ctrl remove" (click)="remove(e)" title="Quitar">✕</button>
                  </div>
                </div>
              </div>
            }
          </div>

          @if (!loading() && entries().length === 0) {
            <div class="empty-state">
              <p>Tu carpeta está vacía. Pulsa <strong>➕ AÑADIR</strong> para empezar.</p>
            </div>
          }
        </div>
      }

      <!-- ═══ ADD ═══ -->
      @if (activeTab() === 'add') {
        <div class="tab-content">
          <div class="tab-toolbar">
            <input type="search" class="search-input"
                   placeholder="Buscar carta por nombre, número o texto…"
                   [(ngModel)]="addSearch"
                   (ngModelChange)="onAddSearch()" />
            <select [(ngModel)]="addType" (ngModelChange)="searchToAdd()">
              <option value="">Todos los tipos</option>
              <option value="unit">Unidad</option>
              <option value="spell">Hechizo</option>
              <option value="champion">Champion</option>
              <option value="legend">Legend</option>
              <option value="gear">Gear</option>
              <option value="battlefield">Battlefield</option>
              <option value="rune">Runa</option>
            </select>
          </div>

          @if (addLoading()) { <p class="muted">Buscando…</p> }

          <div class="card-grid">
            @for (c of addResults(); track c.id) {
              <div class="entry-card add-card">
                @if (c.image) {
                  <img [src]="c.image" [alt]="c.name" loading="lazy" />
                } @else {
                  <div class="img-fallback">{{ c.card_number }}</div>
                }
                <div class="entry-meta">
                  <strong>{{ c.name }}</strong>
                  <small>{{ c.card_number }}</small>
                  <button class="add-btn" (click)="add(c)">
                    + Añadir @if (currentQty(c.id); as q) { ({{ q }} en carpeta) }
                  </button>
                </div>
              </div>
            }
          </div>

          @if (!addLoading() && addResults().length === 0 && addSearch.length >= 2) {
            <p class="muted center">Sin resultados.</p>
          }
        </div>
      }

      <!-- ═══ STATS ═══ -->
      @if (activeTab() === 'stats') {
        <div class="tab-content">
          <div class="stats-grid">
            <div class="stat-card">
              <span class="stat-label">Cartas únicas</span>
              <span class="stat-value">{{ entries().length }}</span>
            </div>
            <div class="stat-card">
              <span class="stat-label">Copias totales</span>
              <span class="stat-value">{{ totalCopies() }}</span>
            </div>
            <div class="stat-card">
              <span class="stat-label">Sets distintos</span>
              <span class="stat-value">{{ uniqueSets().length }}</span>
            </div>
          </div>

          <h3>Por tipo</h3>
          <div class="dist-bars">
            @for (kv of typeStats(); track kv.key) {
              <div class="dist-row">
                <span class="dist-label">{{ kv.key }}</span>
                <div class="dist-bar">
                  <div class="dist-fill" [style.width]="(kv.value / totalCopies() * 100) + '%'"></div>
                </div>
                <span class="dist-num">{{ kv.value }}</span>
              </div>
            }
          </div>

          <h3>Por set</h3>
          <div class="dist-bars">
            @for (kv of setStats(); track kv.key) {
              <div class="dist-row">
                <span class="dist-label">{{ kv.key }}</span>
                <div class="dist-bar">
                  <div class="dist-fill" [style.width]="(kv.value / totalCopies() * 100) + '%'"></div>
                </div>
                <span class="dist-num">{{ kv.value }}</span>
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .carpeta-container { max-width: 1200px; margin: 0 auto; padding: 1.5rem 1rem; }

    /* Header */
    .carpeta-header {
      display: flex; align-items: center; gap: 1rem;
      background: #0f0f23; border: 1px solid #1e3a4a; border-radius: 12px;
      padding: 1rem 1.25rem; margin-bottom: 1rem;
    }
    .binder-avatar-placeholder {
      width: 80px; height: 80px; border-radius: 50%;
      background: linear-gradient(135deg, #e94560, #fff);
      display: grid; place-items: center; font-size: 2.5rem;
    }
    .binder-info h1 { margin: 0; font-size: 1.6rem;
      background: linear-gradient(90deg, #e94560, #fff);
      -webkit-background-clip: text; background-clip: text; color: transparent;
    }
    .binder-user { margin: .15rem 0 0; opacity: .65; }

    /* Tabs */
    .tabs {
      display: flex; gap: .35rem; border-bottom: 2px solid #1e3a4a;
      margin-bottom: 1rem; overflow-x: auto;
    }
    .tab {
      padding: .65rem 1rem; border: none; background: transparent;
      color: #98a2a8; font-weight: 700; font-size: .85rem;
      cursor: pointer; border-bottom: 3px solid transparent;
      transition: all .15s; white-space: nowrap;
    }
    .tab:hover { color: #fff; }
    .tab.active { color: #e94560; border-bottom-color: #e94560; }

    /* Toolbar */
    .tab-toolbar {
      display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 1rem;
    }
    .search-input, select {
      padding: .55rem .8rem; border: 1px solid #2a3a4a; border-radius: 6px;
      background: #0f0f23; color: #e0e0e0; outline: none;
    }
    .search-input { flex: 1; min-width: 220px; }
    .search-input:focus, select:focus { border-color: #e94560; }
    .results-count { color: #98a2a8; font-size: .85rem; margin: 0 0 .75rem; }

    /* Grid */
    .card-grid {
      display: grid; gap: .75rem;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    }
    .entry-card {
      background: #0f0f23; border: 1px solid #1e3a4a; border-radius: 10px;
      padding: .55rem; display: flex; flex-direction: column; gap: .5rem;
      transition: all .15s;
    }
    .entry-card:hover { border-color: #e94560; transform: translateY(-2px); }
    .entry-card img { width: 100%; aspect-ratio: 63/88; object-fit: cover; border-radius: 6px; background: #16213e; }
    .img-fallback {
      width: 100%; aspect-ratio: 63/88; background: #16213e; border-radius: 6px;
      display: grid; place-items: center; font-size: .9rem; color: #c8c8da; text-align: center;
    }
    .entry-meta { display: flex; flex-direction: column; gap: .15rem; min-width: 0; }
    .entry-meta strong {
      color: #fff; font-size: .85rem;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .entry-meta small { color: #6a7a88; font-size: .7rem; }

    .qty-controls { display: flex; gap: .25rem; align-items: center; margin-top: .35rem; }
    .qty-controls input {
      width: 50px; padding: .25rem .35rem; text-align: center;
      border: 1px solid #2a3a4a; border-radius: 4px; background: #0f0f23; color: #e0e0e0;
    }
    .ctrl {
      width: 28px; height: 28px; border-radius: 4px;
      border: 1px solid #2a3a4a; background: #0f0f23; color: #c8c8da;
      cursor: pointer; font-size: 1rem; line-height: 1;
    }
    .ctrl:hover { border-color: #e94560; color: #e94560; }
    .ctrl.remove:hover { border-color: #e94560; color: #e94560; }

    .add-btn {
      width: 100%; padding: .35rem .5rem; border: 1px solid #e94560;
      background: transparent; color: #e94560; border-radius: 4px; cursor: pointer;
      font-size: .8rem; font-weight: 600; margin-top: .35rem;
    }
    .add-btn:hover { background: #e94560; color: #0f0f23; }

    /* Empty / center */
    .empty-state {
      text-align: center; padding: 3rem 1rem;
      background: #0f0f23; border: 1px dashed #1e3a4a; border-radius: 10px;
      color: #98a2a8;
    }
    .muted { opacity: .65; }
    .center { text-align: center; }

    /* Stats */
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: .75rem; margin-bottom: 1.5rem; }
    .stat-card {
      background: #0f0f23; border: 1px solid #1e3a4a; border-radius: 10px;
      padding: 1rem; display: flex; flex-direction: column; align-items: center;
    }
    .stat-label { font-size: .75rem; color: #98a2a8; text-transform: uppercase; letter-spacing: .05em; }
    .stat-value { font-size: 2rem; font-weight: 700; color: #e94560; }

    .tab-content h3 { color: #fff; margin: 1.5rem 0 .75rem; font-size: 1.1rem; }
    .dist-bars { display: flex; flex-direction: column; gap: .35rem; }
    .dist-row { display: grid; grid-template-columns: 100px 1fr 50px; gap: .5rem; align-items: center; }
    .dist-label { color: #c8c8da; font-size: .85rem; }
    .dist-bar { height: 12px; background: rgba(30,58,74,.4); border-radius: 6px; overflow: hidden; }
    .dist-fill { height: 100%; background: linear-gradient(90deg, #fff, #e94560); transition: width .3s; }
    .dist-num { color: #e94560; font-weight: 600; font-size: .85rem; text-align: right; }

    /* Light theme */
    :host-context(body.light-theme) .carpeta-header,
    :host-context(body.light-theme) .entry-card,
    :host-context(body.light-theme) .stat-card,
    :host-context(body.light-theme) .empty-state { background: #fbf6e9; border-color: #d4c489; }
    :host-context(body.light-theme) .entry-meta strong,
    :host-context(body.light-theme) .tab-content h3 { color: #463714; }
    :host-context(body.light-theme) .search-input,
    :host-context(body.light-theme) select,
    :host-context(body.light-theme) .qty-controls input,
    :host-context(body.light-theme) .ctrl { background: #ffffff; border-color: #d4c489; color: #2a1f10; }
  `],
})
export class RiftboundCarpetaComponent implements OnInit {
  private rb = inject(RiftboundService);
  auth = inject(AuthService);

  activeTab = signal<'collection' | 'add' | 'stats'>('collection');

  // Collection
  entries = signal<RiftboundCollectionEntry[]>([]);
  loading = signal(true);
  filterText = '';

  // Add tab
  addSearch = '';
  addType = '';
  addResults = signal<RiftboundCardLite[]>([]);
  addLoading = signal(false);
  private addTimer: ReturnType<typeof setTimeout> | null = null;

  filtered = computed(() => {
    const txt = this.filterText.trim().toLowerCase();
    if (!txt) return this.entries();
    return this.entries().filter(e => {
      const c = e.card_data;
      return c && (
        c.name.toLowerCase().includes(txt) ||
        c.card_number.toLowerCase().includes(txt)
      );
    });
  });

  totalCopies = computed(() =>
    this.entries().reduce((s, e) => s + e.quantity, 0));

  uniqueSets = computed(() => {
    const sets = new Set<string>();
    for (const e of this.entries()) {
      const code = e.card_data?.card_number?.split('-')[0];
      if (code) sets.add(code);
    }
    return [...sets];
  });

  typeStats = computed(() => {
    const m: Record<string, number> = {};
    for (const e of this.entries()) {
      const t = e.card_data?.card_type ?? 'other';
      m[t] = (m[t] ?? 0) + e.quantity;
    }
    return Object.entries(m).map(([key, value]) => ({ key, value }))
      .sort((a, b) => b.value - a.value);
  });

  setStats = computed(() => {
    const m: Record<string, number> = {};
    for (const e of this.entries()) {
      const code = e.card_data?.card_number?.split('-')[0] ?? '?';
      m[code] = (m[code] ?? 0) + e.quantity;
    }
    return Object.entries(m).map(([key, value]) => ({ key, value }))
      .sort((a, b) => b.value - a.value);
  });

  ngOnInit() {
    this.rb.listCollection().subscribe({
      next: (r) => { this.entries.set(r.results); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  // ── Add tab ──
  onAddSearch() {
    if (this.addTimer) clearTimeout(this.addTimer);
    this.addTimer = setTimeout(() => this.searchToAdd(), 300);
  }

  searchToAdd() {
    if (!this.addSearch.trim() && !this.addType) {
      this.addResults.set([]);
      return;
    }
    this.addLoading.set(true);
    this.rb.listCards({
      search: this.addSearch || undefined,
      type: this.addType || undefined,
      lite: true,
    }).subscribe({
      next: (resp) => {
        this.addResults.set(resp.results.slice(0, 30) as RiftboundCardLite[]);
        this.addLoading.set(false);
      },
      error: () => this.addLoading.set(false),
    });
  }

  currentQty(cardId: number): number {
    return this.entries().find(e => e.card === cardId)?.quantity ?? 0;
  }

  add(c: RiftboundCardLite) {
    const existing = this.entries().find(e => e.card === c.id);
    const qty = (existing?.quantity || 0) + 1;
    this.rb.upsertCollection({ card: c.id, quantity: qty, is_foil: false }).subscribe({
      next: (entry) => {
        const list = this.entries().filter(e => e.id !== entry.id);
        this.entries.set([entry, ...list]);
      },
    });
  }

  changeQty(e: RiftboundCollectionEntry, delta: number) {
    const newQty = Math.max(0, e.quantity + delta);
    if (newQty === 0) { this.remove(e); return; }
    this.rb.upsertCollection({ card: e.card, quantity: newQty, is_foil: e.is_foil }).subscribe({
      next: (updated) => {
        this.entries.set(this.entries().map(x => x.id === updated.id ? updated : x));
      },
    });
  }

  setQty(e: RiftboundCollectionEntry, qty: number) {
    const n = Math.max(0, Number(qty) || 0);
    if (n === 0) { this.remove(e); return; }
    this.rb.upsertCollection({ card: e.card, quantity: n, is_foil: e.is_foil }).subscribe({
      next: (updated) => {
        this.entries.set(this.entries().map(x => x.id === updated.id ? updated : x));
      },
    });
  }

  remove(e: RiftboundCollectionEntry) {
    this.rb.deleteCollection(e.id).subscribe({
      next: () => this.entries.set(this.entries().filter(x => x.id !== e.id)),
    });
  }
}
