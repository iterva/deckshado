import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundDeck } from '../../../models/riftbound';

@Component({
  selector: 'app-riftbound-decks',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <header class="rb-page-head">
      <h1>Mazos Riftbound</h1>
      <a routerLink="/riftbound/builder" class="rb-btn rb-btn-primary">+ Nuevo mazo</a>
    </header>

    @if (loading()) { <p>Cargando…</p> }

    <ul class="rb-deck-list">
      @for (d of decks(); track d.id) {
        <li>
          <a [routerLink]="['/riftbound/decks', d.id]">
            <strong>{{ d.name }}</strong>
            <small>{{ d.owner_username }}</small>
          </a>
        </li>
      }
      @if (!loading() && decks().length === 0) {
        <li class="muted">Aún no hay mazos públicos.</li>
      }
    </ul>
  `,
  styles: [`
    .rb-page-head { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
    .rb-btn { padding: .5rem 1rem; border-radius: .4rem; text-decoration: none; }
    .rb-btn-primary { background: #c89b3c; color: #1a1a1a; font-weight: 600; }
    .rb-deck-list { list-style: none; padding: 0; display: grid; gap: .5rem; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
    .rb-deck-list a { display: flex; flex-direction: column; padding: 1rem; border: 1px solid var(--border-color, #333); border-radius: .5rem; text-decoration: none; color: inherit; }
    .rb-deck-list a:hover { background: #ffffff08; }
    .muted { opacity: .65; }
  `],
})
export class RiftboundDecksComponent implements OnInit {
  private rb = inject(RiftboundService);
  decks = signal<RiftboundDeck[]>([]);
  loading = signal(true);

  ngOnInit() {
    this.rb.listDecks().subscribe({
      next: (resp) => { this.decks.set(resp.results); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }
}
