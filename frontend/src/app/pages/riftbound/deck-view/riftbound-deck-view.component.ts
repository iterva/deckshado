import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundDeck, RIFTBOUND_ZONE_LABELS, RiftboundZone } from '../../../models/riftbound';

@Component({
  selector: 'app-riftbound-deck-view',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    @if (deck(); as d) {
      <a routerLink="/riftbound/decks" class="back">← Volver</a>
      <h1>{{ d.name }}</h1>
      <p class="muted">por {{ d.owner_username }}</p>
      @if (d.description) { <p>{{ d.description }}</p> }
      @for (z of zones; track z) {
        <section>
          <h2>{{ labels[z] }} ({{ countZone(z) }})</h2>
          <ul>
            @for (e of entriesByZone(z); track e.card) {
              <li>{{ e.quantity }}× {{ e.card_data?.name }} <small>{{ e.card_data?.card_number }}</small></li>
            }
          </ul>
        </section>
      }
    } @else {
      <p>Cargando…</p>
    }
  `,
  styles: [`
    .back { opacity: .8; }
    .muted { opacity: .65; }
    section { margin: 1.5rem 0; }
    ul { list-style: none; padding: 0; }
    li { padding: .25rem 0; }
    li small { opacity: .55; }
  `],
})
export class RiftboundDeckViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private rb = inject(RiftboundService);
  deck = signal<RiftboundDeck | null>(null);
  readonly zones: RiftboundZone[] = ['champion', 'main', 'side', 'rune', 'bg'];
  readonly labels = RIFTBOUND_ZONE_LABELS;

  ngOnInit() {
    const id = +this.route.snapshot.paramMap.get('id')!;
    this.rb.getDeck(id).subscribe(d => this.deck.set(d));
  }

  entriesByZone(z: RiftboundZone) {
    return this.deck()?.entries.filter(e => e.zone === z) || [];
  }
  countZone(z: RiftboundZone) {
    return this.entriesByZone(z).reduce((s, e) => s + e.quantity, 0);
  }
}
