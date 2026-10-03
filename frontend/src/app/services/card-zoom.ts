import { computed, signal } from '@angular/core';

/** Mismo corte que el layout de los constructores (@media max-width: 960px). */
const MOBILE_QUERY = '(max-width: 960px)';

/**
 * Lupa del catálogo de los constructores (MYL y Riftbound): cartas por fila.
 * Cada nivel agranda ~1,25x. Escritorio: 9 → 4. Móvil: 10 → 1.
 * Cada modo recuerda su propio nivel; null = columnas automáticas del CSS.
 */
export class CardZoom {
  static readonly DESKTOP_LEVELS = [9, 7, 6, 5, 4];
  static readonly MOBILE_LEVELS = [10, 8, 6, 5, 4, 3, 2, 1];

  private readonly media = typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia(MOBILE_QUERY)
    : null;
  readonly isMobile = signal(this.media?.matches ?? false);

  private readonly desktop = signal<number | null>(this.load('desktop', CardZoom.DESKTOP_LEVELS));
  private readonly mobile = signal<number | null>(this.load('mobile', CardZoom.MOBILE_LEVELS));

  readonly levels = computed(() => (this.isMobile() ? CardZoom.MOBILE_LEVELS : CardZoom.DESKTOP_LEVELS));
  /** Columnas fijas elegidas para el modo actual, o null si es automático. */
  readonly columns = computed(() => (this.isMobile() ? this.mobile() : this.desktop()));
  readonly canZoomOut = computed(() => this.columns() !== this.levels()[0]);
  readonly canZoomIn = computed(() => this.columns() !== this.levels()[this.levels().length - 1]);

  private readonly onMediaChange = (e: MediaQueryListEvent) => this.isMobile.set(e.matches);

  constructor(private readonly storageKey: string) {
    this.media?.addEventListener('change', this.onMediaChange);
  }

  destroy() {
    this.media?.removeEventListener('change', this.onMediaChange);
  }

  /**
   * +1 agranda las cartas (menos por fila), -1 las achica (más por fila).
   * `autoColumns` = columnas que muestra hoy el grid en modo automático.
   */
  zoom(direction: 1 | -1, autoColumns: () => number) {
    const levels = this.levels(); // de más columnas a menos
    const fixed = this.columns();
    let next: number;
    if (fixed !== null && levels.includes(fixed)) {
      const index = levels.indexOf(fixed) + direction;
      next = levels[Math.min(Math.max(index, 0), levels.length - 1)];
    } else {
      // Desde automático: primer nivel en la dirección pedida.
      const current = autoColumns();
      next = direction === 1
        ? levels.find(cols => cols < current) ?? levels[levels.length - 1]
        : [...levels].reverse().find(cols => cols > current) ?? levels[0];
    }
    const mode = this.isMobile() ? 'mobile' : 'desktop';
    (mode === 'mobile' ? this.mobile : this.desktop).set(next);
    try { localStorage.setItem(`${this.storageKey}.${mode}`, String(next)); } catch {}
  }

  private load(mode: 'desktop' | 'mobile', levels: number[]): number | null {
    try {
      const saved = Number(localStorage.getItem(`${this.storageKey}.${mode}`));
      return levels.includes(saved) ? saved : null;
    } catch {
      return null;
    }
  }
}
