import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundCardLite, RiftboundColor } from '../../../models/riftbound';

const COLORS: { code: RiftboundColor; label: string; hex: string }[] = [
  { code: 'fury',  label: 'Fury',  hex: '#e94560' },
  { code: 'calm',  label: 'Calm',  hex: '#4caf50' },
  { code: 'mind',  label: 'Mind',  hex: '#3aa6ff' },
  { code: 'body',  label: 'Body',  hex: '#ff9a3c' },
  { code: 'chaos', label: 'Chaos', hex: '#9c5dff' },
  { code: 'order', label: 'Order', hex: '#ffd23c' },
];

const TYPES = [
  { code: 'unit', label: 'Unidad' },
  { code: 'spell', label: 'Hechizo' },
  { code: 'champion', label: 'Champion' },
  { code: 'legend', label: 'Legend' },
  { code: 'gear', label: 'Gear' },
  { code: 'battlefield', label: 'Battlefield' },
  { code: 'rune', label: 'Runa' },
];

const RARITIES = [
  { code: 'common', label: 'Common' },
  { code: 'uncommon', label: 'Uncommon' },
  { code: 'rare', label: 'Rare' },
  { code: 'epic', label: 'Epic' },
  { code: 'legendary', label: 'Legendary' },
  { code: 'champion', label: 'Champion' },
  { code: 'promo', label: 'Promo' },
];

@Component({
  selector: 'app-riftbound-cards',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="rb-cards-page">
      <header class="page-head">
        <h1>Cartas de Riftbound</h1>
        <p class="muted">{{ totalCount() }} cartas en la base de datos</p>
      </header>

      <div class="filters">
        <div class="search-row">
          <input type="search"
                 [(ngModel)]="searchQuery"
                 (ngModelChange)="onSearchInput()"
                 placeholder="Buscar por nombre, número o texto…" />
          <button class="search-btn" (click)="reload()" title="Buscar">🔍</button>
          @if (hasActiveFilter()) {
            <button class="clear-all" (click)="clearAll()" title="Limpiar filtros">Limpiar</button>
          }
        </div>

        <div class="type-chips">
          <button class="chip" [class.active]="!typeFilter" (click)="setType('')">Todos</button>
          @for (t of types; track t.code) {
            <button class="chip"
                    [class.active]="typeFilter === t.code"
                    (click)="setType(t.code)">{{ t.label }}</button>
          }
        </div>

        <div class="filter-row">
          <div class="filter-group">
            <label>Set</label>
            <select [(ngModel)]="setFilter" (ngModelChange)="reset()">
              <option value="">Todos los sets</option>
              @for (s of sets(); track s.code) {
                <option [value]="s.code">{{ s.code }} — {{ s.name }}</option>
              }
            </select>
          </div>

          <div class="filter-group">
            <label>Energía</label>
            <select [(ngModel)]="energyFilter" (ngModelChange)="reset()">
              <option [ngValue]="null">Cualquiera</option>
              @for (n of [0,1,2,3,4,5,6,7,8]; track n) {
                <option [ngValue]="n">{{ n }}</option>
              }
            </select>
          </div>

          <div class="filter-group">
            <label>Rareza</label>
            <select [(ngModel)]="rarityFilter" (ngModelChange)="reset()">
              <option value="">Todas</option>
              @for (r of rarities; track r.code) {
                <option [value]="r.code">{{ r.label }}</option>
              }
            </select>
          </div>
        </div>

        <div class="color-row">
          <span class="color-row-label">Dominios:</span>
          @for (c of colors; track c.code) {
            <button class="color-chip"
                    [class.active]="selectedColors().has(c.code)"
                    [style.--c]="c.hex"
                    (click)="toggleColor(c.code)">{{ c.label }}</button>
          }
        </div>
      </div>

      @if (loading()) {
        <p class="muted center">Cargando…</p>
      }

      <div class="card-grid">
        @for (card of cards(); track card.id) {
          <a class="rb-card" [routerLink]="['/riftbound/cards', card.card_number]">
            @if (card.image) {
              <img [src]="card.image" [alt]="card.name" loading="lazy" decoding="async" />
            } @else {
              <div class="rb-card-placeholder">{{ card.name }}</div>
            }
            <div class="rb-card-meta">
              <strong>{{ card.name }}</strong>
              <small>{{ card.card_number }}</small>
            </div>
          </a>
        }
      </div>

      @if (!loading() && cards().length === 0) {
        <p class="muted center empty">Sin resultados con los filtros actuales.</p>
      }

      @if (totalCount() > pageSize) {
        <nav class="pager">
          <button (click)="prev()" [disabled]="page() === 1">←</button>
          <span>Página {{ page() }} de {{ totalPages() }}</span>
          <button (click)="next()" [disabled]="page() >= totalPages()">→</button>
        </nav>
      }
    </div>
  `,
  styles: [`
    .rb-cards-page { max-width: 1400px; margin: 0 auto; padding: 1.5rem 1rem; }
    .page-head h1 { margin: 0; background: linear-gradient(90deg, #c89b3c, #f0e6d2); -webkit-background-clip: text; background-clip: text; color: transparent; }
    .muted { opacity: .65; }
    .center { text-align: center; }
    .empty { padding: 2rem 1rem; }

    .filters { display: flex; flex-direction: column; gap: .65rem; margin: 1rem 0 1.5rem; }
    .search-row { display: flex; gap: .5rem; }
    .search-row input {
      flex: 1; min-width: 0; padding: .55rem .85rem;
      border: 1px solid #2a3a4a; border-radius: 6px;
      background: #0a1428; color: #e0e0e0; outline: none;
    }
    .search-row input:focus { border-color: #c89b3c; }
    .search-btn {
      padding: .55rem .9rem; border: 1px solid #c89b3c; background: #c89b3c;
      color: #0a1428; border-radius: 6px; cursor: pointer; font-size: 1rem;
    }
    .clear-all {
      padding: .55rem .9rem; border: 1px solid #2a3a4a; background: transparent;
      color: #c8c8da; border-radius: 6px; cursor: pointer;
    }
    .clear-all:hover { border-color: #e94560; color: #e94560; }

    .type-chips { display: flex; flex-wrap: wrap; gap: .35rem; }
    .chip {
      padding: .3rem .8rem; border: 1px solid #2a3a4a; border-radius: 999px;
      background: #0a1428; color: #c8c8da; font-size: .85rem; cursor: pointer;
      transition: all .15s; white-space: nowrap;
    }
    .chip:hover { border-color: #c89b3c; color: #f0e6d2; }
    .chip.active { background: #c89b3c; border-color: #c89b3c; color: #0a1428; font-weight: 600; }

    .filter-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: .5rem; }
    @media (max-width: 600px) { .filter-row { grid-template-columns: 1fr 1fr; } }
    .filter-group label { display: block; font-size: .7rem; color: #98a2a8; margin-bottom: .15rem; text-transform: uppercase; letter-spacing: .05em; }
    .filter-group select {
      width: 100%; padding: .45rem .65rem;
      border: 1px solid #2a3a4a; border-radius: 6px;
      background: #0a1428; color: #e0e0e0; outline: none;
    }
    .filter-group select:focus { border-color: #c89b3c; }

    .color-row { display: flex; gap: .35rem; flex-wrap: wrap; align-items: center; }
    .color-row-label { color: #98a2a8; font-size: .85rem; margin-right: .35rem; }
    .color-chip {
      padding: .3rem .65rem; border: 1px solid var(--c); border-radius: 999px;
      background: transparent; color: var(--c); cursor: pointer; font-size: .8rem;
      font-weight: 600;
    }
    .color-chip.active { background: var(--c); color: #0a1428; }

    .card-grid {
      display: grid; gap: 1rem;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    }
    .rb-card {
      text-decoration: none; color: inherit; display: flex; flex-direction: column; gap: .35rem;
      transition: transform .15s;
    }
    .rb-card:hover { transform: translateY(-3px); }
    .rb-card img { width: 100%; aspect-ratio: 63/88; object-fit: cover; border-radius: .5rem; box-shadow: 0 2px 8px rgba(0,0,0,.3); }
    .rb-card-placeholder { aspect-ratio: 63/88; display: grid; place-items: center; padding: 1rem; text-align: center; background: #16213e; border-radius: .5rem; color: #c8c8da; }
    .rb-card-meta { display: flex; flex-direction: column; }
    .rb-card-meta strong { color: #f0e6d2; font-size: .9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .rb-card-meta small { opacity: .6; font-size: .75rem; }

    .pager { display: flex; gap: 1rem; align-items: center; justify-content: center; margin: 2rem 0; color: #98a2a8; }
    .pager button { padding: .45rem 1rem; border: 1px solid #2a3a4a; background: transparent; color: #c8c8da; border-radius: 6px; cursor: pointer; }
    .pager button:disabled { opacity: .35; cursor: not-allowed; }

    /* Light theme */
    :host-context(body.light-theme) .search-row input,
    :host-context(body.light-theme) .filter-group select,
    :host-context(body.light-theme) .chip { background: #ffffff; border-color: #d4c489; color: #2a1f10; }
    :host-context(body.light-theme) .chip.active { background: #785a28; border-color: #785a28; color: #f0e6d2; }
    :host-context(body.light-theme) .rb-card-meta strong { color: #463714; }
  `],
})
export class RiftboundCardsComponent implements OnInit {
  private rb = inject(RiftboundService);

  readonly colors = COLORS;
  readonly types = TYPES;
  readonly rarities = RARITIES;
  readonly pageSize = 30;

  searchQuery = '';
  typeFilter = '';
  setFilter = '';
  rarityFilter = '';
  energyFilter: number | null = null;
  selectedColors = signal(new Set<RiftboundColor>());

  cards = signal<RiftboundCardLite[]>([]);
  sets = signal<{ code: string; name: string }[]>([]);
  loading = signal(false);
  page = signal(1);
  totalCount = signal(0);
  totalPages = computed(() => Math.max(1, Math.ceil(this.totalCount() / this.pageSize)));

  hasActiveFilter = computed(() =>
    !!(this.searchQuery || this.typeFilter || this.setFilter ||
       this.rarityFilter || this.energyFilter !== null || this.selectedColors().size));

  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit() {
    this.rb.listSets().subscribe({
      next: (sets: any) => {
        const arr = Array.isArray(sets) ? sets : (sets?.results ?? []);
        this.sets.set(arr.map((s: any) => ({ code: s.code, name: s.name })));
      },
    });
    this.reload();
  }

  setType(t: string) { this.typeFilter = t; this.reset(); }

  toggleColor(c: RiftboundColor) {
    const set = new Set(this.selectedColors());
    if (set.has(c)) set.delete(c); else set.add(c);
    this.selectedColors.set(set);
    this.reset();
  }

  onSearchInput() {
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.reset(), 300);
  }

  clearAll() {
    this.searchQuery = '';
    this.typeFilter = '';
    this.setFilter = '';
    this.rarityFilter = '';
    this.energyFilter = null;
    this.selectedColors.set(new Set());
    this.reset();
  }

  reset() {
    this.page.set(1);
    this.reload();
  }

  reload() {
    this.loading.set(true);
    this.rb.listCards({
      search: this.searchQuery || undefined,
      type: this.typeFilter || undefined,
      set: this.setFilter || undefined,
      rarity: this.rarityFilter || undefined,
      energy: this.energyFilter ?? undefined,
      colors: [...this.selectedColors()],
      page: this.page(),
      lite: true,
    }).subscribe({
      next: (resp) => {
        this.cards.set(resp.results as RiftboundCardLite[]);
        this.totalCount.set(resp.count);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  prev() { if (this.page() > 1) { this.page.update(p => p - 1); this.reload(); } }
  next() { if (this.page() < this.totalPages()) { this.page.update(p => p + 1); this.reload(); } }
}
