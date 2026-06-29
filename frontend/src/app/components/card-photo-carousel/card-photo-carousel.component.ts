import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  Input,
  OnChanges,
  SimpleChanges,
  computed,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';

/**
 * Mini carrusel que se ajusta al rectángulo de la carta. Muestra primero la
 * imagen oficial y luego las fotos reales subidas por el vendedor (máx 2).
 * Si solo hay una imagen, no muestra controles.
 *
 * Inputs:
 *   - cardImage: imagen oficial de la carta (siempre primera)
 *   - photos:   fotos reales subidas (máx 2). Valores falsy se filtran.
 *   - alt:      texto alt para accesibilidad
 *   - thumbWidth: ancho objetivo para la pipe `thumb` (por defecto 350)
 *
 * Output: emite click sólo cuando se hace tap sobre la imagen activa (para
 * abrir el modal de detalle del consumidor). Las flechas paran la propagación.
 */
@Component({
  selector: 'app-card-photo-carousel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, ThumbnailPipe],
  template: `
  <div class="cpc-root" [class.cpc-multi]="images().length > 1">
    @for (img of images(); track $index; let i = $index) {
      <img
        class="cpc-img"
        [class.active]="i === index()"
        [class.cpc-zoomable]="i > 0"
        [src]="img | thumb:thumbWidth"
        [alt]="alt"
        loading="lazy"
        (click)="onImageClick(i, img, $event)"
        (error)="onImgError($event, img, i)" />
    }

    @if (images().length === 0) {
      <div class="cpc-empty">Sin imagen</div>
    }

    @if (images().length > 1) {
      <button type="button" class="cpc-arrow cpc-prev" (click)="prev($event)"
              aria-label="Anterior">‹</button>
      <button type="button" class="cpc-arrow cpc-next" (click)="next($event)"
              aria-label="Siguiente">›</button>
      <div class="cpc-dots">
        @for (img of images(); track $index; let i = $index) {
          <span class="cpc-dot" [class.active]="i === index()"
                (click)="goTo(i, $event)"
                [attr.aria-label]="'Imagen ' + (i + 1)"></span>
        }
      </div>
      @if (index() > 0) {
        <span class="cpc-badge cpc-badge-real" (click)="openLightbox(images()[index()], $event)">
          🔍 Foto real
        </span>
      }
    }
  </div>

  @if (lightboxUrl()) {
    <div class="cpc-lightbox" (click)="closeLightbox($event)">
      <button type="button" class="cpc-lb-close" (click)="closeLightbox($event)" aria-label="Cerrar">✕</button>
      <img [src]="lightboxUrl()!" [alt]="alt" class="cpc-lb-img" (click)="$event.stopPropagation()" />
    </div>
  }
  `,
  styles: [`
    :host { display: block; width: 100%; height: 100%; }
    .cpc-root {
      position: relative; width: 100%; height: 100%;
      overflow: hidden;
    }
    .cpc-img {
      position: absolute; inset: 0;
      width: 100%; height: 100%;
      object-fit: cover;
      opacity: 0; transition: opacity .25s ease;
      display: block;
    }
    .cpc-img.active { opacity: 1; z-index: 1; }
    .cpc-empty {
      width: 100%; height: 100%;
      display: flex; align-items: center; justify-content: center;
      color: #888; font-size: .85rem;
    }
    .cpc-arrow {
      position: absolute; top: 50%; transform: translateY(-50%);
      width: 28px; height: 28px;
      background: rgba(0,0,0,.55); color: #fff;
      border: none; border-radius: 50%;
      font-size: 20px; line-height: 1; cursor: pointer;
      z-index: 3; display: flex; align-items: center; justify-content: center;
      padding: 0 0 2px 0;
      opacity: 0; transition: opacity .15s ease;
    }
    .cpc-prev { left: 6px; }
    .cpc-next { right: 6px; }
    .cpc-root:hover .cpc-arrow,
    .cpc-root:focus-within .cpc-arrow { opacity: 1; }
    .cpc-arrow:hover { background: rgba(0,0,0,.8); }
    /* En táctil mantenemos visibles para que se puedan tocar */
    @media (hover: none) {
      .cpc-arrow { opacity: .85; }
    }
    .cpc-dots {
      position: absolute; left: 0; right: 0; bottom: 6px;
      display: flex; justify-content: center; gap: 4px;
      z-index: 3; pointer-events: none;
    }
    .cpc-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: rgba(255,255,255,.45);
      box-shadow: 0 0 0 1px rgba(0,0,0,.5);
      pointer-events: auto; cursor: pointer;
      transition: background .15s ease, transform .15s ease;
    }
    .cpc-dot.active { background: #ffd75e; transform: scale(1.25); }
    .cpc-badge {
      position: absolute; left: 6px; top: 6px;
      background: rgba(0,0,0,.65); color: #fff;
      padding: 2px 8px; border-radius: 999px;
      font-size: 11px; font-weight: 700;
      z-index: 3; letter-spacing: .3px;
      cursor: zoom-in;
    }
    .cpc-badge:hover { background: rgba(0,0,0,.85); }
    .cpc-zoomable { cursor: zoom-in; }

    /* Lightbox */
    .cpc-lightbox {
      position: fixed; inset: 0;
      background: rgba(0,0,0,.92);
      display: flex; align-items: center; justify-content: center;
      z-index: 9999;
      padding: 1rem;
      animation: cpcFadeIn .15s ease;
    }
    @keyframes cpcFadeIn { from { opacity: 0; } to { opacity: 1; } }
    .cpc-lb-img {
      max-width: 95vw; max-height: 92vh;
      object-fit: contain;
      border-radius: 8px;
      box-shadow: 0 12px 60px rgba(0,0,0,.6);
      cursor: default;
    }
    .cpc-lb-close {
      position: absolute; top: 16px; right: 18px;
      width: 38px; height: 38px;
      background: rgba(255,255,255,.12); color: #fff;
      border: none; border-radius: 50%;
      font-size: 18px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: background .15s ease;
    }
    .cpc-lb-close:hover { background: rgba(255,255,255,.25); }
  `],
})
export class CardPhotoCarouselComponent implements OnChanges {
  @Input() cardImage: string | null | undefined = '';
  @Input({ required: false }) fallbackUrls: (string | null | undefined)[] = [];
  @Input({ required: false }) photos: (string | null | undefined)[] = [];
  @Input() alt = '';
  @Input() thumbWidth = 350;

  readonly index = signal(0);
  readonly images = computed<string[]>(() => this._images());
  readonly lightboxUrl = signal<string | null>(null);
  private readonly _images = signal<string[]>([]);
  private readonly _cardFallbacks = signal<string[]>([]);

  ngOnChanges(_: SimpleChanges) {
    const list: string[] = [];
    const normalizedCardImage = this.normalizeUrl(this.cardImage);
    if (normalizedCardImage) list.push(normalizedCardImage);

    const fallbackList: string[] = [];
    for (const url of this.fallbackUrls || []) {
      const normalizedFallback = this.normalizeUrl(url);
      if (!normalizedFallback) continue;
      if (normalizedFallback === normalizedCardImage) continue;
      fallbackList.push(normalizedFallback);
    }
    this._cardFallbacks.set(Array.from(new Set(fallbackList)));

    for (const p of this.photos || []) {
      const normalizedPhoto = this.normalizeUrl(p);
      if (normalizedPhoto) list.push(normalizedPhoto);
    }
    const uniqueList = Array.from(new Set(list));
    this._images.set(uniqueList);
    if (this.index() >= uniqueList.length) this.index.set(0);
  }

  prev(ev: Event) {
    ev.stopPropagation();
    const n = this.images().length;
    if (n < 2) return;
    this.index.update(i => (i - 1 + n) % n);
  }

  next(ev: Event) {
    ev.stopPropagation();
    const n = this.images().length;
    if (n < 2) return;
    this.index.update(i => (i + 1) % n);
  }

  goTo(i: number, ev: Event) {
    ev.stopPropagation();
    this.index.set(i);
  }

  /** Click sobre la imagen activa: si es foto real (i>0) abre el lightbox.
   *  Si es la imagen oficial (i===0) deja burbujear para que el padre maneje. */
  onImageClick(i: number, url: string, ev: Event) {
    if (i > 0) {
      ev.stopPropagation();
      this.openLightbox(url, ev);
    }
    // i===0: no stopPropagation → el padre abre su modal de detalle
  }

  openLightbox(url: string | null | undefined, ev?: Event) {
    if (ev) ev.stopPropagation();
    if (!url) return;
    this.lightboxUrl.set(url);
  }

  closeLightbox(ev?: Event) {
    if (ev) ev.stopPropagation();
    this.lightboxUrl.set(null);
  }

  @HostListener('document:keydown.escape')
  onEsc() {
    if (this.lightboxUrl()) this.closeLightbox();
  }

  /** Swipe básico para touch. */
  private touchStartX = 0;
  @HostListener('touchstart', ['$event'])
  onTouchStart(e: TouchEvent) {
    this.touchStartX = e.touches[0]?.clientX ?? 0;
  }
  @HostListener('touchend', ['$event'])
  onTouchEnd(e: TouchEvent) {
    const endX = e.changedTouches[0]?.clientX ?? 0;
    const dx = endX - this.touchStartX;
    if (Math.abs(dx) < 30) return;
    if (dx < 0) this.next(e);
    else this.prev(e);
  }

  onImgError(ev: Event, original: string | null | undefined, index: number) {
    const el = ev.target as HTMLImageElement;
    if (original && el && el.src !== original && !el.dataset['fallbackApplied']) {
      // fallback a URL original si la miniatura optimizada falla
      el.dataset['fallbackApplied'] = 'true';
      el.src = original;
      return;
    }

    if (index === 0 && el) {
      const fallbacks = this._cardFallbacks();
      const currentFallbackIndex = Number(el.dataset['cardFallbackIndex'] ?? -1);
      const nextFallbackIndex = currentFallbackIndex + 1;
      if (nextFallbackIndex < fallbacks.length) {
        el.dataset['cardFallbackIndex'] = String(nextFallbackIndex);
        el.src = fallbacks[nextFallbackIndex];
        return;
      }
    }

    this.removeBrokenImage(index);
  }

  private removeBrokenImage(index: number) {
    const current = this._images();
    if (index < 0 || index >= current.length) return;

    const next = current.filter((_, i) => i !== index);
    this._images.set(next);

    if (next.length === 0) {
      this.index.set(0);
      return;
    }

    const currentIndex = this.index();
    if (currentIndex > index) {
      this.index.set(currentIndex - 1);
      return;
    }
    if (currentIndex >= next.length) {
      this.index.set(next.length - 1);
    }
  }

  private normalizeUrl(url: string | null | undefined): string {
    if (!url || typeof url !== 'string') return '';
    return url.trim();
  }
}
