import { Component, OnInit, computed, inject, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundCard, RiftboundCardLite } from '../../../models/riftbound';
import { TcgPriceComponent } from '../../../components/tcg-price/tcg-price.component';

const FALLBACK_COLORS: { code: string; label: string; hex: string }[] = [
  { code: 'fury',  label: 'Fury',  hex: '#e94560' },
  { code: 'calm',  label: 'Calm',  hex: '#4caf50' },
  { code: 'mind',  label: 'Mind',  hex: '#3aa6ff' },
  { code: 'body',  label: 'Body',  hex: '#ff9a3c' },
  { code: 'chaos', label: 'Chaos', hex: '#9c5dff' },
  { code: 'order', label: 'Order', hex: '#ff6b7d' },
];

const FALLBACK_TYPES = [
  { code: 'unit', label: 'Unidad' },
  { code: 'spell', label: 'Hechizo' },
  { code: 'champion', label: 'Champion' },
  { code: 'legend', label: 'Legend' },
  { code: 'gear', label: 'Gear' },
  { code: 'battlefield', label: 'Battlefield' },
  { code: 'rune', label: 'Runa' },
];

const FALLBACK_RARITIES = [
  { code: 'common', label: 'Common' },
  { code: 'uncommon', label: 'Uncommon' },
  { code: 'rare', label: 'Rare' },
  { code: 'epic', label: 'Epic' },
  { code: 'legendary', label: 'Legendary' },
  { code: 'champion', label: 'Champion' },
  { code: 'promo', label: 'Promo' },
];

const FALLBACK_ENERGY = [0, 1, 2, 3, 4, 5, 6, 7, 8];

@Component({
  selector: 'app-riftbound-cards',
  standalone: true,
  imports: [CommonModule, FormsModule, TcgPriceComponent],
  template: `
    <div class="rb-cards-page">
      <header class="page-head">
        <h1>Cartas de Riftbound</h1>
        <p class="muted">{{ totalCount() }} cartas en catalogo Riftcodex</p>
      </header>

      <div class="filters">
        <div class="search-row">
          <div class="search-modes" role="tablist" aria-label="Modo de búsqueda">
            <button type="button" role="tab"
                    [class.active]="searchMode === 'name'"
                    (click)="setMode('name')"
                    title="Buscar por nombre o número">Nombre</button>
            <button type="button" role="tab"
                    [class.active]="searchMode === 'ability'"
                    (click)="setMode('ability')"
                    title="Buscar dentro del texto de habilidad">Habilidad</button>
            <button type="button" role="tab"
                    [class.active]="searchMode === 'all'"
                    (click)="setMode('all')"
                    title="Buscar en nombre y habilidad">Todo</button>
          </div>
          <div class="search-input-row">
            <input type="search"
                   [(ngModel)]="searchQuery"
                   (ngModelChange)="onSearchInput()"
                   [placeholder]="searchMode === 'ability' ? 'Buscar habilidad…' : (searchMode === 'all' ? 'Buscar nombre o habilidad…' : 'Buscar nombre o número…')" />
            <button class="search-btn" (click)="reload(true)" title="Buscar">🔍</button>
            @if (hasActiveFilter()) {
              <button class="clear-all" (click)="clearAll()" title="Limpiar filtros">Limpiar</button>
            }
          </div>
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
              @for (n of energyOptions; track n) {
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

      @if (loading() && cards().length === 0) {
        <p class="muted center">Cargando…</p>
      }

      <div class="card-grid">
        @for (card of cards(); track card.id) {
          <button type="button" class="rb-card" (click)="openCard(card.card_number)">
            @if (card.image) {
              <img [src]="card.image" [alt]="card.name" loading="lazy" decoding="async" />
            } @else {
              <div class="rb-card-placeholder">{{ card.name }}</div>
            }
          </button>
        }
      </div>

      @if (modalOpen()) {
        <div class="rb-modal-overlay" (click)="closeCard()">
          <div class="rb-modal" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
            <button class="rb-modal-close" (click)="closeCard()" aria-label="Cerrar">✕</button>
            @if (modalLoading()) {
              <p class="muted center" style="padding:3rem">Cargando…</p>
            } @else if (selectedCard(); as c) {
              <div class="rb-modal-layout">
                @if (c.image) {
                  <img class="rb-modal-img" [src]="c.image" [alt]="c.name" />
                }
                <div class="rb-modal-info">
                  <h2>{{ c.name }}</h2>
                  <p class="muted">{{ c.card_number }} · {{ c.set?.name || c.set?.code || '—' }}</p>
                  <div class="badges">
                    @if (c.card_type) { <span class="badge">{{ c.card_type }}</span> }
                    @if (c.rarity) { <span class="badge">{{ c.rarity }}</span> }
                    @if (c.variant) { <span class="badge">{{ c.variant }}</span> }
                    @for (col of c.colors; track col) { <span class="badge color">{{ col }}</span> }
                    @for (st of c.subtypes; track st) { <span class="badge">{{ st }}</span> }
                  </div>
                  <div class="stats">
                    @if (c.energy != null) { <div><span>Energy</span><strong>{{ c.energy }}</strong></div> }
                    @if (c.power != null) { <div><span>Power</span><strong>{{ c.power }}</strong></div> }
                    @if (c.might != null) { <div><span>Might</span><strong>{{ c.might }}</strong></div> }
                  </div>
                  @if (c.description) {
                    <h3>Descripción</h3>
                    <pre class="desc">{{ c.description }}</pre>
                  }
                  <app-tcg-price [cardName]="c.name" [compact]="false" [showLink]="true"></app-tcg-price>
                </div>
              </div>
            } @else {
              <p class="muted center" style="padding:3rem">Carta no encontrada.</p>
            }
          </div>
        </div>
      }

      @if (!loading() && cards().length === 0) {
        <p class="muted center empty">Sin resultados con los filtros actuales.</p>
      }

      @if (totalCount() > pageSize) {
        <div class="infinite-sentinel" aria-hidden="true"></div>
        @if (loading() && cards().length > 0) {
          <p class="muted center" style="margin: 1rem 0;">Cargando más...</p>
        }
        @if (!hasMoreResults() && cards().length > 0) {
          <p class="muted center" style="margin: 1rem 0;">— Fin de resultados —</p>
        }
      }
    </div>
  `,
  styles: [`
    .rb-cards-page { max-width: 1400px; margin: 0 auto; padding: 1.5rem 1rem; }
    @media (max-width: 600px) { .rb-cards-page { padding: 1rem 0.65rem 2rem; } .page-head h1 { font-size: 1.3rem !important; } }
    .page-head h1 {
      margin: 0; font-size: 1.6rem; font-weight: 700;
      background: linear-gradient(90deg, #e94560, #fff);
      -webkit-background-clip: text; background-clip: text; color: transparent;
    }
    .muted { opacity: .65; }
    .center { text-align: center; }
    .empty { padding: 2rem 1rem; }

    .filters { display: flex; flex-direction: column; gap: .65rem; margin: 1rem 0 1.5rem; }
    .search-row { display: flex; flex-direction: column; gap: .5rem; align-items: stretch; }
    .search-input-row { display: flex; gap: .5rem; width: 100%; }
    .search-row input {
      flex: 1; min-width: 0; padding: .65rem 1rem;
      border: 1px solid #2a3a4a; border-radius: 6px;
      background: #0f0f23; color: #e0e0e0; outline: none;
      font-size: 1rem;
    }
    .search-row input:focus { border-color: #e94560; }
    .search-btn {
      padding: .55rem .9rem; border: 1px solid #e94560; background: #e94560;
      color: #fff; border-radius: 6px; cursor: pointer; font-size: 1rem;
      transition: background .15s;
    }
    .search-btn:hover { background: #c73650; }
    .search-btn:active { transform: scale(.95); }
    .clear-all {
      padding: .55rem .9rem; border: 1px solid #2a3a4a; background: transparent;
      color: #c8c8da; border-radius: 6px; cursor: pointer;
    }
    .clear-all:hover { border-color: #e94560; color: #e94560; }

    .type-chips { display: flex; flex-wrap: wrap; gap: .4rem; }
    .chip {
      padding: .3rem .8rem; border: 1px solid #2a3a4a; border-radius: 999px;
      background: #0f0f23; color: #c8c8da; font-size: .85rem; cursor: pointer;
      transition: all .15s; white-space: nowrap;
    }
    .chip:hover { border-color: #e94560; color: #fff; }
    .chip.active { background: #ffbd39; border-color: #ffbd39; color: #1a1a2e; font-weight: 700; }

    .filter-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: .5rem; }
    @media (max-width: 600px) { .filter-row { grid-template-columns: 1fr 1fr; } }
    .filter-group label { display: block; font-size: .7rem; color: #98a2a8; margin-bottom: .15rem; text-transform: uppercase; letter-spacing: .05em; }
    .filter-group select {
      width: 100%; padding: .45rem .65rem;
      border: 1px solid #2a3a4a; border-radius: 6px;
      background: #0f0f23; color: #e0e0e0; outline: none;
    }
    .filter-group select:focus { border-color: #e94560; }

    .color-row { display: flex; gap: .35rem; flex-wrap: wrap; align-items: center; }
    .color-row-label { color: #98a2a8; font-size: .85rem; margin-right: .35rem; }
    .color-chip {
      padding: .3rem .65rem; border: 1px solid var(--c); border-radius: 999px;
      background: transparent; color: var(--c); cursor: pointer; font-size: .8rem;
      font-weight: 600;
    }
    .color-chip.active { background: var(--c); color: #0f0f23; }

    .card-grid {
      display: grid; gap: 1rem;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    }
    @media (max-width: 600px) {
      .card-grid { grid-template-columns: repeat(auto-fit, minmax(78px, 1fr)); gap: 0.45rem; }
      .rb-card { gap: 0; }
      .rb-card img, .rb-card-placeholder { border-radius: .35rem; }
    }
    @media (max-width: 360px) { .card-grid { grid-template-columns: repeat(auto-fit, minmax(70px, 1fr)); gap: 0.35rem; } }
    .rb-card {
      text-decoration: none; color: inherit; display: flex; flex-direction: column;
      transition: transform .15s;
      background: transparent; border: none; padding: 0; cursor: pointer;
      font: inherit; text-align: left;
    }
    .rb-card:hover { transform: translateY(-3px); }
    .rb-card img { width: 100%; aspect-ratio: 63/88; object-fit: cover; border-radius: .5rem; box-shadow: 0 2px 8px rgba(0,0,0,.3); }
    .rb-card-placeholder { aspect-ratio: 63/88; display: grid; place-items: center; padding: 1rem; text-align: center; background: #16213e; border-radius: .5rem; color: #c8c8da; }

    .search-modes {
      display: flex; background: #16213e; border: 1px solid #2a2a4a;
      border-radius: 6px; padding: 2px; gap: 2px; align-self: flex-start;
    }
    .search-modes button {
      padding: .35rem .7rem; border: none; background: transparent;
      color: #b0b0c8; border-radius: 4px; font-size: .85rem; cursor: pointer;
      white-space: nowrap; transition: background .15s, color .15s;
    }
    .search-modes button:hover { color: #fff; }
    .search-modes button.active { background: #e94560; color: #fff; font-weight: 600; }

    .infinite-sentinel {
      width: 100%;
      height: 1px;
      margin-top: 1rem;
    }

    /* Modal */
    .rb-modal-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,.78);
      display: flex; align-items: center; justify-content: center;
      z-index: 1000; padding: 1rem; backdrop-filter: blur(3px);
      animation: fadeIn .15s ease-out;
    }
    @keyframes fadeIn { from { opacity: 0 } to { opacity: 1 } }
    .rb-modal {
      position: relative; max-width: 1000px; width: 100%; max-height: 92vh; overflow: auto;
      background: #0f0f23; border: 1px solid #2a3a4a; border-radius: 12px;
      padding: 1.5rem; color: #e0e0e0; box-shadow: 0 20px 60px rgba(0,0,0,.5);
    }
    .rb-modal-close {
      position: absolute; top: .6rem; right: .6rem;
      width: 36px; height: 36px; border-radius: 50%;
      background: #16213e; border: 1px solid #2a3a4a; color: #c8c8da;
      cursor: pointer; font-size: 1rem; display: grid; place-items: center;
      transition: all .15s; z-index: 2;
    }
    .rb-modal-close:hover { background: #e94560; border-color: #e94560; color: #fff; }
    .rb-modal-layout {
      display: grid; gap: 1.5rem; grid-template-columns: minmax(220px, 360px) 1fr;
    }
    .rb-modal-img { width: 100%; border-radius: .75rem; align-self: start; }
    .rb-modal-info h2 { margin: 0 0 .25rem; font-size: 1.6rem; color: #fff; }
    .rb-modal-info h3 { margin: 1rem 0 .25rem; color: #fff; font-size: 1.05rem; }
    .badges { display: flex; gap: .35rem; flex-wrap: wrap; margin: .75rem 0; }
    .badge { padding: .25rem .55rem; border-radius: .35rem; border: 1px solid #2a3a4a; font-size: .8rem; background: #16213e; }
    .badge.color { background: #e9456020; border-color: #e9456050; }
    .stats { display: flex; gap: .65rem; margin: 1rem 0; flex-wrap: wrap; }
    .stats > div { display: flex; flex-direction: column; align-items: center; padding: .5rem 1rem; border: 1px solid #2a3a4a; border-radius: .5rem; min-width: 70px; background: #16213e; }
    .stats span { opacity: .7; font-size: .8rem; }
    .stats strong { font-size: 1.4rem; color: #fff; }
    .desc { white-space: pre-wrap; font-family: inherit; line-height: 1.55; margin: 0; font-size: .92rem; }
    .rb-modal-info app-tcg-price {
      display: block;
      width: 100%;
      max-width: 100%;
      margin-top: .9rem;
      margin-left: 0;
    }
    @media (max-width: 720px) {
      .rb-modal-layout { grid-template-columns: 1fr; }
      .rb-modal { padding: 1rem; }
      .rb-modal-info h2 { font-size: 1.25rem !important; }
      .stats > div { padding: 0.35rem 0.7rem; min-width: 60px; }
      .stats strong { font-size: 1.1rem; }
      .rb-modal-info app-tcg-price { margin-left: 0; }
    }

    /* Light theme */
    :host-context(body.light-theme) .search-row input,
    :host-context(body.light-theme) .filter-group select,
    :host-context(body.light-theme) .chip { background: #ffffff; border-color: #d4c489; color: #2a1f10; }
    :host-context(body.light-theme) .chip.active { background: #785a28; border-color: #785a28; color: #fff; }
  `],
})
export class RiftboundCardsComponent implements OnInit {
  private rb = inject(RiftboundService);

  colors = [...FALLBACK_COLORS];
  types = [...FALLBACK_TYPES];
  rarities = [...FALLBACK_RARITIES];
  energyOptions = [...FALLBACK_ENERGY];
  // Debe coincidir con DRF PAGE_SIZE (backend/backend/settings.py).
  // Si no coincide, totalPages se calcula mal y quedan cartas inaccesibles.
  readonly pageSize = 20;

  searchQuery = '';
  searchMode: 'name' | 'ability' | 'all' = 'name';
  typeFilter = '';
  setFilter = '';
  rarityFilter = '';
  energyFilter: number | null = null;
  selectedColors = signal(new Set<string>());

  cards = signal<RiftboundCardLite[]>([]);
  sets = signal<{ code: string; name: string }[]>([]);
  loading = signal(false);
  modalOpen = signal(false);
  modalLoading = signal(false);
  selectedCard = signal<RiftboundCard | null>(null);
  page = signal(1);
  totalCount = signal(0);
  hasMoreResults = signal(false);
  totalPages = computed(() => Math.max(1, Math.ceil(this.totalCount() / this.pageSize)));

  hasActiveFilter = computed(() =>
    !!(this.searchQuery || this.typeFilter || this.setFilter ||
       this.rarityFilter || this.energyFilter !== null || this.selectedColors().size));

  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit() {
    this.loadDynamicIndexes();
    this.rb.listSets().subscribe({
      next: (sets: any) => {
        const arr = Array.isArray(sets) ? sets : (sets?.results ?? []);
        this.sets.set(arr.map((s: any) => ({ code: s.code, name: s.name })));
      },
    });
    this.reload();
  }

  setType(t: string) { this.typeFilter = t; this.reset(); }

  setMode(m: 'name' | 'ability' | 'all') {
    if (this.searchMode === m) return;
    this.searchMode = m;
    if (this.searchQuery) this.reset();
  }

  toggleColor(c: string) {
    const set = new Set(this.selectedColors());
    if (set.has(c)) set.delete(c); else set.add(c);
    this.selectedColors.set(set);
    this.reset();
  }

  private loadDynamicIndexes() {
    this.rb.getRiftcodexIndex('card-types').subscribe({
      next: (data) => { this.types = this.buildTypeOptions(data.values); },
    });

    this.rb.getRiftcodexIndex('rarities').subscribe({
      next: (data) => { this.rarities = this.buildRarityOptions(data.values); },
    });

    this.rb.getRiftcodexIndex('domains').subscribe({
      next: (data) => { this.colors = this.buildColorOptions(data.values); },
    });

    this.rb.getRiftcodexIndex('energy').subscribe({
      next: (data) => { this.energyOptions = this.buildEnergyOptions(data.values); },
    });
  }

  private buildTypeOptions(values: Array<string | number>): { code: string; label: string }[] {
    const map = new Map(FALLBACK_TYPES.map((x) => [x.code, x.label]));
    for (const raw of values) {
      const code = String(raw || '').trim().toLowerCase();
      if (!code) continue;
      if (!map.has(code)) map.set(code, this.toLabel(String(raw)));
    }
    return Array.from(map.entries()).map(([code, label]) => ({ code, label }));
  }

  private buildRarityOptions(values: Array<string | number>): { code: string; label: string }[] {
    const map = new Map(FALLBACK_RARITIES.map((x) => [x.code, x.label]));
    for (const raw of values) {
      const code = String(raw || '').trim().toLowerCase();
      if (!code) continue;
      if (!map.has(code)) map.set(code, this.toLabel(String(raw)));
    }
    return Array.from(map.entries()).map(([code, label]) => ({ code, label }));
  }

  private buildColorOptions(values: Array<string | number>): { code: string; label: string; hex: string }[] {
    const map = new Map(FALLBACK_COLORS.map((x) => [x.code, x]));
    for (const raw of values) {
      const code = String(raw || '').trim().toLowerCase();
      if (!code) continue;
      if (!map.has(code)) {
        map.set(code, { code, label: this.toLabel(String(raw)), hex: this.pickColorHex(code) });
      }
    }
    return Array.from(map.values());
  }

  private buildEnergyOptions(values: Array<string | number>): number[] {
    const energies = new Set<number>();
    for (const raw of values) {
      const n = Number(raw);
      if (Number.isFinite(n) && n >= 0) energies.add(n);
    }
    const list = Array.from(energies).sort((a, b) => a - b);
    return list.length ? list : [...FALLBACK_ENERGY];
  }

  private toLabel(raw: string): string {
    return raw
      .toLowerCase()
      .replace(/[-_]+/g, ' ')
      .replace(/\b\w/g, (x) => x.toUpperCase());
  }

  private pickColorHex(code: string): string {
    const known = FALLBACK_COLORS.find((x) => x.code === code)?.hex;
    if (known) return known;
    let hash = 0;
    for (let i = 0; i < code.length; i += 1) hash = ((hash << 5) - hash) + code.charCodeAt(i);
    const hue = Math.abs(hash) % 360;
    return `hsl(${hue} 72% 56%)`;
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
    this.reload(true);
  }

  reload(reset = true) {
    if (reset) {
      this.page.set(1);
      this.cards.set([]);
      this.hasMoreResults.set(false);
    }
    this.fetchCards(!reset);
  }

  private fetchCards(append = false) {
    this.loading.set(true);
    this.rb.listCards({
      search: this.searchQuery || undefined,
      searchMode: this.searchMode,
      hybrid: !!this.searchQuery && this.searchMode === 'all',
      type: this.typeFilter || undefined,
      set: this.setFilter || undefined,
      rarity: this.rarityFilter || undefined,
      energy: this.energyFilter ?? undefined,
      colors: [...this.selectedColors()],
      excludeBattlefields: this.selectedColors().size > 0 && this.typeFilter !== 'battlefield',
      page: this.page(),
      pageSize: this.pageSize,
      lite: true,
    }).subscribe({
      next: (resp) => {
        const next = resp.results as RiftboundCardLite[];
        if (append) {
          this.cards.update(curr => [...curr, ...next]);
        } else {
          this.cards.set(next);
        }
        this.totalCount.set(resp.count);
        this.hasMoreResults.set(!!resp.next);
        this.loading.set(false);
        queueMicrotask(() => this.tryLoadMoreByViewport());
      },
      error: () => this.loading.set(false),
    });
  }

  prev() { if (this.page() > 1) { this.page.update(p => p - 1); this.fetchCards(false); } }
  next() { if (this.page() < this.totalPages()) { this.page.update(p => p + 1); this.fetchCards(false); } }

  private loadMoreResults() {
    if (this.loading() || !this.hasMoreResults()) return;
    this.page.update(p => p + 1);
    this.fetchCards(true);
  }

  @HostListener('window:scroll')
  onWindowScroll() {
    this.tryLoadMoreByViewport();
  }

  @HostListener('window:resize')
  onWindowResize() {
    this.tryLoadMoreByViewport();
  }

  private tryLoadMoreByViewport() {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    if (this.loading() || !this.hasMoreResults()) return;

    const doc = document.documentElement;
    const body = document.body;
    const scrollTop = window.scrollY || doc.scrollTop || body.scrollTop || 0;
    const viewport = window.innerHeight || doc.clientHeight || 0;
    const fullHeight = Math.max(doc.scrollHeight || 0, body.scrollHeight || 0);
    const nearBottom = scrollTop + viewport >= fullHeight - 320;
    if (nearBottom) this.loadMoreResults();
  }

  openCard(cardNumber: string) {
    this.modalOpen.set(true);
    this.modalLoading.set(true);
    this.selectedCard.set(null);
    document.body.style.overflow = 'hidden';
    this.rb.getCard(cardNumber).subscribe({
      next: (c) => { this.selectedCard.set(c); this.modalLoading.set(false); },
      error: () => this.modalLoading.set(false),
    });
  }

  closeCard() {
    this.modalOpen.set(false);
    this.selectedCard.set(null);
    document.body.style.overflow = '';
  }

  @HostListener('document:keydown.escape')
  onEsc() { if (this.modalOpen()) this.closeCard(); }
}
