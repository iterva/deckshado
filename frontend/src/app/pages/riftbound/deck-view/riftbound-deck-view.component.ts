import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { RiftboundService } from '../../../services/riftbound.service';
import { AuthService } from '../../../services/auth.service';
import {
  RiftboundDeck, RiftboundDeckEntry,
  RIFTBOUND_ZONE_LABELS, RiftboundZone, RiftboundColor, RiftboundCard,
} from '../../../models/riftbound';

const COLOR_HEX: Record<RiftboundColor, string> = {
  fury: '#e94560', calm: '#4caf50', mind: '#3aa6ff',
  body: '#ff9a3c', chaos: '#9c5dff', order: '#ffd23c', neutral: '#888',
};
const COLOR_LABEL: Record<RiftboundColor, string> = {
  fury: 'Fury', calm: 'Calm', mind: 'Mind',
  body: 'Body', chaos: 'Chaos', order: 'Order', neutral: 'Neutral',
};

@Component({
  selector: 'app-riftbound-deck-view',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    @if (loading()) {
      <p class="loading">Cargando mazo…</p>
    } @else if (deck(); as d) {
      <div class="container">
        <a routerLink="/riftbound/decks" class="back-link">← Volver a mazos</a>

        <!-- Hero -->
        <div class="deck-hero" [class.with-cover]="!!d.cover_card_data?.image">
          @if (d.cover_card_data?.image; as img) {
            <div class="hero-bg" [style.background-image]="'url(' + img + ')'"></div>
          }
          <div class="hero-overlay"></div>
          <div class="hero-content">
            @if (d.cover_card_data?.image; as img) {
              <img class="hero-cover" [src]="img" [alt]="d.cover_card_data?.name || ''" />
            } @else {
              <div class="hero-cover hero-cover-empty">⚔️</div>
            }
            <div class="hero-info">
              <h1 class="page-title">{{ d.name }}</h1>
              <div class="deck-chips">
                <span class="chip chip-owner">👤 {{ d.owner_username }}</span>
                @for (col of d.primary_colors; track col) {
                  <span class="chip chip-color" [style.--c]="hex(col)">
                    <span class="dot"></span>{{ label(col) }}
                  </span>
                }
                <span class="chip chip-cards">📚 {{ totalCards() }}</span>
                <span class="chip" [class.chip-public]="d.is_public" [class.chip-private]="!d.is_public">
                  {{ d.is_public ? '🌐 Público' : '🔒 Privado' }}
                </span>
                <span class="chip chip-time" [title]="d.updated_at">
                  🕒 {{ formatDate(d.updated_at) }}
                </span>
              </div>
              @if (d.description) {
                <p class="hero-description">{{ d.description }}</p>
              }
            </div>
          </div>
        </div>

        <!-- Action bar -->
        <div class="action-bar">
          <div class="action-spacer"></div>
          @if (isOwner()) {
            <button class="action-btn" (click)="toggleVisibility()" [disabled]="togglingVisibility()">
              {{ d.is_public ? '🔓 Hacer privado' : '🌐 Hacer público' }}
            </button>
            <button class="action-btn accent" (click)="editDeck()">✏️ Editar</button>
            <button class="action-btn danger" (click)="deleteDeck()">🗑 Eliminar</button>
          }
        </div>

        <!-- Secciones por zona -->
        @for (z of zones; track z) {
          @if (entriesByZone(z).length) {
            <section class="zone-section">
              <h2 class="zone-title">
                <span class="zone-name">{{ labels[z] }}</span>
                <span class="zone-count">{{ countZone(z) }}</span>
              </h2>
              <div class="card-grid">
                @for (e of entriesByZone(z); track e.id || e.card) {
                  <button type="button"
                          class="card-stack"
                          [class.qty-2]="e.quantity === 2"
                          [class.qty-3]="e.quantity >= 3"
                          (click)="openPreview(e)"
                          [title]="e.card_data?.name || ''">
                    @if (e.quantity >= 3 && e.card_data?.image) {
                      <img class="shadow s3" [src]="e.card_data?.image" aria-hidden="true" />
                    }
                    @if (e.quantity >= 2 && e.card_data?.image) {
                      <img class="shadow s2" [src]="e.card_data?.image" aria-hidden="true" />
                    }
                    @if (e.card_data?.image) {
                      <img class="top" [src]="e.card_data?.image" [alt]="e.card_data?.name || ''" />
                    } @else {
                      <div class="top placeholder">{{ e.card_data?.card_number }}</div>
                    }
                    @if (e.quantity > 1) {
                      <span class="qty-badge">×{{ e.quantity }}</span>
                    }
                    <span class="card-name">{{ e.card_data?.name }}</span>
                  </button>
                }
              </div>
            </section>
          }
        }

        @if (validationErrors().length) {
          <div class="errors-box">
            <strong>⚠ Mazo inválido:</strong>
            <ul>
              @for (err of validationErrors(); track err) { <li>{{ err }}</li> }
            </ul>
          </div>
        }
      </div>

      <!-- Modal preview -->
      @if (previewEntry(); as pe) {
        <div class="preview-overlay" (click)="closePreview()">
          <div class="preview-box" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
            <button class="preview-close" (click)="closePreview()" aria-label="Cerrar">✕</button>
            @if (previewLoading()) {
              <p class="muted" style="padding:3rem;text-align:center">Cargando…</p>
            } @else if (previewDetail(); as c) {
              <div class="preview-layout">
                @if (c.image) { <img class="preview-img" [src]="c.image" [alt]="c.name" /> }
                <div class="preview-info">
                  <h2>{{ c.name }}</h2>
                  <p class="muted">{{ c.card_number }} · {{ c.set?.name || c.set?.code || '—' }}</p>
                  <div class="preview-badges">
                    @if (c.card_type) { <span class="pv-badge">{{ c.card_type }}</span> }
                    @if (c.rarity) { <span class="pv-badge">{{ c.rarity }}</span> }
                    @for (col of c.colors; track col) { <span class="pv-badge color">{{ col }}</span> }
                    @for (st of c.subtypes; track st) { <span class="pv-badge">{{ st }}</span> }
                  </div>
                  <div class="preview-stats">
                    @if (c.energy != null) { <div><span>Energy</span><strong>{{ c.energy }}</strong></div> }
                    @if (c.power != null) { <div><span>Power</span><strong>{{ c.power }}</strong></div> }
                    @if (c.might != null) { <div><span>Might</span><strong>{{ c.might }}</strong></div> }
                  </div>
                  @if (c.description) {
                    <h3>Descripción</h3>
                    <pre class="preview-desc">{{ c.description }}</pre>
                  }
                </div>
              </div>
            } @else {
              @if (pe.card_data?.image) {
                <img class="preview-img" [src]="pe.card_data?.image" [alt]="pe.card_data?.name || ''" />
              }
              <h3>{{ pe.card_data?.name }} <small>{{ pe.card_data?.card_number }}</small></h3>
            }
          </div>
        </div>
      }
    } @else {
      <p class="loading">Mazo no encontrado.</p>
    }
  `,
  styles: [`
    .container { max-width: 1200px; margin: 0 auto; padding: 1.25rem 1rem 3rem; }
    .loading { color: #888; text-align: center; padding: 3rem; }
    .back-link { display: inline-block; opacity: .8; margin-bottom: 1rem; text-decoration: none; color: #c8c8da; }
    .back-link:hover { opacity: 1; color: #c89b3c; }
    .muted { opacity: .65; }

    /* Hero */
    .deck-hero {
      position: relative; border-radius: 14px; overflow: hidden;
      background: linear-gradient(135deg, #15152a 0%, #1a1a2e 100%);
      border: 1px solid #2a2a4a; min-height: 220px; margin-bottom: 1.25rem;
    }
    .hero-bg {
      position: absolute; inset: 0;
      background-size: cover; background-position: center 22%;
      filter: blur(28px) saturate(1.2); opacity: .55; transform: scale(1.15);
    }
    .hero-overlay {
      position: absolute; inset: 0;
      background: linear-gradient(180deg, rgba(10,20,40,.55) 0%, rgba(10,20,40,.92) 100%);
    }
    .hero-content {
      position: relative; z-index: 1; display: flex; gap: 1.25rem;
      padding: 1.25rem; align-items: stretch;
    }
    .hero-cover {
      width: 180px; height: 252px; object-fit: cover; object-position: center 25%;
      border-radius: 10px; border: 1px solid #c89b3c66; flex-shrink: 0;
      box-shadow: 0 10px 30px rgba(0,0,0,.5);
    }
    .hero-cover-empty {
      display: grid; place-items: center; background: #16213e;
      color: #2a2a4a; font-size: 3.2rem;
    }
    .hero-info { display: flex; flex-direction: column; min-width: 0; flex: 1; }
    .page-title {
      margin: 0 0 .65rem; font-size: 2rem; line-height: 1.15;
      background: linear-gradient(90deg, #c89b3c, #f0e6d2);
      -webkit-background-clip: text; background-clip: text; color: transparent;
      font-weight: 800;
    }
    .deck-chips { display: flex; flex-wrap: wrap; gap: .4rem; margin-bottom: .6rem; }
    .chip {
      display: inline-flex; align-items: center; gap: .3rem;
      padding: .25rem .65rem; border-radius: 999px;
      background: rgba(22,33,62,.7); border: 1px solid #2a3a4a;
      color: #e0e0e0; font-size: .8rem; backdrop-filter: blur(4px);
    }
    .chip-color {
      border-color: color-mix(in srgb, var(--c) 50%, transparent);
      background: color-mix(in srgb, var(--c) 14%, rgba(22,33,62,.7));
      color: var(--c); font-weight: 600;
    }
    .chip-color .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--c); }
    .chip-public { color: #4ade80; border-color: #4ade8055; }
    .chip-private { color: #888; }
    .chip-cards { color: #ffbd39; }
    .hero-description {
      color: #c8c8da; font-size: .92rem; line-height: 1.5; margin: .25rem 0 0;
      white-space: pre-wrap;
    }

    @media (max-width: 720px) {
      .hero-content { flex-direction: column; align-items: flex-start; }
      .hero-cover { width: 140px; height: 196px; }
      .page-title { font-size: 1.5rem; }
    }

    /* Action bar */
    .action-bar {
      display: flex; gap: .5rem; align-items: center;
      padding: .65rem .75rem; margin-bottom: 1.25rem;
      background: #15152a; border: 1px solid #2a2a4a; border-radius: 10px;
    }
    .action-spacer { flex: 1; }
    .action-btn {
      padding: .5rem .85rem; border-radius: 8px; cursor: pointer;
      background: #1a1a2e; border: 1px solid #2a3a4a; color: #e0e0e0;
      font-family: inherit; font-size: .88rem;
      display: inline-flex; align-items: center; gap: .35rem;
      transition: all .15s;
    }
    .action-btn:hover { border-color: #c89b3c; color: #fff; }
    .action-btn.accent {
      background: linear-gradient(135deg, #c89b3c 0%, #ffd23c 100%);
      color: #0a1428; border-color: transparent; font-weight: 700;
    }
    .action-btn.accent:hover { filter: brightness(1.1); color: #0a1428; }
    .action-btn.danger { color: #d97a7a; border-color: #4a2a2a; }
    .action-btn.danger:hover { background: rgba(220,53,69,.18); border-color: #dc3545; color: #fff; }

    /* Zona */
    .zone-section { margin-bottom: 1.75rem; }
    .zone-title {
      display: flex; align-items: center; gap: .65rem; margin: 0 0 .85rem;
      padding-bottom: .4rem; border-bottom: 1px solid #2a2a4a;
      color: #f0e6d2; font-size: 1.15rem;
    }
    .zone-name { font-weight: 700; }
    .zone-count {
      background: #16213e; color: #ffbd39; padding: .12rem .55rem;
      border-radius: 999px; font-size: .8rem; font-weight: 600;
    }

    /* Card grid (stacks) */
    .card-grid {
      display: grid; gap: 1.5rem 1.1rem;
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    }
    .card-stack {
      position: relative; aspect-ratio: 63/88; padding: 0;
      background: transparent; border: none; cursor: pointer;
      transition: transform .15s; outline: none;
    }
    .card-stack:hover { transform: translateY(-4px); }
    .card-stack:focus-visible { outline: 2px solid #c89b3c; outline-offset: 4px; border-radius: 6px; }
    .card-stack .top, .card-stack .shadow {
      position: absolute; inset: 0; width: 100%; height: 100%;
      object-fit: cover; border-radius: 6px;
      box-shadow: 0 4px 14px rgba(0,0,0,.4);
    }
    .card-stack .placeholder {
      display: grid; place-items: center;
      background: #16213e; color: #c8c8da; padding: 1rem; text-align: center;
    }
    .shadow.s2 { transform: translate(6px, 6px); filter: brightness(.6); z-index: 0; }
    .shadow.s3 { transform: translate(12px, 12px); filter: brightness(.4); z-index: -1; }
    .card-stack .top { z-index: 1; }
    .qty-badge {
      position: absolute; top: 6px; left: 6px; z-index: 3;
      background: linear-gradient(135deg, #c89b3c 0%, #ffd23c 100%);
      color: #0a1428; font-weight: 800; font-size: .82rem;
      padding: .15rem .5rem; border-radius: 999px;
      box-shadow: 0 2px 8px rgba(0,0,0,.5);
    }
    .card-name {
      position: absolute; left: 0; right: 0; bottom: -1.35rem;
      text-align: center; font-size: .75rem; color: #c8c8da;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .card-stack.qty-2, .card-stack.qty-3 { margin-right: 14px; margin-bottom: 14px; }

    /* Errors */
    .errors-box {
      margin: 1.25rem 0; padding: .85rem 1rem;
      background: rgba(233,69,96,.1); border: 1px solid #e9456066;
      border-radius: 8px; color: #ffb8c1;
    }
    .errors-box ul { margin: .35rem 0 0; padding-left: 1.25rem; }

    /* Modal */
    .preview-overlay {
      position: fixed; inset: 0; z-index: 1000;
      background: rgba(0,0,0,.78); display: grid; place-items: center;
      padding: 1rem; backdrop-filter: blur(3px);
    }
    .preview-box {
      position: relative; max-width: 1000px; width: 100%; max-height: 92vh; overflow: auto;
      background: #0a1428; border: 1px solid #c89b3c; border-radius: 12px;
      padding: 1.5rem; color: #e0e0e0; box-shadow: 0 20px 60px rgba(0,0,0,.5);
    }
    .preview-close {
      position: absolute; top: .6rem; right: .6rem;
      width: 36px; height: 36px; border-radius: 50%;
      background: #16213e; border: 1px solid #2a3a4a; color: #c8c8da;
      cursor: pointer; font-size: 1rem; display: grid; place-items: center;
      transition: all .15s; z-index: 2;
    }
    .preview-close:hover { background: #e94560; border-color: #e94560; color: #fff; }
    .preview-layout { display: grid; gap: 1.5rem; grid-template-columns: minmax(220px, 360px) 1fr; }
    .preview-img { width: 100%; border-radius: .75rem; align-self: start; }
    .preview-info h2 { margin: 0 0 .25rem; font-size: 1.6rem; color: #f0e6d2; }
    .preview-info h3 { margin: 1rem 0 .25rem; color: #f0e6d2; font-size: 1.05rem; }
    .preview-badges { display: flex; gap: .35rem; flex-wrap: wrap; margin: .75rem 0; }
    .pv-badge { padding: .25rem .55rem; border-radius: .35rem; border: 1px solid #2a3a4a; font-size: .8rem; background: #16213e; }
    .pv-badge.color { background: #c89b3c20; border-color: #c89b3c50; }
    .preview-stats { display: flex; gap: .65rem; margin: 1rem 0; flex-wrap: wrap; }
    .preview-stats > div { display: flex; flex-direction: column; align-items: center; padding: .5rem 1rem; border: 1px solid #2a3a4a; border-radius: .5rem; min-width: 70px; background: #16213e; }
    .preview-stats span { opacity: .7; font-size: .8rem; }
    .preview-stats strong { font-size: 1.4rem; color: #f0e6d2; }
    .preview-desc { white-space: pre-wrap; font-family: inherit; line-height: 1.55; margin: 0; font-size: .92rem; }
    @media (max-width: 720px) { .preview-layout { grid-template-columns: 1fr; } .preview-box { padding: 1rem; } }
  `],
})
export class RiftboundDeckViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private rb = inject(RiftboundService);
  private auth = inject(AuthService);

  deck = signal<RiftboundDeck | null>(null);
  loading = signal(true);
  togglingVisibility = signal(false);
  previewEntry = signal<RiftboundDeckEntry | null>(null);
  previewDetail = signal<RiftboundCard | null>(null);
  previewLoading = signal(false);

  readonly zones: RiftboundZone[] = ['champion', 'main', 'side', 'rune', 'bg'];
  readonly labels = RIFTBOUND_ZONE_LABELS;

  isOwner = computed(() => {
    const u = this.auth.user();
    const d = this.deck();
    return !!u && !!d && u.username === d.owner_username;
  });

  totalCards = computed(() =>
    (this.deck()?.entries ?? []).reduce((s, e) => s + e.quantity, 0));

  validationErrors = computed(() => this.deck()?.validation?.errors ?? []);

  hex(c: RiftboundColor): string { return COLOR_HEX[c] ?? '#888'; }
  label(c: RiftboundColor): string { return COLOR_LABEL[c] ?? c; }

  ngOnInit() {
    const id = +this.route.snapshot.paramMap.get('id')!;
    if (!id) { this.loading.set(false); return; }
    this.rb.getDeck(id).subscribe({
      next: (d) => { this.deck.set(d); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  entriesByZone(z: RiftboundZone): RiftboundDeckEntry[] {
    return this.deck()?.entries.filter(e => e.zone === z) ?? [];
  }

  countZone(z: RiftboundZone): number {
    return this.entriesByZone(z).reduce((s, e) => s + e.quantity, 0);
  }

  formatDate(s: string): string {
    if (!s) return '';
    const d = new Date(s);
    const diff = (Date.now() - +d) / 1000;
    if (diff < 60) return 'hace un momento';
    if (diff < 3600) return `hace ${Math.floor(diff/60)} min`;
    if (diff < 86400) return `hace ${Math.floor(diff/3600)} h`;
    if (diff < 86400 * 7) return `hace ${Math.floor(diff/86400)} d`;
    return d.toLocaleDateString('es-CL');
  }

  editDeck() {
    const d = this.deck();
    if (d) this.router.navigate(['/riftbound/builder', d.id]);
  }

  toggleVisibility() {
    const d = this.deck();
    if (!d || this.togglingVisibility()) return;
    this.togglingVisibility.set(true);
    this.rb.patchDeck(d.id, { is_public: !d.is_public }).subscribe({
      next: (updated) => { this.deck.set(updated); this.togglingVisibility.set(false); },
      error: () => this.togglingVisibility.set(false),
    });
  }

  deleteDeck() {
    const d = this.deck();
    if (!d) return;
    if (!confirm('¿Eliminar este mazo? Esta acción no se puede deshacer.')) return;
    this.rb.deleteDeck(d.id).subscribe({
      next: () => this.router.navigate(['/riftbound/decks']),
    });
  }

  openPreview(e: RiftboundDeckEntry) {
    this.previewEntry.set(e);
    this.previewDetail.set(null);
    const cn = e.card_data?.card_number;
    if (!cn) return;
    this.previewLoading.set(true);
    this.rb.getCard(cn).subscribe({
      next: (c) => { this.previewDetail.set(c); this.previewLoading.set(false); },
      error: () => this.previewLoading.set(false),
    });
  }

  closePreview() {
    this.previewEntry.set(null);
    this.previewDetail.set(null);
    this.previewLoading.set(false);
  }
}
