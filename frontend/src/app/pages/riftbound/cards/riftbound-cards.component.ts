import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundCard, RiftboundCardLite, RiftboundColor } from '../../../models/riftbound';

const COLORS: { code: RiftboundColor; label: string }[] = [
  { code: 'fury', label: 'Fury' },
  { code: 'calm', label: 'Calm' },
  { code: 'mind', label: 'Mind' },
  { code: 'body', label: 'Body' },
  { code: 'chaos', label: 'Chaos' },
  { code: 'order', label: 'Order' },
];

const TYPES = [
  { code: 'unit', label: 'Unidad' },
  { code: 'spell', label: 'Hechizo' },
  { code: 'champion', label: 'Campeón' },
  { code: 'legend', label: 'Leyenda' },
  { code: 'gear', label: 'Gear' },
  { code: 'battlefield', label: 'Battleground' },
  { code: 'rune', label: 'Runa' },
];

@Component({
  selector: 'app-riftbound-cards',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <header class="rb-page-head">
      <h1>Cartas de Riftbound</h1>
      <p class="muted">{{ totalCount() }} cartas en la base de datos</p>
    </header>

    <div class="rb-filters">
      <input
        type="search"
        [(ngModel)]="searchQuery"
        (ngModelChange)="onSearchChange()"
        placeholder="Buscar por nombre, número o texto..."
      />

      <select [(ngModel)]="typeFilter" (ngModelChange)="reload()">
        <option value="">Todos los tipos</option>
        @for (t of types; track t.code) {
          <option [value]="t.code">{{ t.label }}</option>
        }
      </select>

      <div class="rb-color-filters">
        @for (c of colors; track c.code) {
          <button
            type="button"
            [class.active]="selectedColors().has(c.code)"
            (click)="toggleColor(c.code)"
          >{{ c.label }}</button>
        }
      </div>
    </div>

    @if (loading()) {
      <p class="muted">Cargando…</p>
    }

    <div class="rb-grid">
      @for (card of cards(); track card.id) {
        <a class="rb-card" [routerLink]="['/riftbound/cards', card.card_number]">
          @if (card.image) {
            <img [src]="card.image" [alt]="card.name" loading="lazy" />
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
      <p class="muted center">Sin resultados.</p>
    }

    @if (totalCount() > pageSize) {
      <nav class="rb-pager">
        <button (click)="prev()" [disabled]="page() === 1">←</button>
        <span>Página {{ page() }} de {{ totalPages() }}</span>
        <button (click)="next()" [disabled]="page() >= totalPages()">→</button>
      </nav>
    }
  `,
  styles: [`
    .rb-page-head h1 { margin: 0 0 .25rem; }
    .muted { opacity: .7; }
    .center { text-align: center; }
    .rb-filters { display: flex; gap: .75rem; flex-wrap: wrap; align-items: center; margin: 1rem 0; }
    .rb-filters input, .rb-filters select { padding: .5rem .75rem; border-radius: .4rem; border: 1px solid var(--border-color, #444); background: var(--input-bg, #1a1a1a); color: inherit; }
    .rb-filters input { flex: 1; min-width: 220px; }
    .rb-color-filters { display: flex; gap: .35rem; flex-wrap: wrap; }
    .rb-color-filters button { padding: .35rem .65rem; border-radius: .35rem; border: 1px solid var(--border-color, #444); background: transparent; color: inherit; cursor: pointer; }
    .rb-color-filters button.active { background: #c89b3c; color: #1a1a1a; border-color: #c89b3c; }
    .rb-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); margin-top: 1rem; }
    .rb-card { text-decoration: none; color: inherit; display: flex; flex-direction: column; gap: .35rem; transition: transform .15s; }
    .rb-card:hover { transform: translateY(-3px); }
    .rb-card img { width: 100%; aspect-ratio: 63/88; object-fit: cover; border-radius: .5rem; box-shadow: 0 2px 8px rgba(0,0,0,.3); }
    .rb-card-placeholder { aspect-ratio: 63/88; display: grid; place-items: center; padding: 1rem; text-align: center; background: #2a2a2a; border-radius: .5rem; }
    .rb-card-meta { display: flex; flex-direction: column; }
    .rb-card-meta small { opacity: .6; }
    .rb-pager { display: flex; gap: 1rem; align-items: center; justify-content: center; margin: 2rem 0; }
    .rb-pager button { padding: .5rem 1rem; border: 1px solid var(--border-color, #444); background: transparent; color: inherit; border-radius: .35rem; cursor: pointer; }
    .rb-pager button:disabled { opacity: .4; cursor: not-allowed; }
  `],
})
export class RiftboundCardsComponent {
  private rb = inject(RiftboundService);

  readonly colors = COLORS;
  readonly types = TYPES;
  readonly pageSize = 24;

  searchQuery = '';
  typeFilter = '';
  selectedColors = signal(new Set<RiftboundColor>());
  cards = signal<RiftboundCardLite[]>([]);
  loading = signal(false);
  page = signal(1);
  totalCount = signal(0);
  totalPages = computed(() => Math.max(1, Math.ceil(this.totalCount() / this.pageSize)));

  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() { this.reload(); }

  toggleColor(c: RiftboundColor) {
    const set = new Set(this.selectedColors());
    if (set.has(c)) set.delete(c); else set.add(c);
    this.selectedColors.set(set);
    this.page.set(1);
    this.reload();
  }

  onSearchChange() {
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => { this.page.set(1); this.reload(); }, 300);
  }

  reload() {
    this.loading.set(true);
    this.rb.listCards({
      search: this.searchQuery || undefined,
      type: this.typeFilter || undefined,
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
