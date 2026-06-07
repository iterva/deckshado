import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundCard } from '../../../models/riftbound';
import { TcgPriceComponent } from '../../../components/tcg-price/tcg-price.component';

@Component({
  selector: 'app-riftbound-card-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, TcgPriceComponent],
  template: `
    @if (card(); as c) {
      <article class="rb-card-detail">
        <a routerLink="/riftbound/cards" class="back">← Volver al catálogo</a>
        <div class="layout">
          @if (c.image) {
            <div class="img-wrap" [class.battlefield]="c.card_type === 'battlefield'">
              <img [src]="c.image" [alt]="c.name" />
            </div>
          }
          <div class="info">
            <h1>{{ c.name }}</h1>
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
              <h2>Descripción</h2>
              <pre class="desc">{{ c.description }}</pre>
            }
            <app-tcg-price [cardName]="c.name" [compact]="false" [showLink]="true"></app-tcg-price>
          </div>
        </div>
      </article>
    } @else if (loading()) {
      <p>Cargando…</p>
    } @else {
      <p>Carta no encontrada.</p>
    }
  `,
  styles: [`
    .back { display: inline-block; margin-bottom: 1rem; opacity: .8; }
    .layout { display: grid; gap: 2rem; grid-template-columns: minmax(220px, 360px) 1fr; }
    .layout .img-wrap { width: 100%; }
    .layout .img-wrap img { width: 100%; border-radius: .75rem; display: block; }
    .layout .img-wrap.battlefield {
      position: relative;
      width: 100%;
      aspect-ratio: 5 / 7;
      overflow: hidden;
      border-radius: .75rem;
      background: #0f0f23;
    }
    .layout .img-wrap.battlefield img {
      position: absolute;
      top: 50%; left: 50%;
      width: 140%;
      height: auto;
      border-radius: 0;
      transform: translate(-50%, -50%) rotate(-90deg);
      transform-origin: center center;
    }
    .badges { display: flex; gap: .35rem; flex-wrap: wrap; margin: .75rem 0; }
    .badge { padding: .25rem .55rem; border-radius: .35rem; border: 1px solid var(--border-color, #444); font-size: .85rem; }
    .badge.color { background: #e9456020; }
    .stats { display: flex; gap: 1rem; margin: 1rem 0; }
    .stats div { display: flex; flex-direction: column; align-items: center; padding: .5rem 1rem; border: 1px solid var(--border-color, #444); border-radius: .5rem; }
    .stats span { opacity: .7; font-size: .85rem; }
    .stats strong { font-size: 1.5rem; }
    .desc { white-space: pre-wrap; font-family: inherit; line-height: 1.6; }
    .muted { opacity: .7; }
    @media (max-width: 720px) { .layout { grid-template-columns: 1fr; } }
  `],
})
export class RiftboundCardDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private rb = inject(RiftboundService);
  card = signal<RiftboundCard | null>(null);
  loading = signal(true);

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('cardNumber');
    if (!id) { this.loading.set(false); return; }
    this.rb.getCard(id).subscribe({
      next: (c) => { this.card.set(c); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }
}
