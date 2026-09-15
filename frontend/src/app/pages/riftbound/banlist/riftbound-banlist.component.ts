import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundBanlistEntry } from '../../../models/riftbound';
import { TcgPriceComponent } from '../../../components/tcg-price/tcg-price.component';

@Component({
  selector: 'app-riftbound-banlist',
  standalone: true,
  imports: [CommonModule, TcgPriceComponent],
  template: `
    <div class="rb-banlist-page">
      <header class="rb-page-head">
        <h1>Banlist Riftbound · Standard</h1>
        <p class="muted">
          Cartas prohibidas y limitadas en formato <strong>Standard Constructed</strong>.
          Vigente desde el 31 de marzo de 2026.
        </p>
      </header>

      @if (loading()) { <p class="center muted">Cargando…</p> }

      @if (!loading() && entries().length === 0) {
        <p class="center muted">Banlist vacía actualmente.</p>
      }

      @if (banned().length) {
        <section class="ban-section">
          <h2 class="ban-title">
            <span class="dot dot-banned"></span> Prohibidas
            <small>({{ banned().length }})</small>
          </h2>
          <div class="ban-grid">
            @for (e of banned(); track e.id) {
              <article class="ban-card">
                @if (cardImageUrl(e); as imgUrl) {
                  <img [src]="imgUrl" [alt]="e.card_name" loading="lazy" (error)="onCardImageError(e, $event)" />
                } @else {
                  <div class="img-fallback">{{ e.card_number }}</div>
                }
                <div class="ban-info">
                  <strong>{{ e.card_name }}</strong>
                  <small><code>{{ e.card_number }}</code></small>
                  <span class="ban-tag">PROHIBIDA</span>
                  <app-tcg-price [cardName]="e.card_name" [compact]="true"></app-tcg-price>
                </div>
              </article>
            }
          </div>
        </section>
      }

      @if (limited().length) {
        <section class="ban-section">
          <h2 class="ban-title">
            <span class="dot dot-limited"></span> Limitadas
            <small>({{ limited().length }})</small>
          </h2>
          <div class="ban-grid">
            @for (e of limited(); track e.id) {
              <article class="ban-card">
                @if (cardImageUrl(e); as imgUrl) {
                  <img [src]="imgUrl" [alt]="e.card_name" loading="lazy" (error)="onCardImageError(e, $event)" />
                } @else {
                  <div class="img-fallback">{{ e.card_number }}</div>
                }
                <div class="ban-info">
                  <strong>{{ e.card_name }}</strong>
                  <small><code>{{ e.card_number }}</code></small>
                  <span class="ban-tag tag-limited">{{ statusLabel(e.status) }}</span>
                  <app-tcg-price [cardName]="e.card_name" [compact]="true"></app-tcg-price>
                </div>
              </article>
            }
          </div>
        </section>
      }
    </div>
  `,
  styles: [`
    .rb-banlist-page { max-width: 1200px; margin: 0 auto; padding: 1.5rem 1rem; }
    @media (max-width: 600px) { .rb-banlist-page { padding: 1rem 0.65rem 2rem; } }
    .rb-page-head h1 {
      margin: 0; font-size: 1.7rem; font-weight: 700;
      background: linear-gradient(90deg, #e94560, #fff);
      -webkit-background-clip: text; background-clip: text; color: transparent;
    }
    .muted { opacity: .65; }
    .center { text-align: center; }

    .ban-section { margin: 1.75rem 0; }
    .ban-title {
      display: flex; align-items: center; gap: .5rem;
      font-size: 1.15rem; color: #fff; margin: 0 0 1rem;
      padding-bottom: .5rem; border-bottom: 1px solid #1e3a4a;
    }
    .ban-title small { color: #98a2a8; font-weight: 400; }
    .dot { width: 10px; height: 10px; border-radius: 50%; }
    .dot-banned { background: #e94560; box-shadow: 0 0 8px #e94560; }
    .dot-limited { background: #f0a830; box-shadow: 0 0 8px #f0a830; }

    .ban-grid {
      display: grid; gap: 1rem;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    }
    .ban-card {
      background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 10px;
      overflow: hidden; display: flex; flex-direction: column;
      transition: all .15s; position: relative;
    }
    .ban-card:hover { border-color: #e94560; transform: translateY(-2px); }
    .ban-card img { width: 100%; aspect-ratio: 63/88; object-fit: cover; background: #16213e; }
    .img-fallback {
      width: 100%; aspect-ratio: 63/88; background: #16213e;
      display: grid; place-items: center; color: #c8c8da;
    }
    .ban-info { padding: .65rem .75rem; display: flex; flex-direction: column; gap: .15rem; }
    .ban-info strong { color: #fff; font-size: .95rem; }
    .ban-info small { color: #98a2a8; font-size: .75rem; }
    .ban-info code { color: #e94560; font-family: 'Courier New', monospace; }

    .ban-tag {
      display: inline-block; align-self: flex-start; margin-top: .35rem;
      padding: .15rem .55rem; border-radius: 999px;
      background: #e94560; color: #fff; font-size: .65rem; font-weight: 700;
      letter-spacing: .05em; text-transform: uppercase;
    }
    .tag-limited { background: #f0a830; color: #1a1a2e; }

    :host-context(body.light-theme) .ban-card { background: #fbf6e9; border-color: #d4c489; }
    :host-context(body.light-theme) .ban-info strong { color: #463714; }
    :host-context(body.light-theme) .ban-title { color: #463714; }
  `],
})
export class RiftboundBanlistComponent implements OnInit {
  private rb = inject(RiftboundService);
  entries = signal<RiftboundBanlistEntry[]>([]);
  loading = signal(true);

  banned = computed(() => this.entries().filter(e => e.status === 'banned'));
  limited = computed(() => this.entries().filter(e => e.status !== 'banned'));

  private brokenUrlsByEntry = new Map<number, Set<string>>();
  private imageFallbackNonce = signal(0);

  ngOnInit() {
    this.rb.listBanlist('standard').subscribe({
      next: (r) => { this.entries.set(r.results); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  statusLabel(s: string) {
    return s === 'limited_1' ? 'Limitada a 1' : 'Limitada a 2';
  }

  private toHttps(url: string | null | undefined): string {
    const value = (url || '').trim();
    if (!value) return '';
    return value.startsWith('http://') ? `https://${value.slice(7)}` : value;
  }

  private imageUrlVariants(url: string | null | undefined): string[] {
    const raw = (url || '').trim();
    if (!raw) return [];
    const https = this.toHttps(raw);
    return raw === https ? [raw] : [raw, https];
  }

  private cloudinaryFetchVariants(url: string | null | undefined): string[] {
    const variants = this.imageUrlVariants(url);
    if (!variants.length) return [];
    return variants.map((candidate) =>
      `https://res.cloudinary.com/daobfx9yb/image/fetch/f_auto,q_auto/${encodeURIComponent(candidate)}`
    );
  }

  private candidateImageUrls(e: RiftboundBanlistEntry): string[] {
    const candidates = [
      ...this.imageUrlVariants(e.card_cdn_image_url),
      ...this.cloudinaryFetchVariants(e.card_image_url),
      ...this.cloudinaryFetchVariants(e.card_image_url_small),
      ...this.cloudinaryFetchVariants(e.card_image),
      ...this.imageUrlVariants(e.card_image_url),
      ...this.imageUrlVariants(e.card_image_url_small),
      ...this.imageUrlVariants(e.card_image),
    ].filter(Boolean);

    return Array.from(new Set(candidates));
  }

  cardImageUrl(e: RiftboundBanlistEntry): string {
    this.imageFallbackNonce();
    const broken = this.brokenUrlsByEntry.get(e.id);
    for (const url of this.candidateImageUrls(e)) {
      if (!broken?.has(url)) return url;
    }
    return '';
  }

  onCardImageError(e: RiftboundBanlistEntry, event: Event) {
    const img = event.target as HTMLImageElement | null;
    const failedUrls = [img?.currentSrc, img?.src]
      .map((url) => (url || '').trim())
      .filter(Boolean);
    if (!failedUrls.length) return;

    let broken = this.brokenUrlsByEntry.get(e.id);
    if (!broken) {
      broken = new Set<string>();
      this.brokenUrlsByEntry.set(e.id, broken);
    }

    let changed = false;
    for (const url of failedUrls) {
      if (!broken.has(url)) {
        broken.add(url);
        changed = true;
      }
    }
    if (changed) this.imageFallbackNonce.update((value) => value + 1);
  }
}
