import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundCardLite, RiftboundCollectionEntry } from '../../../models/riftbound';

@Component({
  selector: 'app-riftbound-carpeta',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <header class="rb-page-head">
      <h1>Mi carpeta de Riftbound</h1>
      <p class="muted">Lleva el inventario de tus cartas físicas.</p>
    </header>

    <div class="add-row">
      <input [(ngModel)]="search" (ngModelChange)="onSearch()" placeholder="Buscar carta para añadir…" />
      @if (results().length) {
        <ul class="results">
          @for (c of results(); track c.id) {
            <li>
              <span>{{ c.name }} <small>{{ c.card_number }}</small></span>
              <button (click)="add(c)">+ Añadir</button>
            </li>
          }
        </ul>
      }
    </div>

    <ul class="entries">
      @for (e of entries(); track e.id) {
        <li>
          <span>{{ e.card_data?.name }} <small>{{ e.card_data?.card_number }}</small></span>
          <span>×{{ e.quantity }}</span>
          <button (click)="remove(e)">✕</button>
        </li>
      }
      @if (!loading() && entries().length === 0) {
        <li class="muted">Sin entradas. Añade tus primeras cartas arriba.</li>
      }
    </ul>
  `,
  styles: [`
    .rb-page-head h1 { margin: 0; }
    .muted { opacity: .65; }
    .add-row input { width: 100%; padding: .5rem; border-radius: .35rem; border: 1px solid var(--border-color, #444); background: transparent; color: inherit; }
    .results { list-style: none; padding: 0; max-height: 220px; overflow: auto; border: 1px solid var(--border-color, #333); border-radius: .35rem; margin-top: .5rem; }
    .results li, .entries li { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: .5rem .75rem; }
    .results li:hover { background: #ffffff08; }
    .entries { list-style: none; padding: 0; margin-top: 1.5rem; }
    .entries li { border-bottom: 1px solid var(--border-color, #333); }
    button { background: transparent; color: inherit; border: 1px solid var(--border-color, #444); border-radius: .25rem; padding: .25rem .55rem; cursor: pointer; }
    small { opacity: .6; }
  `],
})
export class RiftboundCarpetaComponent implements OnInit {
  private rb = inject(RiftboundService);
  search = '';
  results = signal<RiftboundCardLite[]>([]);
  entries = signal<RiftboundCollectionEntry[]>([]);
  loading = signal(true);
  private timer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit() {
    this.rb.listCollection().subscribe({
      next: (r) => { this.entries.set(r.results); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  onSearch() {
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      if (!this.search.trim()) { this.results.set([]); return; }
      this.rb.listCards({ search: this.search, lite: true }).subscribe({
        next: (resp) => this.results.set(resp.results.slice(0, 8) as RiftboundCardLite[]),
      });
    }, 250);
  }

  add(c: RiftboundCardLite) {
    const existing = this.entries().find(e => e.card === c.id);
    const qty = (existing?.quantity || 0) + 1;
    this.rb.upsertCollection({
      card: c.id, quantity: qty, is_foil: false,
    }).subscribe({
      next: (entry) => {
        const list = this.entries().filter(e => e.id !== entry.id);
        this.entries.set([entry, ...list]);
        this.search = '';
        this.results.set([]);
      },
    });
  }

  remove(e: RiftboundCollectionEntry) {
    this.rb.deleteCollection(e.id).subscribe({
      next: () => this.entries.set(this.entries().filter(x => x.id !== e.id)),
    });
  }
}
