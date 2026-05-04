import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { RiftboundService } from '../../../services/riftbound.service';
import {
  RiftboundCard, RiftboundCardLite, RiftboundDeck, RiftboundDeckEntry,
  RiftboundZone, RIFTBOUND_ZONE_RULES, RIFTBOUND_ZONE_LABELS,
} from '../../../models/riftbound';

interface BuilderEntry {
  card: RiftboundCardLite;
  quantity: number;
  zone: RiftboundZone;
}

@Component({
  selector: 'app-riftbound-builder',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <header class="rb-page-head">
      <input class="rb-name" [(ngModel)]="deckName" placeholder="Nombre del mazo" />
      <div class="rb-zone-summary">
        @for (z of zones; track z) {
          <span [class.ok]="zoneCount(z) === rules[z]" [class.bad]="zoneCount(z) !== rules[z]">
            {{ labels[z] }}: {{ zoneCount(z) }} / {{ rules[z] }}
          </span>
        }
      </div>
      <div class="actions">
        <button class="rb-btn rb-btn-primary" (click)="save()" [disabled]="saving()">
          {{ saving() ? 'Guardando…' : (deckId() ? 'Guardar cambios' : 'Crear mazo') }}
        </button>
        @if (errors().length) {
          <ul class="errors">@for (e of errors(); track e) { <li>{{ e }}</li> }</ul>
        }
      </div>
    </header>

    <div class="rb-builder">
      <aside class="rb-search">
        <h3>Buscar cartas</h3>
        <input [(ngModel)]="search" (ngModelChange)="onSearch()" placeholder="Nombre o texto…" />
        <select [(ngModel)]="typeFilter" (ngModelChange)="reloadCards()">
          <option value="">Todos los tipos</option>
          <option value="unit">Unidad</option>
          <option value="spell">Hechizo</option>
          <option value="champion">Campeón</option>
          <option value="legend">Leyenda</option>
          <option value="gear">Gear</option>
          <option value="battlefield">Battleground</option>
          <option value="rune">Runa</option>
        </select>

        <div class="results">
          @for (c of results(); track c.id) {
            <button class="result" type="button" (click)="quickAdd(c)">
              @if (c.image) { <img [src]="c.image" [alt]="c.name" /> }
              <div>
                <strong>{{ c.name }}</strong>
                <small>{{ c.card_number }} · {{ c.card_type }}</small>
              </div>
            </button>
          }
        </div>
      </aside>

      <section class="rb-zones">
        @for (z of zones; track z) {
          <div class="zone">
            <h2>{{ labels[z] }} ({{ zoneCount(z) }}/{{ rules[z] }})</h2>
            @if (entries()[z].length === 0) {
              <p class="muted small">Vacío. Click en una carta para agregar.</p>
            }
            @for (e of entries()[z]; track e.card.id) {
              <div class="entry">
                <span class="qty">
                  <button (click)="dec(e)" type="button">−</button>
                  <strong>{{ e.quantity }}</strong>
                  <button (click)="inc(e)" type="button">+</button>
                </span>
                <span class="name">{{ e.card.name }} <small>{{ e.card.card_number }}</small></span>
                <button class="remove" (click)="remove(e)" type="button" aria-label="Quitar">✕</button>
              </div>
            }
          </div>
        }
      </section>
    </div>
  `,
  styles: [`
    .rb-page-head { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; padding: 1rem 0; }
    .rb-name { flex: 1; min-width: 220px; padding: .55rem .75rem; border-radius: .4rem; border: 1px solid var(--border-color, #444); background: transparent; color: inherit; font-size: 1.15rem; }
    .rb-zone-summary { display: flex; gap: .75rem; flex-wrap: wrap; }
    .rb-zone-summary span { padding: .35rem .65rem; border-radius: .35rem; border: 1px solid var(--border-color, #444); font-size: .85rem; }
    .rb-zone-summary .ok { border-color: #2ea043; background: #2ea04322; }
    .rb-zone-summary .bad { border-color: #c89b3c; background: #c89b3c11; }
    .rb-btn { padding: .55rem 1rem; border-radius: .4rem; border: 1px solid var(--border-color, #444); background: transparent; color: inherit; cursor: pointer; }
    .rb-btn-primary { background: #c89b3c; border-color: #c89b3c; color: #1a1a1a; font-weight: 600; }
    .errors { color: #ff6b6b; padding-left: 1.25rem; margin: .5rem 0; }

    .rb-builder { display: grid; grid-template-columns: 320px 1fr; gap: 1.5rem; align-items: start; }
    @media (max-width: 900px) { .rb-builder { grid-template-columns: 1fr; } }

    .rb-search { position: sticky; top: 1rem; }
    .rb-search input, .rb-search select { width: 100%; padding: .5rem; margin-bottom: .5rem; border-radius: .35rem; border: 1px solid var(--border-color, #444); background: transparent; color: inherit; }
    .results { max-height: 70vh; overflow-y: auto; display: flex; flex-direction: column; gap: .35rem; }
    .result { display: flex; gap: .5rem; align-items: center; padding: .35rem; border-radius: .35rem; border: 1px solid transparent; background: transparent; color: inherit; cursor: pointer; text-align: left; }
    .result:hover { border-color: var(--border-color, #555); background: #ffffff08; }
    .result img { width: 32px; height: 45px; object-fit: cover; border-radius: .25rem; }
    .result small { display: block; opacity: .65; font-size: .75rem; }

    .zone { padding: .75rem; border: 1px solid var(--border-color, #333); border-radius: .5rem; margin-bottom: 1rem; }
    .zone h2 { margin: 0 0 .5rem; font-size: 1rem; }
    .entry { display: flex; align-items: center; gap: .75rem; padding: .25rem .5rem; border-radius: .35rem; }
    .entry:hover { background: #ffffff08; }
    .qty { display: flex; align-items: center; gap: .35rem; }
    .qty button { width: 1.6rem; height: 1.6rem; border-radius: .25rem; border: 1px solid var(--border-color, #444); background: transparent; color: inherit; cursor: pointer; }
    .name { flex: 1; }
    .name small { opacity: .65; }
    .remove { background: transparent; border: none; color: #ff6b6b; cursor: pointer; }
    .small { font-size: .85rem; }
    .muted { opacity: .65; }
  `],
})
export class RiftboundBuilderComponent implements OnInit {
  private rb = inject(RiftboundService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  readonly zones: RiftboundZone[] = ['main', 'side', 'rune', 'champion', 'bg'];
  readonly rules = RIFTBOUND_ZONE_RULES;
  readonly labels = RIFTBOUND_ZONE_LABELS;

  deckId = signal<number | null>(null);
  deckName = 'Nuevo mazo Riftbound';
  description = '';
  saving = signal(false);
  errors = signal<string[]>([]);

  search = '';
  typeFilter = '';
  results = signal<RiftboundCardLite[]>([]);

  entries = signal<Record<RiftboundZone, BuilderEntry[]>>({
    main: [], side: [], rune: [], champion: [], bg: [],
  });

  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.deckId.set(+id);
      this.rb.getDeck(+id).subscribe({
        next: (deck) => this.loadFromDeck(deck),
      });
    }
    this.reloadCards();
  }

  loadFromDeck(deck: RiftboundDeck) {
    this.deckName = deck.name;
    this.description = deck.description;
    const map: Record<RiftboundZone, BuilderEntry[]> = {
      main: [], side: [], rune: [], champion: [], bg: [],
    };
    for (const e of deck.entries) {
      if (e.card_data) {
        map[e.zone].push({ card: e.card_data, quantity: e.quantity, zone: e.zone });
      }
    }
    this.entries.set(map);
  }

  onSearch() {
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.reloadCards(), 250);
  }

  reloadCards() {
    this.rb.listCards({
      search: this.search || undefined,
      type: this.typeFilter || undefined,
      lite: true,
    }).subscribe({
      next: (resp) => this.results.set(resp.results as RiftboundCardLite[]),
    });
  }

  zoneCount(z: RiftboundZone): number {
    return this.entries()[z].reduce((s, e) => s + e.quantity, 0);
  }

  /** Decide la zona destino por defecto según el tipo de la carta. */
  defaultZone(c: RiftboundCardLite): RiftboundZone {
    if (c.card_type === 'rune') return 'rune';
    if (c.card_type === 'champion') return 'champion';
    if (c.card_type === 'battlefield') return 'bg';
    return 'main';
  }

  quickAdd(c: RiftboundCardLite) {
    const zone = this.defaultZone(c);
    const list = [...this.entries()[zone]];
    const existing = list.find(e => e.card.id === c.id);
    if (existing) {
      if (zone === 'champion' || zone === 'bg' || zone === 'rune') {
        existing.quantity += 1;
      } else {
        existing.quantity = Math.min(3, existing.quantity + 1);
      }
    } else {
      list.push({ card: c, quantity: 1, zone });
    }
    this.entries.set({ ...this.entries(), [zone]: list });
  }

  inc(e: BuilderEntry) {
    if (e.zone === 'main' || e.zone === 'side') {
      if (e.quantity >= 3) return;
    }
    e.quantity += 1;
    this.entries.set({ ...this.entries() });
  }

  dec(e: BuilderEntry) {
    e.quantity = Math.max(0, e.quantity - 1);
    if (e.quantity === 0) this.remove(e);
    else this.entries.set({ ...this.entries() });
  }

  remove(e: BuilderEntry) {
    const list = this.entries()[e.zone].filter(x => x.card.id !== e.card.id);
    this.entries.set({ ...this.entries(), [e.zone]: list });
  }

  save() {
    this.saving.set(true);
    this.errors.set([]);
    const flatEntries: Partial<RiftboundDeckEntry>[] = [];
    for (const z of this.zones) {
      for (const e of this.entries()[z]) {
        flatEntries.push({ card: e.card.id, quantity: e.quantity, zone: z });
      }
    }
    const payload: Partial<RiftboundDeck> = {
      name: this.deckName,
      description: this.description,
      entries: flatEntries as RiftboundDeckEntry[],
    };
    const obs = this.deckId()
      ? this.rb.updateDeck(this.deckId()!, payload)
      : this.rb.createDeck(payload);
    obs.subscribe({
      next: (deck) => {
        this.saving.set(false);
        if (deck.validation && !deck.validation.valid) {
          this.errors.set(deck.validation.errors);
        }
        if (!this.deckId()) {
          this.deckId.set(deck.id);
          this.router.navigate(['/riftbound/builder', deck.id]);
        }
      },
      error: (err) => {
        this.saving.set(false);
        this.errors.set([err?.error?.detail || 'Error al guardar.']);
      },
    });
  }
}
