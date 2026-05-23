import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { RiftboundService } from '../../../services/riftbound.service';
import { AuthService } from '../../../services/auth.service';
import { RiftboundDeck, RiftboundColor } from '../../../models/riftbound';

type Tab = 'public' | 'mine';
type SortKey = 'recent' | 'created' | 'cards' | 'name' | 'name_desc';

const COLOR_HEX: Record<RiftboundColor, string> = {
  fury: '#e94560',
  calm: '#4caf50',
  mind: '#3aa6ff',
  body: '#ff9a3c',
  chaos: '#9c5dff',
  order: '#ff6b7d',
  neutral: '#888',
};

const COLOR_LABEL: Record<RiftboundColor, string> = {
  fury: 'Fury', calm: 'Calm', mind: 'Mind',
  body: 'Body', chaos: 'Chaos', order: 'Order', neutral: 'Neutral',
};

@Component({
  selector: 'app-riftbound-decks',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="rb-decks-container">
      <h1 class="page-title">Mazos Riftbound</h1>

      @if (auth.isAuthenticated()) {
        <div class="toolbar-row" role="tablist">
          <div class="tabs">
            <button role="tab" [class.active]="activeTab() === 'public'" (click)="setTab('public')">
              🌐 <span>Públicos</span>
            </button>
            <button role="tab" [class.active]="activeTab() === 'mine'" (click)="setTab('mine')">
              👤 <span>Míos</span>
            </button>
          </div>
        </div>
      }

      <!-- Filtros -->
      <div class="filter-toolbar">
        <div class="search-bar">
          <span class="search-icon">🔍</span>
          <input type="text"
                 placeholder="Buscar mazos..."
                 [(ngModel)]="search"
                 (keyup.enter)="reload()"
                 aria-label="Buscar mazos" />
          @if (search) {
            <button class="search-clear" (click)="search=''; reload()">✕</button>
          }
          <button class="btn-search-go" (click)="reload()">Buscar</button>
        </div>

        <div class="filter-row">
          <div class="color-chips" role="group" aria-label="Filtrar por color">
            @for (c of colors; track c.code) {
              <button type="button"
                      class="color-chip"
                      [class.active]="filterColor === c.code"
                      [style.--c]="c.hex"
                      (click)="toggleColor(c.code)">
                <span class="dot"></span>{{ c.label }}
              </button>
            }
            @if (filterColor) {
              <button class="btn-clear" (click)="filterColor=''; reload()">✕ Color</button>
            }
          </div>

          <select [(ngModel)]="sort" (change)="reload()" class="sort-select" aria-label="Ordenar por">
            @for (opt of sortOptions; track opt.value) {
              <option [value]="opt.value">{{ opt.label }}</option>
            }
          </select>
        </div>
      </div>

      <!-- Header con botón Crear -->
      @if (activeTab() === 'mine') {
        <div class="my-decks-header">
          <span class="results-count">
            @if (totalCount() > 0) { {{ totalCount() }} mazo{{ totalCount() === 1 ? '' : 's' }} }
          </span>
          <a routerLink="/riftbound/builder" class="btn-create">+ Crear mazo</a>
        </div>
      }

      <!-- Loading skeletons -->
      @if (loading() && decks().length === 0) {
        <div class="deck-grid">
          @for (s of skeletonRange; track $index) {
            <div class="deck-card skeleton">
              <div class="deck-cover skeleton-block"></div>
              <div class="skeleton-line w-70"></div>
              <div class="skeleton-line w-40"></div>
            </div>
          }
        </div>
      } @else {
        <div class="deck-grid">
          @for (deck of decks(); track deck.id) {
            <div class="deck-card" [style.--accent]="getAccent(deck)">
              <a class="cover-link" [routerLink]="['/riftbound/decks', deck.id]" tabindex="-1">
                @if (deck.cover_card_data?.image; as img) {
                  <div class="deck-cover single">
                    <img [src]="img" [alt]="deck.cover_card_data?.name || ''" loading="lazy" decoding="async" />
                    <div class="cover-fade"></div>
                  </div>
                } @else {
                  <div class="deck-cover empty-cover">⚔️</div>
                }
              </a>

              <div class="deck-body">
                <a class="deck-title-link" [routerLink]="['/riftbound/decks', deck.id]">
                  <h3 class="deck-name">{{ deck.name }}</h3>
                </a>

                <div class="deck-tags">
                  @for (col of deck.primary_colors || []; track col) {
                    <span class="color-tag" [style.--c]="hex(col)">
                      <span class="dot"></span>{{ label(col) }}
                    </span>
                  }
                  <span class="card-count">📚 {{ countCards(deck) }}</span>
                </div>

                @if (deck.description) {
                  <p class="deck-desc">{{ deck.description }}</p>
                }

                <div class="deck-footer">
                  @if (activeTab() === 'mine') {
                    <span class="deck-visibility" [class.public]="deck.is_public">
                      {{ deck.is_public ? '🌐 Público' : '🔒 Privado' }}
                    </span>
                  } @else {
                    <span class="deck-author">👤 {{ deck.owner_username }}</span>
                  }
                  <span class="deck-date">{{ formatDate(deck.updated_at) }}</span>
                </div>

                @if (activeTab() === 'mine') {
                  <div class="deck-actions">
                    <a [routerLink]="['/riftbound/builder', deck.id]" class="action-btn action-edit">
                      ✏️ Editar
                    </a>
                    <button class="action-btn action-delete" (click)="deleteDeck(deck.id)">🗑</button>
                  </div>
                }
              </div>
            </div>
          } @empty {
            <p class="empty">
              @if (activeTab() === 'mine') {
                No tienes mazos aún. <a routerLink="/riftbound/builder">Crea uno aquí</a>.
              } @else {
                No hay mazos públicos para mostrar.
              }
            </p>
          }
        </div>

        @if (totalPages() > 1) {
          <div class="pagination">
            <button class="btn-page" (click)="prev()" [disabled]="page() === 1">← Anterior</button>
            <span>Página {{ page() }} de {{ totalPages() }}</span>
            <button class="btn-page" (click)="next()" [disabled]="page() >= totalPages()">Siguiente →</button>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .rb-decks-container { max-width: 1200px; margin: 0 auto; padding: 1.5rem 1rem; }
    .page-title { font-size: 1.6rem; margin: 0 0 1rem; color: #fff; font-weight: 700; }

    /* Tabs */
    .toolbar-row { display: flex; gap: .75rem; margin-bottom: 1rem; flex-wrap: wrap; }
    .tabs {
      display: inline-flex; gap: .25rem; padding: .25rem;
      background: #111827; border: 1px solid #2a2a4a; border-radius: 10px;
    }
    .tabs button {
      padding: .45rem .95rem; border: 0; background: transparent; color: #aaa;
      border-radius: 7px; font-size: .85rem; font-family: inherit; cursor: pointer;
      transition: all .15s; white-space: nowrap;
      display: inline-flex; align-items: center; gap: .4rem;
    }
    .tabs button.active { background: #e94560; color: #0f0f23; font-weight: 600; }
    .tabs button:hover:not(.active) { background: #1f1f3a; color: #fff; }

    /* Filtros */
    .filter-toolbar { display: flex; flex-direction: column; gap: .6rem; margin-bottom: 1.25rem; }
    .search-bar { position: relative; display: flex; gap: .5rem; align-items: center; }
    .search-bar .search-icon {
      position: absolute; left: .75rem; top: 50%; transform: translateY(-50%);
      color: #666; pointer-events: none; font-size: .9rem;
    }
    .search-bar input {
      flex: 1; padding: .6rem 2.4rem .6rem 2.2rem;
      border: 1px solid #333; border-radius: 8px; background: #1a1a2e;
      color: #e0e0e0; outline: none; font: inherit;
    }
    .search-bar input:focus { border-color: #e94560; }
    .search-clear {
      position: absolute; right: 5.6rem; top: 50%; transform: translateY(-50%);
      background: transparent; border: 0; color: #888; cursor: pointer;
      padding: .2rem .4rem; border-radius: 4px;
    }
    .search-clear:hover { color: #fff; background: #2a2a4a; }
    .btn-search-go {
      padding: .55rem 1rem; background: #e94560; color: #0f0f23;
      border: none; border-radius: 8px; font-weight: 600; cursor: pointer;
    }
    .btn-search-go:hover { filter: brightness(1.1); }

    .filter-row { display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; }
    .color-chips { display: flex; gap: .35rem; flex-wrap: wrap; align-items: center; }
    .color-chip {
      display: inline-flex; align-items: center; gap: .35rem;
      padding: .35rem .65rem; border: 1px solid #2a2a4a; border-radius: 999px;
      background: #111827; color: #c8c8da; font-size: .78rem; cursor: pointer;
      transition: all .15s; font-family: inherit;
    }
    .color-chip:hover { border-color: var(--c); color: #fff; }
    .color-chip.active { background: var(--c); color: #0f0f23; border-color: var(--c); font-weight: 600; }
    .color-chip .dot {
      width: 10px; height: 10px; border-radius: 50%; background: var(--c);
      border: 1px solid rgba(255,255,255,.25);
    }
    .color-chip.active .dot { background: rgba(0,0,0,.3); border-color: rgba(0,0,0,.4); }

    .btn-clear {
      padding: .35rem .75rem; border: 1px solid #e94560;
      background: rgba(233,69,96,.08); color: #e94560; border-radius: 6px;
      font-size: .78rem; cursor: pointer; font-family: inherit;
    }
    .btn-clear:hover { background: rgba(233,69,96,.18); }

    .sort-select {
      margin-left: auto; padding: .5rem .8rem; border: 1px solid #2a2a4a;
      border-radius: 8px; background: #111827; color: #e0e0e0;
      font-size: .85rem; cursor: pointer; font-family: inherit; outline: none;
    }
    .sort-select:focus { border-color: #e94560; }

    .my-decks-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .results-count { color: #777; font-size: .85rem; }
    .btn-create {
      padding: .55rem 1rem; background: linear-gradient(135deg, #e94560 0%, #ff6b7d 100%);
      color: #0f0f23; border-radius: 8px; text-decoration: none; font-weight: 700;
    }
    .btn-create:hover { filter: brightness(1.1); }

    /* Grid */
    .deck-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
    @media (max-width: 600px) { .deck-grid { grid-template-columns: 1fr; gap: 0.75rem; } .rb-decks-container { padding: 1rem 0.65rem 2rem; } }
    .deck-card {
      --accent: #e94560;
      position: relative; background: #1a1a2e; border: 1px solid #2a2a4a;
      border-radius: 12px; overflow: hidden;
      transition: transform .15s, border-color .15s, box-shadow .15s;
      display: flex; flex-direction: column; color: inherit;
    }
    .deck-card::before {
      content: ''; position: absolute; left: 0; top: 0; bottom: 0;
      width: 4px; background: var(--accent); z-index: 2;
    }
    .deck-card:hover {
      border-color: var(--accent); transform: translateY(-3px);
      box-shadow: 0 8px 22px rgba(0,0,0,.4);
    }

    .cover-link { display: block; text-decoration: none; color: inherit; }
    .deck-cover {
      position: relative; width: 100%; height: 140px; overflow: hidden;
      background: #0f0f1e; border-bottom: 1px solid #2a2a4a;
    }
    .deck-cover.single img { width: 100%; height: 100%; object-fit: cover; object-position: center 22%; display: block; }
    .deck-cover.empty-cover { display: flex; align-items: center; justify-content: center; color: #2a2a4a; font-size: 2.4rem; }
    .cover-fade { position: absolute; inset: 0; pointer-events: none;
      background: linear-gradient(180deg, transparent 35%, rgba(26,26,46,.85) 100%);
    }

    .deck-body { padding: .85rem .95rem .95rem 1.1rem; display: flex; flex-direction: column; flex: 1; }
    .deck-name {
      font-size: 1.05rem; color: #fff; margin: 0 0 .55rem; line-height: 1.25;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }
    .deck-title-link { text-decoration: none; color: inherit; }
    .deck-title-link:hover .deck-name { color: var(--accent); }

    .deck-tags { display: flex; flex-wrap: wrap; gap: .35rem; align-items: center; margin-bottom: .6rem; }
    .card-count { background: #16213e; padding: .2rem .55rem; border-radius: 4px; font-size: .78rem; color: #ffbd39; white-space: nowrap; }
    .color-tag {
      display: inline-flex; align-items: center; gap: .3rem;
      padding: .18rem .55rem; border-radius: 4px;
      border: 1px solid color-mix(in srgb, var(--c) 40%, transparent);
      background: color-mix(in srgb, var(--c) 12%, transparent);
      color: var(--c); font-size: .75rem; font-weight: 600; white-space: nowrap;
    }
    .color-tag .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--c); }

    .deck-desc {
      color: #888; font-size: .83rem; margin: 0 0 .7rem; line-height: 1.4;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }

    .deck-footer { display: flex; justify-content: space-between; align-items: center; gap: .5rem; font-size: .77rem; color: #777; margin-top: auto; padding-top: .4rem; }
    .deck-author { display: inline-flex; align-items: center; gap: .3rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .deck-visibility { color: #666; }
    .deck-visibility.public { color: #4ade80; }
    .deck-date { color: #666; }

    .deck-actions { display: flex; gap: .5rem; margin-top: .6rem; padding-top: .6rem; border-top: 1px dashed #2a2a4a; }
    .action-btn {
      display: inline-flex; align-items: center; justify-content: center;
      gap: .4rem; padding: .42rem .75rem; border-radius: 8px;
      font-size: .85rem; font-weight: 500; text-decoration: none;
      border: 1px solid transparent; cursor: pointer; background: transparent;
      transition: background-color .15s, border-color .15s, color .15s; font-family: inherit;
    }
    .action-edit { flex: 1; color: #c9c9e6; border-color: #3a3a5e; }
    .action-edit:hover { color: #fff; background: rgba(99,102,241,.12); border-color: #6366f1; }
    .action-delete { flex: 0 0 auto; width: 38px; color: #d97a7a; border-color: #4a2a2a; }
    .action-delete:hover { color: #fff; background: rgba(220,53,69,.18); border-color: #dc3545; }

    /* Skeletons */
    .deck-card.skeleton { pointer-events: none; }
    .skeleton-block {
      height: 140px;
      background: linear-gradient(90deg, #1f1f3a 0%, #2a2a4a 50%, #1f1f3a 100%);
      background-size: 200% 100%; animation: shimmer 1.4s linear infinite;
      border-bottom: 1px solid #2a2a4a;
    }
    .skeleton-line {
      height: .7rem; margin: .6rem .95rem;
      background: linear-gradient(90deg, #1f1f3a 0%, #2a2a4a 50%, #1f1f3a 100%);
      background-size: 200% 100%; border-radius: 4px;
      animation: shimmer 1.4s linear infinite;
    }
    .w-70 { width: 70%; } .w-40 { width: 40%; }
    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .empty { grid-column: 1/-1; text-align: center; color: #777; padding: 3rem 1rem; }
    .empty a { color: #e94560; }
    .pagination { display: flex; justify-content: center; align-items: center; gap: 1rem; margin-top: 1.5rem; color: #aaa; font-size: .9rem; }
    .btn-page { padding: .45rem .85rem; background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 6px; color: #e0e0e0; cursor: pointer; font-family: inherit; }
    .btn-page:hover:not(:disabled) { border-color: #e94560; }
    .btn-page:disabled { opacity: .4; cursor: not-allowed; }
  `],
})
export class RiftboundDecksComponent implements OnInit {
  private rb = inject(RiftboundService);
  auth = inject(AuthService);

  decks = signal<RiftboundDeck[]>([]);
  loading = signal(true);
  page = signal(1);
  totalCount = signal(0);
  activeTab = signal<Tab>('public');
  readonly pageSize = 20;
  totalPages = () => Math.max(1, Math.ceil(this.totalCount() / this.pageSize));

  search = '';
  filterColor: '' | RiftboundColor = '';
  sort: SortKey = 'recent';

  readonly skeletonRange = Array.from({ length: 6 });

  readonly colors = (Object.keys(COLOR_HEX) as RiftboundColor[]).map(c => ({
    code: c, label: COLOR_LABEL[c], hex: COLOR_HEX[c],
  }));

  readonly sortOptions: { value: SortKey; label: string }[] = [
    { value: 'recent', label: 'Recientes' },
    { value: 'created', label: 'Creación' },
    { value: 'cards', label: 'Más cartas' },
    { value: 'name', label: 'A → Z' },
    { value: 'name_desc', label: 'Z → A' },
  ];

  hex(c: RiftboundColor): string { return COLOR_HEX[c] ?? '#888'; }
  label(c: RiftboundColor): string { return COLOR_LABEL[c] ?? c; }

  getAccent(deck: RiftboundDeck): string {
    return deck.primary_colors?.[0] ? COLOR_HEX[deck.primary_colors[0]] : '#e94560';
  }

  countCards(deck: RiftboundDeck): number {
    return (deck.entries ?? []).reduce((s, e) => s + (e.quantity ?? 0), 0);
  }

  formatDate(s: string): string {
    if (!s) return '';
    const d = new Date(s);
    const now = new Date();
    const diff = (+now - +d) / 1000;
    if (diff < 60) return 'hace un momento';
    if (diff < 3600) return `hace ${Math.floor(diff/60)} min`;
    if (diff < 86400) return `hace ${Math.floor(diff/3600)} h`;
    if (diff < 86400 * 7) return `hace ${Math.floor(diff/86400)} d`;
    return d.toLocaleDateString('es-CL');
  }

  ngOnInit() { this.reload(); }

  setTab(t: Tab) {
    if (this.activeTab() === t) return;
    this.activeTab.set(t);
    this.page.set(1);
    this.reload();
  }

  toggleColor(c: RiftboundColor) {
    this.filterColor = this.filterColor === c ? '' : c;
    this.page.set(1);
    this.reload();
  }

  reload() {
    this.loading.set(true);
    this.rb.listDecks({
      mine: this.activeTab() === 'mine',
      search: this.search.trim() || undefined,
      page: this.page(),
    }).subscribe({
      next: (resp) => {
        let list = resp.results ?? [];
        if (this.filterColor) {
          list = list.filter(d => (d.primary_colors ?? []).includes(this.filterColor as RiftboundColor));
        }
        list = this.sortList(list);
        this.decks.set(list);
        this.totalCount.set(resp.count ?? list.length);
        this.loading.set(false);
      },
      error: () => { this.decks.set([]); this.loading.set(false); },
    });
  }

  sortList(list: RiftboundDeck[]): RiftboundDeck[] {
    const arr = list.slice();
    switch (this.sort) {
      case 'recent': arr.sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at)); break;
      case 'created': arr.sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at)); break;
      case 'cards': arr.sort((a, b) => this.countCards(b) - this.countCards(a)); break;
      case 'name': arr.sort((a, b) => a.name.localeCompare(b.name, 'es')); break;
      case 'name_desc': arr.sort((a, b) => b.name.localeCompare(a.name, 'es')); break;
    }
    return arr;
  }

  prev() { if (this.page() > 1) { this.page.update(p => p - 1); this.reload(); } }
  next() { if (this.page() < this.totalPages()) { this.page.update(p => p + 1); this.reload(); } }

  deleteDeck(id: number) {
    if (!confirm('¿Eliminar este mazo? Esta acción no se puede deshacer.')) return;
    this.rb.deleteDeck(id).subscribe({ next: () => this.reload() });
  }
}
