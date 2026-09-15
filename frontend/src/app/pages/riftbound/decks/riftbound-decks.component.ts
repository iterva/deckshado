import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { RiftboundService } from '../../../services/riftbound.service';
import { AuthService } from '../../../services/auth.service';
import { RiftboundDeck, RiftboundColor } from '../../../models/riftbound';
import { IconComponent } from '../../../components/icon/icon.component';

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
  imports: [CommonModule, FormsModule, RouterLink, IconComponent],
  template: `
    <div class="rb-decks-container">
      <div class="page-header-row">
        <h1 class="page-title rb-page-title">
          <app-icon name="swords" [size]="22"></app-icon> Mazos Riftbound
        </h1>
      </div>

      @if (auth.isAuthenticated()) {
        <div class="toolbar-row" role="tablist">
          <div class="tabs">
            <button role="tab" [class.active]="activeTab() === 'public'" (click)="setTab('public')">
              <app-icon name="library" [size]="14"></app-icon> <span>Públicos</span>
            </button>
            <button role="tab" [class.active]="activeTab() === 'mine'" (click)="setTab('mine')">
              <app-icon name="user" [size]="14"></app-icon> <span>Míos</span>
            </button>
          </div>
        </div>
      }

      <!-- Filtros -->
      <div class="filter-toolbar">
        <div class="search-bar">
          <div class="search-input-wrap">
            <app-icon name="search" [size]="14" class="search-icon"></app-icon>
            <input type="text"
                   placeholder="Buscar mazos..."
                   [(ngModel)]="search"
                   (keyup.enter)="reload()"
                   aria-label="Buscar mazos" />
            @if (search) {
              <button class="search-clear" (click)="search=''; reload()">
                <app-icon name="x" [size]="14"></app-icon>
              </button>
            }
          </div>
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
              <button class="btn-clear" (click)="filterColor=''; reload()">
                <app-icon name="x" [size]="12"></app-icon> Color
              </button>
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
          <a routerLink="/riftbound/builder" class="btn-create">
            <app-icon name="plus" [size]="14"></app-icon> Crear mazo
          </a>
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
                @if (coverUrl(deck); as img) {
                  <div class="deck-cover single">
                    <img [src]="img" [alt]="deck.cover_card_data?.name || ''" loading="lazy" decoding="async"
                         (error)="onCoverError(deck.id)" />
                    <div class="cover-fade"></div>
                  </div>
                } @else {
                  <div class="deck-cover empty-cover">
                    <app-icon name="layers" [size]="28"></app-icon>
                  </div>
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
                  <span class="card-count">
                    <app-icon name="layers" [size]="11"></app-icon> {{ countCards(deck) }}
                  </span>
                </div>

                @if (deck.description) {
                  <p class="deck-desc">{{ deck.description }}</p>
                }

                <div class="deck-footer">
                  @if (activeTab() === 'mine') {
                    <span class="deck-visibility" [class.public]="deck.is_public">
                      <app-icon [name]="deck.is_public ? 'library' : 'shield'" [size]="12"></app-icon>
                      {{ deck.is_public ? 'Público' : 'Privado' }}
                    </span>
                  } @else {
                    <span class="deck-author">
                      <app-icon name="user" [size]="12"></app-icon> {{ deck.owner_username }}
                    </span>
                  }
                  <span class="deck-date">{{ formatDate(deck.updated_at) }}</span>
                </div>

                @if (activeTab() === 'mine') {
                  <div class="deck-actions">
                    <a [routerLink]="['/riftbound/builder', deck.id]" class="action-btn action-edit">
                      <app-icon name="edit" [size]="13"></app-icon> <span>Editar</span>
                    </a>
                    <button class="action-btn action-copy" (click)="duplicateDeck(deck)" [disabled]="duplicatingId() === deck.id" title="Duplicar este mazo">
                      <app-icon name="copy" [size]="13"></app-icon>
                    </button>
                    <button class="action-btn action-delete" (click)="deleteDeck(deck.id)" title="Eliminar mazo">
                      <app-icon name="trash-2" [size]="13"></app-icon>
                    </button>
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
            <button class="btn-page" (click)="prev()" [disabled]="page() === 1">
              <app-icon name="chevron-left" [size]="14"></app-icon> Anterior
            </button>
            <span>Página {{ page() }} de {{ totalPages() }}</span>
            <button class="btn-page" (click)="next()" [disabled]="page() >= totalPages()">
              Siguiente <app-icon name="chevron-right" [size]="14"></app-icon>
            </button>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .rb-decks-container { max-width: 1400px; margin: 0 auto; padding: 1.25rem 1.5rem; }

    .page-header-row {
      margin-bottom: 1.25rem;
    }

    .rb-page-title {
      font-size: 1.3rem;
      font-weight: 700;
      color: #ffffff !important;
      background: none !important;
      -webkit-background-clip: initial !important;
      background-clip: initial !important;
      -webkit-text-fill-color: #ffffff !important;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      letter-spacing: -0.02em;
      margin: 0;

      app-icon { color: var(--ui-accent, #06b6d4); }
    }

    /* Tabs */
    .toolbar-row { display: flex; gap: .75rem; margin-bottom: 1rem; flex-wrap: wrap; }
    .tabs {
      display: inline-flex; gap: .25rem; padding: .25rem;
      background: var(--ui-surface); border: 1px solid var(--ui-border); border-radius: 10px;
    }
    .tabs button {
      padding: .45rem .85rem; border: 0; background: transparent; color: var(--ui-text-muted);
      border-radius: 7px; font-size: .82rem; font-family: inherit; cursor: pointer;
      transition: all .15s ease; white-space: nowrap;
      display: inline-flex; align-items: center; gap: .4rem;
    }
    .tabs button.active { background: rgba(6, 182, 212, 0.15); color: var(--ui-accent, #06b6d4); font-weight: 600; }
    .tabs button:hover:not(.active) { background: rgba(255, 255, 255, 0.05); color: #fff; }

    /* Filtros */
    .filter-toolbar { display: flex; flex-direction: column; gap: .6rem; margin-bottom: 1.25rem; }
    .search-bar { position: relative; display: flex; gap: .5rem; align-items: center; }
    .search-input-wrap {
      position: relative; flex: 1; min-width: 0;
      display: flex; align-items: center;
    }
    .search-input-wrap .search-icon {
      position: absolute; left: .75rem; color: var(--ui-text-muted); pointer-events: none;
    }
    .search-input-wrap input {
      width: 100%; padding: .6rem 2.4rem .6rem 2.2rem;
      border: 1px solid var(--ui-border); border-radius: 8px; background: var(--ui-surface);
      color: #ffffff; outline: none; font: inherit; font-size: 0.875rem;
      transition: border-color 0.15s ease;
    }
    .search-input-wrap input:focus { border-color: var(--ui-accent, #06b6d4); }
    .search-clear {
      position: absolute; right: .55rem;
      background: transparent; border: 0; color: var(--ui-text-muted); cursor: pointer;
      display: flex; align-items: center; padding: 2px;
    }
    .search-clear:hover { color: #fff; }
    .btn-search-go {
      padding: .6rem 1.1rem; background: var(--ui-accent, #06b6d4); color: #09090b;
      border: none; border-radius: 8px; font-weight: 600; cursor: pointer;
      font-size: 0.85rem; transition: opacity 0.15s ease;
    }
    .btn-search-go:hover { opacity: 0.9; }

    .filter-row { display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; }
    .color-chips { display: flex; gap: .35rem; flex-wrap: wrap; align-items: center; }
    .color-chip {
      display: inline-flex; align-items: center; gap: .35rem;
      padding: .3rem .65rem; border: 1px solid var(--ui-border); border-radius: 999px;
      background: var(--ui-surface); color: var(--ui-text-muted); font-size: .78rem; cursor: pointer;
      transition: all .15s ease; font-family: inherit;
    }
    .color-chip:hover { border-color: var(--c); color: #fff; }
    .color-chip.active { background: color-mix(in srgb, var(--c) 15%, var(--ui-surface)); color: #fff; border-color: var(--c); font-weight: 600; }
    .color-chip .dot {
      width: 8px; height: 8px; border-radius: 50%; background: var(--c);
    }

    .btn-clear {
      display: inline-flex; align-items: center; gap: 0.25rem;
      padding: .3rem .65rem; border: 1px solid rgba(239, 68, 68, 0.4);
      background: rgba(239, 68, 68, 0.1); color: #ef4444; border-radius: 6px;
      font-size: .78rem; cursor: pointer; font-family: inherit;
    }
    .btn-clear:hover { background: rgba(239, 68, 68, 0.2); }

    .sort-select {
      margin-left: auto; padding: .5rem .75rem; border: 1px solid var(--ui-border);
      border-radius: 8px; background: var(--ui-surface); color: var(--ui-text-muted);
      font-size: .82rem; cursor: pointer; font-family: inherit; outline: none;
    }
    .sort-select:focus { border-color: var(--ui-accent, #06b6d4); }
    .sort-select option { background: #18181b; }

    .my-decks-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .results-count { color: var(--ui-text-muted); font-size: .85rem; }
    .btn-create {
      display: inline-flex; align-items: center; gap: 0.35rem;
      padding: .5rem 1rem; background: var(--ui-accent, #06b6d4);
      color: #09090b; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.85rem;
      transition: opacity 0.15s ease;
    }
    .btn-create:hover { opacity: 0.9; }

    /* Grid */
    .deck-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
    @media (max-width: 600px) { .deck-grid { grid-template-columns: 1fr; gap: 0.75rem; } }

    .deck-card {
      --accent: #06b6d4;
      position: relative; background: var(--ui-surface); border: 1px solid var(--ui-border);
      border-radius: 12px; overflow: hidden;
      transition: transform .15s ease, border-color .15s ease, box-shadow .15s ease;
      display: flex; flex-direction: column; color: inherit;
    }
    .deck-card:hover {
      border-color: var(--accent); transform: translateY(-2px);
      box-shadow: 0 8px 30px rgba(0,0,0,.3);
    }

    .cover-link { display: block; text-decoration: none; color: inherit; }
    .deck-cover {
      position: relative; width: 100%; height: 140px; overflow: hidden;
      background: #09090b; border-bottom: 1px solid var(--ui-border);
    }
    .deck-cover.single img { width: 100%; height: 100%; object-fit: cover; object-position: center 22%; display: block; }
    .deck-cover.empty-cover { display: flex; align-items: center; justify-content: center; color: var(--ui-text-muted); }
    .cover-fade { position: absolute; inset: 0; pointer-events: none;
      background: linear-gradient(180deg, transparent 40%, rgba(9,9,11,.85) 100%);
    }

    .deck-body { padding: .85rem .95rem; display: flex; flex-direction: column; flex: 1; }
    .deck-name {
      font-size: 1rem; font-weight: 600; color: #ffffff; margin: 0 0 .5rem; line-height: 1.3;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }
    .deck-title-link { text-decoration: none; color: inherit; }
    .deck-title-link:hover .deck-name { color: var(--accent); }

    .deck-tags { display: flex; flex-wrap: wrap; gap: .35rem; align-items: center; margin-bottom: .55rem; }
    .card-count {
      display: inline-flex; align-items: center; gap: 0.25rem;
      background: rgba(255, 255, 255, 0.05); padding: .15rem .45rem; border-radius: 4px;
      font-size: .75rem; color: var(--ui-accent, #06b6d4); font-weight: 600;
    }
    .color-tag {
      display: inline-flex; align-items: center; gap: .3rem;
      padding: .15rem .45rem; border-radius: 4px;
      border: 1px solid color-mix(in srgb, var(--c) 40%, transparent);
      background: color-mix(in srgb, var(--c) 12%, transparent);
      color: var(--c); font-size: .73rem; font-weight: 600; white-space: nowrap;
    }
    .color-tag .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--c); }

    .deck-desc {
      color: var(--ui-text-muted); font-size: .8rem; margin: 0 0 .6rem; line-height: 1.4;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }

    .deck-footer { display: flex; justify-content: space-between; align-items: center; gap: .5rem; font-size: .75rem; color: var(--ui-text-muted); margin-top: auto; padding-top: .4rem; }
    .deck-author { display: inline-flex; align-items: center; gap: .3rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .deck-visibility { display: inline-flex; align-items: center; gap: 0.3rem; color: var(--ui-text-muted); }
    .deck-visibility.public { color: #10b981; }
    .deck-date { color: var(--ui-text-muted); }

    .deck-actions { display: flex; gap: .4rem; margin-top: .6rem; padding-top: .6rem; border-top: 1px solid var(--ui-border); }
    .action-btn {
      display: inline-flex; align-items: center; justify-content: center;
      gap: .35rem; padding: .35rem .65rem; border-radius: 6px;
      font-size: .8rem; font-weight: 500; text-decoration: none;
      border: 1px solid var(--ui-border); cursor: pointer; background: rgba(255, 255, 255, 0.03);
      color: var(--ui-text-muted);
      transition: all .15s ease; font-family: inherit;
    }
    .action-edit { flex: 1; }
    .action-edit:hover { color: #fff; background: rgba(6, 182, 212, 0.12); border-color: var(--ui-accent, #06b6d4); }
    .action-copy { flex: 0 0 auto; width: 34px; }
    .action-copy:hover:not(:disabled) { color: #fff; background: rgba(56, 189, 248, 0.15); border-color: #38bdf8; }
    .action-delete { flex: 0 0 auto; width: 34px; }
    .action-delete:hover { color: #ef4444; background: rgba(239, 68, 68, 0.15); border-color: #ef4444; }

    /* Skeletons */
    .deck-card.skeleton { pointer-events: none; }
    .skeleton-block {
      height: 140px;
      background: linear-gradient(90deg, #18181b 0%, #27272a 50%, #18181b 100%);
      background-size: 200% 100%; animation: shimmer 1.4s linear infinite;
    }
    .skeleton-line {
      height: .7rem; margin: .6rem .95rem;
      background: linear-gradient(90deg, #18181b 0%, #27272a 50%, #18181b 100%);
      background-size: 200% 100%; border-radius: 4px;
      animation: shimmer 1.4s linear infinite;
    }
    .w-70 { width: 70%; } .w-40 { width: 40%; }
    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .empty { grid-column: 1/-1; text-align: center; color: var(--ui-text-muted); padding: 3rem 1rem; }
    .empty a { color: var(--ui-accent, #06b6d4); }
    .pagination { display: flex; justify-content: center; align-items: center; gap: 1rem; margin-top: 1.5rem; color: var(--ui-text-muted); font-size: .85rem; }
    .btn-page {
      display: inline-flex; align-items: center; gap: 0.35rem;
      padding: .4rem .8rem; background: var(--ui-surface); border: 1px solid var(--ui-border);
      border-radius: 6px; color: var(--ui-text-muted); cursor: pointer; font-family: inherit; font-size: 0.82rem;
      transition: all 0.15s ease;
    }
    .btn-page:hover:not(:disabled) { border-color: var(--ui-accent, #06b6d4); color: var(--ui-accent, #06b6d4); }
    .btn-page:disabled { opacity: .35; cursor: not-allowed; }
  `],
})
export class RiftboundDecksComponent implements OnInit {
  private rb = inject(RiftboundService);
  auth = inject(AuthService);

  decks = signal<RiftboundDeck[]>([]);
  loading = signal(true);
  page = signal(1);
  totalCount = signal(0);
  duplicatingId = signal<number | null>(null);
  activeTab = signal<Tab>('public');
  private coverAttempt = new Map<number, number>();
  private coverAttemptBump = signal(0);
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

  /** URL de portada, probando candidatos alternativos si la preferida no existe (404 en el CDN). */
  coverUrl(deck: RiftboundDeck): string {
    this.coverAttemptBump();
    const c = deck.cover_card_data;
    if (!c) return '';
    const candidates = Array.from(new Set([c.image, c.image_url, c.cdn_image_url, c.image_url_small].filter((u): u is string => !!u)));
    const attempt = this.coverAttempt.get(deck.id) ?? 0;
    return candidates[attempt] || '';
  }

  onCoverError(id: number) {
    this.coverAttempt.set(id, (this.coverAttempt.get(id) ?? 0) + 1);
    this.coverAttemptBump.update(n => n + 1);
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

  duplicateDeck(deck: RiftboundDeck) {
    if (this.duplicatingId() !== null) return;
    this.duplicatingId.set(deck.id);
    this.rb.getDeck(deck.id).subscribe({
      next: (full) => {
        const entries = (full.entries ?? []).map(e => ({
          card: e.card, quantity: e.quantity, zone: e.zone,
        })) as RiftboundDeck['entries'];
        const payload: Partial<RiftboundDeck> = {
          name: `${full.name} (copia)`,
          description: full.description,
          is_public: false,
          cover_card: full.cover_card,
          champion_unit: full.champion_unit,
          entries,
        };
        this.rb.createDeck(payload).subscribe({
          next: () => { this.duplicatingId.set(null); this.activeTab.set('mine'); this.page.set(1); this.reload(); },
          error: () => { this.duplicatingId.set(null); alert('No se pudo duplicar el mazo.'); },
        });
      },
      error: () => { this.duplicatingId.set(null); alert('No se pudo cargar el mazo para duplicar.'); },
    });
  }
}
