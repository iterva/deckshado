import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  Input,
  ViewChild,
  signal,
} from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';

export interface ShareImageItem {
  name: string;
  image: string;
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
  imports: [CommonModule, ThumbnailPipe, DecimalPipe],
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
            @if (includeCardImages && it.image) {
              <img [src]="it.image | thumb:400" [alt]="it.name" crossorigin="anonymous" />
            } @else {
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
export class ShareImageComponent {
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

  private renderCanvasFallback(): HTMLCanvasElement | null {
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

    const icon = this.mode === 'buying' ? 'Search' : 'Sell';
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

      this.drawRoundedRect(ctx, x + 1, y + 1, slotW - 2, imgH - 2, 9);
      ctx.strokeStyle = '#2a346e';
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.fillStyle = '#8ea0d0';
      ctx.font = '600 12px Segoe UI, Arial, sans-serif';
      const placeholder = this.ellipsize(ctx, it.name || 'Carta', slotW - 20);
      ctx.fillText(placeholder, x + 10, y + Math.floor(imgH / 2));

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
    await Promise.all(imgs.map(img =>
      img.complete ? Promise.resolve() :
      new Promise<void>(res => { img.addEventListener('load', () => res(), { once: true });
                                  img.addEventListener('error', () => res(), { once: true }); })
    ));

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
    // En modo sin imágenes remotas, evitar html2canvas por completo para no depender de parseo CSS.
    if (!this.includeCardImages) {
      return { canvas: this.renderCanvasFallback(), fallbackUsed: true };
    }

    try {
      const canvas = await this.render();
      return { canvas, fallbackUsed: false };
    } catch {
      try {
        const canvas = await this.render({ stripImages: true });
        return { canvas, fallbackUsed: true };
      } catch {
        return { canvas: this.renderCanvasFallback(), fallbackUsed: true };
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
