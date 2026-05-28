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
            (click)="download()" [disabled]="busy() || !items?.length"
            [title]="!items?.length ? 'No hay cartas para incluir' : 'Descargar imagen'">
      📷 {{ busy() ? 'Generando...' : ctaLabel }}
    </button>
    @if (canCopy) {
      <button type="button" class="btn btn-sm" (click)="copy()" [disabled]="busy() || !items?.length"
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
            @if (it.image) {
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

    <div class="footer">
      <div class="brand">ShadowForge</div>
      <div class="tagline">{{ footerTagline }}</div>
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
      aspect-ratio: 0.715; /* proporción carta Riftbound/MYL */
      border-radius: 10px;
      overflow: hidden;
      background: #1a2040;
      box-shadow: 0 6px 16px rgba(0,0,0,0.5);
    }
    .img-wrap img {
      width: 100%; height: 100%; object-fit: cover; display: block;
    }
    .img-fallback {
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
  @Input() items: ShareImageItem[] = [];
  @Input() filenamePrefix = 'shadowforge';
  /** Etiqueta del botón principal (sobrescribe el por defecto). */
  @Input() ctaLabel = 'Descargar imagen';
  @Input() footerTagline = 'ShadowForge · TCG community';
  @Input() canCopy = true;

  @ViewChild('exportArea', { static: true }) exportArea!: ElementRef<HTMLElement>;

  readonly busy = signal(false);
  readonly toast = signal<string | null>(null);

  get headlineText(): string {
    const game = this.gameLabel ? ` ${this.gameLabel}` : '';
    if (this.mode === 'buying') {
      const sep = this.gameLabel ? ' · ' : '';
      return `En la mira${sep}${this.gameLabel ?? ''}`.trim();
    }
    return `Vendiendo${game}`;
  }

  get gridCols(): number {
    const n = this.items?.length || 0;
    if (n <= 3) return 3;
    if (n >= 15) return 5;
    return 4;
  }

  private async render(): Promise<HTMLCanvasElement | null> {
    if (!this.items?.length) return null;
    const el = this.exportArea?.nativeElement;
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
    const html2canvas = (await import('html2canvas')).default;
    return await html2canvas(el, {
      backgroundColor: '#0f1326',
      useCORS: true,
      allowTaint: false,
      scale: 2,
      width: 900,
      windowWidth: 900,
    });
  }

  async download() {
    if (this.busy()) return;
    this.busy.set(true);
    try {
      const canvas = await this.render();
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
      this.flashToast('Imagen descargada');
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
      const canvas = await this.render();
      if (!canvas) return;
      const blob: Blob | null = await new Promise(res => canvas.toBlob(b => res(b), 'image/png'));
      if (!blob) return;
      await navigator.clipboard.write([new w.ClipboardItem({ 'image/png': blob })]);
      this.flashToast('Imagen copiada');
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
