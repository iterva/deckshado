import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  Input,
  OnChanges,
  SimpleChanges,
  ViewChild,
  signal,
} from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';

export interface ShareImageItem {
  name: string;
  image: string;
  imageCandidates?: string[];
  quantity: number;
  foil?: boolean;
  price?: number | null;
}

/**
 * Genera una imagen "estilo CardIndex.cl" para compartir lo que el usuario
 * busca (wishlist) o vende (tienda). Renderiza el contenido en un área
 * fija fuera de pantalla y usa html2canvas (lazy) para capturarla como PNG.
 *
 * Uso:
 *   <app-share-image
 *     mode="buying"
 *     gameLabel="Riftbound"
 *     sellerName="@usuario"
 *     contactLine="¿Tienes alguna? Escríbeme · ShadowForge"
 *     [items]="items">
 *   </app-share-image>
 */
@Component({
  selector: 'app-share-image',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, DecimalPipe],
  template: `
  <div class="share-toolbar">
    <button type="button" class="btn btn-sm btn-primary"
            (click)="download()" [disabled]="busy() || !items.length"
            [title]="!items.length ? 'No hay cartas para incluir' : 'Descargar imagen'">
      📷 {{ busy() ? 'Generando...' : ctaLabel }}
    </button>
    @if (canCopy) {
      <button type="button" class="btn btn-sm" (click)="copy()" [disabled]="busy() || !items.length"
              title="Copiar imagen al portapapeles">
        📋 Copiar
      </button>
    }
    @if (toast()) { <span class="share-toast">{{ toast() }}</span> }
  </div>

  <!-- Área de exportación: fuera de pantalla pero con tamaño real. -->
  <div class="share-export" #exportArea aria-hidden="true">
    <div class="hero">
      <div class="title-row">
        <span class="emoji">{{ mode === 'buying' ? '🔎' : '🛒' }}</span>
        <h1>{{ headlineText }}</h1>
      </div>
      @if (contactLine) { <p class="subtitle">{{ contactLine }}</p> }
    </div>

    <div class="grid" [attr.data-cols]="gridCols">
      @for (it of items || []; track $index) {
        <div class="card">
          <div class="img-wrap">
            @if (includeCardImages && cardImageUrl(it, $index) && !isCardImageBroken($index)) {
              <img [src]="cardImageUrl(it, $index)"
                   [alt]="it.name"
                   crossorigin="anonymous"
                   [attr.data-share-index]="$index"
                   (error)="onCardImageError($index, it, $event)" />
            }
            @if (!includeCardImages || !cardImageUrl(it, $index) || isCardImageBroken($index)) {
              <div class="img-fallback">{{ it.name }}</div>
            }
            @if ((it.quantity || 1) > 1) {
              <span class="qty-badge">×{{ it.quantity }}</span>
            }
            @if (it.foil) { <div class="foil-ribbon">FOIL</div> }
          </div>
          <div class="card-name">{{ it.name }}</div>
          @if (mode === 'selling' && it.price != null) {
            <div class="price">\${{ it.price | number:'1.0-0':'es-CL' }}</div>
          }
        </div>
      }
    </div>
  </div>
  `,
  styles: [`
    :host { display: inline-flex; }
    .share-toolbar { display: inline-flex; gap: .5rem; align-items: center; flex-wrap: wrap; }
    .share-toast {
      font-size: .85rem; padding: .25rem .5rem; border-radius: 6px;
      background: #1e3a8a; color: #fff;
    }
    /* Off-screen render target: real size so html2canvas captures it accurately. */
    .share-export {
      position: fixed;
      top: 0;
      left: -100000px;
      width: 900px;
      box-sizing: border-box;
      padding: 36px 34px 28px;
      background: linear-gradient(180deg, #0f1326 0%, #131a36 100%);
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      pointer-events: none;
    }
    .hero { text-align: center; margin-bottom: 22px; }
    .title-row {
      display: flex; align-items: center; justify-content: center; gap: 14px;
    }
    .title-row .emoji { font-size: 38px; line-height: 1; }
    .title-row h1 {
      margin: 0; font-size: 36px; font-weight: 800; letter-spacing: -.5px; color: #fff;
    }
    .subtitle {
      margin: 8px 0 0; font-size: 15px; color: #a9b3d6; font-weight: 500;
    }
    .grid {
      display: grid; gap: 18px;
      grid-template-columns: repeat(4, 1fr);
    }
    .grid[data-cols='3'] { grid-template-columns: repeat(3, 1fr); }
    .grid[data-cols='5'] { grid-template-columns: repeat(5, 1fr); }
    .card {
      display: flex; flex-direction: column; align-items: stretch;
    }
    .img-wrap {
      position: relative;
      width: 100%;
      height: 0;
      padding-top: 139.86%; /* 1 / 0.715: fallback robusto para html2canvas */
      border-radius: 10px;
      overflow: hidden;
      background: #1a2040;
      box-shadow: 0 6px 16px rgba(0,0,0,0.5);
    }
    .img-wrap.no-export-image {
      background: linear-gradient(135deg, #1a2040 0%, #111733 100%);
      border: 1px solid #2a346e;
      box-shadow: none;
    }
    .img-wrap.no-export-image::after {
      content: 'Imagen no disponible';
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 10px;
      font-size: 12px;
      color: #8ea0d0;
      font-weight: 600;
      letter-spacing: .2px;
    }
    .img-wrap img {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .img-fallback {
      position: absolute;
      inset: 0;
      display: flex; align-items: center; justify-content: center;
      width: 100%; height: 100%; font-size: 12px; color: #8ea0d0; padding: 8px;
      text-align: center;
    }
    .qty-badge {
      position: absolute; top: 8px; right: 8px;
      background: #ff7a1a; color: #fff; font-weight: 800;
      border-radius: 999px; padding: 4px 10px;
      font-size: 14px;
      box-shadow: 0 2px 6px rgba(0,0,0,.4);
      line-height: 1;
    }
    .foil-ribbon {
      position: absolute; left: 0; right: 0; bottom: 0;
      background: linear-gradient(90deg, #f5b400 0%, #ffd75e 50%, #f5b400 100%);
      color: #20180a; font-weight: 900; font-size: 14px;
      letter-spacing: 2px; text-align: center; padding: 4px 0;
    }
    .card-name {
      margin-top: 8px; font-size: 13px; color: #d4dbf2;
      text-align: center; font-weight: 600;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    @media (max-width: 640px) {
      .card-name { font-size: 16px; }
    }
    .price {
      text-align: center; font-size: 14px; font-weight: 800; color: #fff;
      background: #1f2a52; border-radius: 999px; padding: 3px 0;
      margin-top: 4px;
    }
    .footer {
      margin-top: 26px; padding-top: 18px; border-top: 1px solid #2a346e;
      text-align: center;
    }
    .brand {
      font-size: 22px; font-weight: 800; color: #fff;
    }
    .tagline {
      margin-top: 4px; font-size: 13px; color: #99a3c9;
    }
  `],
})
export class ShareImageComponent implements OnChanges {
  @Input() mode: 'buying' | 'selling' = 'buying';
  @Input() gameLabel = '';
  @Input() sellerName = '';
  @Input() contactLine = '';
  /** Si se define, reemplaza completamente el título por defecto. */
  @Input() customHeadline = '';
  @Input() items: ShareImageItem[] = [];
  @Input() filenamePrefix = 'shadowforge';
  /** Etiqueta del botón principal (sobrescribe el por defecto). */
  @Input() ctaLabel = 'Descargar imagen';
  @Input() footerTagline = 'ShadowForge · TCG community';
  @Input() canCopy = true;
  /** Si es false, la imagen se genera sin cargar artes remotas (solo placeholders con nombre). */
  @Input() includeCardImages = true;

  @ViewChild('exportArea', { static: true }) exportArea!: ElementRef<HTMLElement>;

  readonly busy = signal(false);
  readonly toast = signal<string | null>(null);
  private readonly imageFallbackStepBySlot = new Map<number, number>();
  private readonly brokenImageSlots = new Set<number>();
  private readonly thumbnailPipe = new ThumbnailPipe();

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['items']) {
      this.imageFallbackStepBySlot.clear();
      this.brokenImageSlots.clear();
    }
  }

  get headlineText(): string {
    const custom = (this.customHeadline || '').trim();
    if (custom) return custom;
    const game = this.gameLabel ? ` ${this.gameLabel}` : '';
    if (this.mode === 'buying') {
      const sep = this.gameLabel ? ' · ' : '';
      return `En la mira${sep}${this.gameLabel ?? ''}`.trim();
    }
    return `Vendiendo${game}`;
  }

  get gridCols(): number {
    const n = this.items.length;
    if (n <= 3) return 3;
    if (n >= 15) return 5;
    return 4;
  }

  cardImageUrl(item: ShareImageItem, index: number): string {
    const candidates = this.displayImageCandidates(item);
    if (!candidates.length) return '';
    const step = this.currentImageStep(index, candidates);
    return candidates[step] || '';
  }

  isCardImageBroken(index: number): boolean {
    return this.brokenImageSlots.has(index);
  }

  onCardImageError(index: number, item: ShareImageItem, event: Event): void {
    const img = event.target as HTMLImageElement | null;
    if (this.advanceCardImageFallback(index, item, img)) {
      this.brokenImageSlots.delete(index);
      return;
    }
    this.brokenImageSlots.add(index);
    if (img) img.style.display = 'none';
  }

  private normalizeCandidateUrl(url: string | null | undefined): string {
    return (url || '').trim();
  }

  private rawImageCandidates(item: ShareImageItem): string[] {
    const raw = [item.image, ...(item.imageCandidates || [])]
      .map((url) => this.normalizeCandidateUrl(url))
      .filter(Boolean);
    return Array.from(new Set(raw));
  }

  private displayImageCandidates(item: ShareImageItem): string[] {
    const expanded: string[] = [];
    for (const raw of this.rawImageCandidates(item)) {
      // Hosts sin CORS (p. ej. blog.myl.cl) se ven en pantalla pero html2canvas los
      // dibuja vacíos: los pasamos primero por el proxy de Cloudinary, que sí envía CORS.
      const proxied = this.toCloudinaryFetchUrl(raw);
      if (proxied) expanded.push(proxied);
      const thumb = this.thumbnailPipe.transform(raw, 400);
      if (thumb) expanded.push(thumb);
      expanded.push(raw);
    }
    return Array.from(new Set(expanded.filter(Boolean)));
  }

  /** Proxy CORS de Cloudinary para URLs fuera de los CDN que ya envían CORS; null si no hace falta. */
  private toCloudinaryFetchUrl(url: string): string | null {
    const normalized = url.startsWith('//') ? `https:${url}` : url;
    const lower = normalized.toLowerCase();
    if (!lower.startsWith('http')) return null;
    if (lower.includes('localhost') || lower.includes('127.0.0.1')) return null;
    const corsSafeHosts = ['res.cloudinary.com/', 'ik.imagekit.io/', '.r2.dev/', '.r2.cloudflarestorage.com/'];
    if (corsSafeHosts.some((host) => lower.includes(host))) return null;
    return `https://res.cloudinary.com/daobfx9yb/image/fetch/w_600,c_limit/${encodeURIComponent(normalized)}`;
  }

  private currentImageStep(index: number, candidates: string[]): number {
    if (!candidates.length) return 0;
    const stored = this.imageFallbackStepBySlot.get(index) || 0;
    return Math.min(stored, candidates.length - 1);
  }

  private hasRemainingImageFallback(index: number, item: ShareImageItem): boolean {
    const candidates = this.displayImageCandidates(item);
    if (!candidates.length) return false;
    const step = this.currentImageStep(index, candidates);
    return step < candidates.length - 1;
  }

  private advanceCardImageFallback(index: number, item: ShareImageItem, img?: HTMLImageElement | null): boolean {
    const candidates = this.displayImageCandidates(item);
    if (!candidates.length) return false;

    const step = this.currentImageStep(index, candidates);
    if (step >= candidates.length - 1) return false;

    const nextStep = step + 1;
    this.imageFallbackStepBySlot.set(index, nextStep);
    if (img) img.src = candidates[nextStep];
    return true;
  }

  private waitForImageReady(img: HTMLImageElement, itemIndex: number): Promise<void> {
    return new Promise((resolve) => {
      if (!Number.isFinite(itemIndex) || itemIndex < 0 || itemIndex >= this.items.length) {
        resolve();
        return;
      }

      const item = this.items[itemIndex];
      const timeoutId = window.setTimeout(done, 6000);

      const onLoad = () => done();
      const onError = () => {
        if (!this.hasRemainingImageFallback(itemIndex, item)) {
          done();
        }
      };

      function done() {
        img.removeEventListener('load', onLoad);
        img.removeEventListener('error', onError);
        window.clearTimeout(timeoutId);
        resolve();
      }

      img.addEventListener('load', onLoad);
      img.addEventListener('error', onError);

      if (img.complete) {
        if (img.naturalWidth > 0) {
          done();
          return;
        }
        if (!this.hasRemainingImageFallback(itemIndex, item)) {
          done();
          return;
        }
        if (!this.advanceCardImageFallback(itemIndex, item, img)) {
          done();
        }
      }
    });
  }

  private drawRoundedRect(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    w: number,
    h: number,
    r: number,
  ) {
    const rr = Math.max(0, Math.min(r, Math.min(w, h) / 2));
    ctx.beginPath();
    ctx.moveTo(x + rr, y);
    ctx.arcTo(x + w, y, x + w, y + h, rr);
    ctx.arcTo(x + w, y + h, x, y + h, rr);
    ctx.arcTo(x, y + h, x, y, rr);
    ctx.arcTo(x, y, x + w, y, rr);
    ctx.closePath();
  }

  private ellipsize(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string {
    if (ctx.measureText(text).width <= maxWidth) return text;
    const suffix = '...';
    let lo = 0;
    let hi = text.length;
    while (lo < hi) {
      const mid = Math.ceil((lo + hi) / 2);
      const t = text.slice(0, mid) + suffix;
      if (ctx.measureText(t).width <= maxWidth) lo = mid;
      else hi = mid - 1;
    }
    return text.slice(0, lo) + suffix;
  }

  private loadImage(url: string): Promise<HTMLImageElement | null> {
    return new Promise((resolve) => {
      const clean = (url || '').trim();
      if (!clean) {
        resolve(null);
        return;
      }

      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.decoding = 'async';
      img.referrerPolicy = 'no-referrer';
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = clean;
    });
  }

  private async renderCanvasFallback(options: { includeImages?: boolean } = {}): Promise<HTMLCanvasElement | null> {
    if (!this.items.length) return null;

    const scale = 2;
    const width = 900;
    const paddingX = 34;
    const topPad = 36;
    const cols = this.gridCols;
    const gap = 18;
    const cardRatio = 1 / 0.715;
    const slotW = Math.floor((width - paddingX * 2 - gap * (cols - 1)) / cols);
    const imgH = Math.round(slotW * cardRatio);
    const metaH = this.mode === 'selling' ? 52 : 34;
    const rows = Math.ceil(this.items.length / cols);
    const headerH = this.contactLine ? 100 : 84;
    const gridH = rows * (imgH + metaH) + Math.max(0, rows - 1) * gap;
    const height = topPad + headerH + 22 + gridH + 28;

    const canvas = document.createElement('canvas');
    canvas.width = width * scale;
    canvas.height = height * scale;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.scale(scale, scale);

    const bg = ctx.createLinearGradient(0, 0, 0, height);
    bg.addColorStop(0, '#0f1326');
    bg.addColorStop(1, '#131a36');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, width, height);

    const includeImages = options.includeImages ?? this.includeCardImages;
    const itemCandidateUrls = includeImages
      ? this.items.map((it) => this.displayImageCandidates(it))
      : [];
    const uniqueUrls = includeImages
      ? Array.from(new Set(itemCandidateUrls.flat().filter(Boolean)))
      : [];

    const loadedImages = new Map<string, HTMLImageElement>();
    if (uniqueUrls.length) {
      const loaded = await Promise.all(uniqueUrls.map((url) => this.loadImage(url)));
      uniqueUrls.forEach((url, idx) => {
        const img = loaded[idx];
        if (img) loadedImages.set(url, img);
      });
    }

    const icon = this.mode === 'buying' ? '🔎' : '🛒';
    ctx.fillStyle = '#ffffff';
    ctx.font = '800 36px Segoe UI, Arial, sans-serif';
    const title = this.headlineText || (this.mode === 'buying' ? 'En la mira' : 'Vendiendo');
    ctx.fillText(`${icon} ${title}`, paddingX, topPad + 32);

    if (this.contactLine) {
      ctx.fillStyle = '#a9b3d6';
      ctx.font = '500 15px Segoe UI, Arial, sans-serif';
      ctx.fillText(this.ellipsize(ctx, this.contactLine, width - paddingX * 2), paddingX, topPad + 60);
    }

    const gridY = topPad + headerH;
    this.items.forEach((it, idx) => {
      const row = Math.floor(idx / cols);
      const col = idx % cols;
      const x = paddingX + col * (slotW + gap);
      const y = gridY + row * (imgH + metaH + gap);

      this.drawRoundedRect(ctx, x, y, slotW, imgH, 10);
      ctx.fillStyle = '#1a2040';
      ctx.fill();

      let loaded: HTMLImageElement | null = null;
      if (includeImages) {
        const candidates = itemCandidateUrls[idx] || [];
        const startStep = this.currentImageStep(idx, candidates);
        let resolvedStep = -1;

        for (let step = startStep; step < candidates.length; step++) {
          const candidate = candidates[step];
          const found = loadedImages.get(candidate);
          if (found) {
            loaded = found;
            resolvedStep = step;
            break;
          }
        }

        if (!loaded) {
          for (let step = 0; step < startStep; step++) {
            const candidate = candidates[step];
            const found = loadedImages.get(candidate);
            if (found) {
              loaded = found;
              resolvedStep = step;
              break;
            }
          }
        }

        if (resolvedStep >= 0 && resolvedStep !== startStep) {
          this.imageFallbackStepBySlot.set(idx, resolvedStep);
        }
      }

      if (loaded) {
          const ratio = loaded.width / loaded.height;
          const targetRatio = slotW / imgH;
          let drawW = slotW;
          let drawH = imgH;
          let dx = x;
          let dy = y;

          if (ratio > targetRatio) {
            drawW = Math.round(imgH * ratio);
            dx = x - Math.round((drawW - slotW) / 2);
          } else {
            drawH = Math.round(slotW / ratio);
            dy = y - Math.round((drawH - imgH) / 2);
          }

          ctx.save();
          this.drawRoundedRect(ctx, x, y, slotW, imgH, 10);
          ctx.clip();
          ctx.drawImage(loaded, dx, dy, drawW, drawH);
          ctx.restore();
      }

      this.drawRoundedRect(ctx, x + 1, y + 1, slotW - 2, imgH - 2, 9);
      ctx.strokeStyle = '#2a346e';
      ctx.lineWidth = 1;
      ctx.stroke();

      const hasRenderedImage = !!loaded;
      if (!hasRenderedImage) {
        ctx.fillStyle = '#8ea0d0';
        ctx.font = '600 12px Segoe UI, Arial, sans-serif';
        const placeholder = this.ellipsize(ctx, it.name || 'Carta', slotW - 20);
        ctx.fillText(placeholder, x + 10, y + Math.floor(imgH / 2));
      }

      if ((it.quantity || 1) > 1) {
        const qty = `x${it.quantity}`;
        ctx.font = '800 14px Segoe UI, Arial, sans-serif';
        const badgeW = Math.max(34, Math.ceil(ctx.measureText(qty).width + 16));
        const badgeH = 24;
        const bx = x + slotW - badgeW - 8;
        const by = y + 8;
        this.drawRoundedRect(ctx, bx, by, badgeW, badgeH, 999);
        ctx.fillStyle = '#ff7a1a';
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.fillText(qty, bx + 8, by + 16);
      }

      if (it.foil) {
        const fh = 22;
        const gy = y + imgH - fh;
        const foil = ctx.createLinearGradient(x, gy, x + slotW, gy);
        foil.addColorStop(0, '#f5b400');
        foil.addColorStop(0.5, '#ffd75e');
        foil.addColorStop(1, '#f5b400');
        ctx.fillStyle = foil;
        ctx.fillRect(x, gy, slotW, fh);
        ctx.fillStyle = '#20180a';
        ctx.font = '900 12px Segoe UI, Arial, sans-serif';
        ctx.fillText('FOIL', x + Math.max(8, Math.floor(slotW / 2) - 16), gy + 15);
      }

      ctx.fillStyle = '#d4dbf2';
      ctx.font = '600 13px Segoe UI, Arial, sans-serif';
      ctx.fillText(this.ellipsize(ctx, it.name || '', slotW), x, y + imgH + 18);

      if (this.mode === 'selling' && it.price != null) {
        const py = y + imgH + 25;
        this.drawRoundedRect(ctx, x, py, slotW, 21, 999);
        ctx.fillStyle = '#1f2a52';
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.font = '800 13px Segoe UI, Arial, sans-serif';
        const price = `$${Math.round(it.price).toLocaleString('es-CL')}`;
        ctx.fillText(this.ellipsize(ctx, price, slotW - 14), x + 8, py + 15);
      }
    });

    return canvas;
  }

  private sanitizeCloneStyles(root: HTMLElement): void {
    const nodes: HTMLElement[] = [
      root,
      ...Array.from(root.querySelectorAll<HTMLElement>('*')),
    ];
    const badColorFn = /\b(?:color|oklab|oklch|lab|lch)\(/i;
    const colorProps: Array<keyof CSSStyleDeclaration> = [
      'color',
      'backgroundColor',
      'borderColor',
      'borderTopColor',
      'borderRightColor',
      'borderBottomColor',
      'borderLeftColor',
      'outlineColor',
      'textDecorationColor',
      'caretColor',
      'columnRuleColor',
      'fill',
      'stroke',
    ];

    for (const node of nodes) {
      for (const prop of colorProps) {
        const raw = (node.style as any)[prop];
        if (typeof raw !== 'string' || !badColorFn.test(raw)) continue;
        if (prop === 'color' || prop === 'textDecorationColor' || prop === 'caretColor' || prop === 'fill' || prop === 'stroke') {
          (node.style as any)[prop] = '#d4dbf2';
        } else if (prop === 'backgroundColor') {
          (node.style as any)[prop] = 'transparent';
        } else {
          (node.style as any)[prop] = 'transparent';
        }
      }

      if (typeof node.style.boxShadow === 'string' && badColorFn.test(node.style.boxShadow)) {
        node.style.boxShadow = 'none';
      }
      if (typeof node.style.textShadow === 'string' && badColorFn.test(node.style.textShadow)) {
        node.style.textShadow = 'none';
      }
    }
  }

  private async render(options: { stripImages?: boolean } = {}): Promise<HTMLCanvasElement | null> {
    if (!this.items.length) return null;
    const el = this.exportArea.nativeElement;
    if (!el) return null;
    // Esperar a que el navegador haga layout de las imágenes
    await new Promise<void>(r => requestAnimationFrame(() => r()));
    // Esperar a que carguen las imágenes (evita capturar en blanco)
    const imgs = Array.from(el.querySelectorAll('img'));
    await Promise.all(imgs.map((img) => {
      const itemIndex = Number((img as HTMLImageElement).dataset['shareIndex']);
      return this.waitForImageReady(img as HTMLImageElement, itemIndex);
    }));

    // Fija un ancho de celda uniforme para cada carta antes de capturar.
    const grid = el.querySelector<HTMLElement>('.grid');
    if (grid) {
      const gridWidth = grid.getBoundingClientRect().width;
      const gap = parseFloat(getComputedStyle(grid).columnGap || getComputedStyle(grid).gap || '0') || 0;
      const cols = this.gridCols;
      const slotWidth = Math.max(1, Math.floor((gridWidth - gap * (cols - 1)) / cols));
      const cards = Array.from(grid.querySelectorAll<HTMLElement>('.card'));
      for (const card of cards) {
        card.style.width = `${slotWidth}px`;
        card.style.minWidth = `${slotWidth}px`;
        card.style.maxWidth = `${slotWidth}px`;
        card.style.justifySelf = 'stretch';
      }
    }

    // html2canvas puede renderizar distinto padding/aspect-ratio; fijamos alto en px
    // para que todas las cartas queden idénticas en la captura.
    const cardRatio = 1 / 0.715;
    const wraps = Array.from(el.querySelectorAll<HTMLElement>('.img-wrap'));
    for (const wrap of wraps) {
      const width = wrap.getBoundingClientRect().width;
      if (!width) continue;
      wrap.style.paddingTop = '0';
      wrap.style.height = `${Math.round(width * cardRatio)}px`;
    }

    // Reinicia estilos de una captura previa.
    for (const wrap of wraps) {
      wrap.style.backgroundImage = '';
      wrap.style.backgroundSize = '';
      wrap.style.backgroundPosition = '';
      wrap.style.backgroundRepeat = '';
      wrap.classList.remove('no-export-image');
    }
    for (const img of imgs) {
      (img as HTMLElement).style.visibility = '';
      (img as HTMLElement).style.display = '';
    }

    // Fallback robusto: durante la captura normal, usamos background-size: cover en el wrap.
    // Esto evita que html2canvas ignore object-fit en algunos navegadores.
    for (const img of imgs) {
      if (options.stripImages) break;
      const src = (img as HTMLImageElement).currentSrc || (img as HTMLImageElement).src;
      if (!src) continue;
      const wrap = (img as HTMLElement).closest('.img-wrap') as HTMLElement | null;
      if (!wrap) continue;
      wrap.style.backgroundImage = `url("${src}")`;
      wrap.style.backgroundSize = 'cover';
      wrap.style.backgroundPosition = 'center';
      wrap.style.backgroundRepeat = 'no-repeat';
      (img as HTMLElement).style.visibility = 'hidden';
    }

    const html2canvas = (await import('html2canvas')).default;
    const exportWindowWidth = window.matchMedia('(max-width: 640px)').matches ? 640 : 900;
    const exportId = `share-export-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    el.setAttribute('data-export-id', exportId);

    try {
      return await html2canvas(el, {
      backgroundColor: '#0f1326',
      useCORS: true,
      allowTaint: false,
      scale: 2,
      width: 900,
      windowWidth: exportWindowWidth,
      onclone: (doc) => {
        const root = doc.querySelector(`[data-export-id="${exportId}"]`) as HTMLElement | null;
        if (!root) return;
        this.sanitizeCloneStyles(root);
        if (!options.stripImages) return;
        root.querySelectorAll('.img-wrap img').forEach((img) => (img as HTMLElement).style.display = 'none');
        root.querySelectorAll('.img-wrap').forEach((wrap) => (wrap as HTMLElement).classList.add('no-export-image'));
      },
      });
    } finally {
      el.removeAttribute('data-export-id');
    }
  }

  private async renderWithFallback(): Promise<{ canvas: HTMLCanvasElement | null; fallbackUsed: boolean }> {
    this.imageFallbackStepBySlot.clear();
    this.brokenImageSlots.clear();

    // En modo sin imágenes remotas, evitar html2canvas por completo para no depender de parseo CSS.
    if (!this.includeCardImages) {
      return { canvas: await this.renderCanvasFallback({ includeImages: false }), fallbackUsed: true };
    }

    try {
      const canvas = await this.render();
      return { canvas, fallbackUsed: false };
    } catch {
      try {
        const canvas = await this.render({ stripImages: true });
        return { canvas, fallbackUsed: true };
      } catch {
        return { canvas: await this.renderCanvasFallback({ includeImages: true }), fallbackUsed: true };
      }
    }
  }

  async download() {
    if (this.busy()) return;
    this.busy.set(true);
    try {
      const { canvas, fallbackUsed } = await this.renderWithFallback();
      if (!canvas) return;
      const blob: Blob | null = await new Promise(res => canvas.toBlob(b => res(b), 'image/png'));
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const slug = (this.mode === 'buying' ? 'busco' : 'vendo') +
        (this.gameLabel ? '-' + this.gameLabel.toLowerCase().replace(/\s+/g, '-') : '');
      a.href = url;
      a.download = `${this.filenamePrefix}-${slug}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      this.flashToast(fallbackUsed ? 'Imagen descargada (sin algunas fotos)' : 'Imagen descargada');
    } catch (e) {
      console.error('share-image download error', e);
      this.flashToast('Error generando imagen');
    } finally {
      this.busy.set(false);
    }
  }

  async copy() {
    if (this.busy()) return;
    const w = window as any;
    if (!navigator.clipboard || !w.ClipboardItem) {
      this.flashToast('Tu navegador no soporta copiar imagen');
      return;
    }
    this.busy.set(true);
    try {
      const { canvas, fallbackUsed } = await this.renderWithFallback();
      if (!canvas) return;
      const blob: Blob | null = await new Promise(res => canvas.toBlob(b => res(b), 'image/png'));
      if (!blob) return;
      await navigator.clipboard.write([new w.ClipboardItem({ 'image/png': blob })]);
      this.flashToast(fallbackUsed ? 'Imagen copiada (sin algunas fotos)' : 'Imagen copiada');
    } catch (e) {
      console.error('share-image copy error', e);
      this.flashToast('Error al copiar');
    } finally {
      this.busy.set(false);
    }
  }

  private flashToast(msg: string) {
    this.toast.set(msg);
    setTimeout(() => this.toast.set(null), 2000);
  }
}
