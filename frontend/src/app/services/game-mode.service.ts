import { Injectable, signal, computed, inject } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';

export type GameMode = 'myl' | 'riftbound';

/**
 * Mantiene el "modo de juego" actual (MyL ↔ Riftbound).
 *
 * - Persiste la preferencia en localStorage.
 * - Aplica la clase `mode-myl` / `mode-riftbound` al <body> para que el CSS
 *   pueda repintar la paleta sin tocar el routing.
 * - Detecta automáticamente el modo cuando el usuario entra a una ruta
 *   `/riftbound/*` (modo riftbound) o cualquier otra (modo myl) — sin
 *   forzar redirecciones.
 * - El método `toggle()` cambia de modo Y navega a la home del modo
 *   destino para que la sensación sea de "página dedicada".
 */
@Injectable({ providedIn: 'root' })
export class GameModeService {
  private readonly STORAGE_KEY = 'deckshado_game_mode';
  private router = inject(Router);

  mode = signal<GameMode>('myl');

  isRiftbound = computed(() => this.mode() === 'riftbound');
  isMyl = computed(() => this.mode() === 'myl');

  constructor() {
    const saved = localStorage.getItem(this.STORAGE_KEY) as GameMode | null;
    const initial: GameMode = saved === 'riftbound' ? 'riftbound' : 'myl';
    this.applyMode(initial);

    // Sincroniza con la URL:
    // - `/riftbound/*` → modo riftbound.
    // - Rutas exclusivas de MyL (`/cards`, `/decks`, `/builder`, `/carpeta`,
    //   `/wordle`, `/banlist`, `/tienda`, `/t`, `/wishlist`, `/w`, `/tiendas`,
    //   `/team`, `/`) → modo myl.
    // - Rutas neutrales compartidas (`/login`, `/register`, `/profile`,
    //   `/admin`) → no cambian el modo, así el usuario mantiene la
    //   experiencia visual del juego en el que estaba.
    this.router.events
      .pipe(filter((e) => e instanceof NavigationEnd))
      .subscribe((e) => {
        const url = (e as NavigationEnd).urlAfterRedirects || '';
        const next = this.detectModeFromUrl(url);
        if (next && next !== this.mode()) {
          this.applyMode(next);
        }
      });
  }

  /**
   * Devuelve el modo correspondiente a la URL, o `null` si la ruta es
   * neutral (no debe cambiar el modo actual).
   */
  private detectModeFromUrl(url: string): GameMode | null {
    if (url.startsWith('/riftbound')) return 'riftbound';

    // Rutas neutrales (cuenta de usuario, autenticación, panel admin).
    // No alteran el modo activo.
    const neutralPrefixes = ['/login', '/register', '/profile', '/admin'];
    if (neutralPrefixes.some((p) => url === p || url.startsWith(p + '/') || url.startsWith(p + '?'))) {
      return null;
    }

    return 'myl';
  }

  /** Cambia de modo y navega a la home correspondiente. */
  toggle(): void {
    const next: GameMode = this.mode() === 'myl' ? 'riftbound' : 'myl';
    this.applyMode(next);
    this.router.navigateByUrl(next === 'riftbound' ? '/riftbound' : '/');
  }

  /** Cambia el modo sin navegar (uso interno). */
  setMode(mode: GameMode): void {
    if (mode !== this.mode()) {
      this.applyMode(mode);
    }
  }

  private applyMode(mode: GameMode): void {
    this.mode.set(mode);
    localStorage.setItem(this.STORAGE_KEY, mode);
    document.body.classList.toggle('mode-riftbound', mode === 'riftbound');
    document.body.classList.toggle('mode-myl', mode === 'myl');
    // Riftbound todavía no tiene estilos de modo claro (QA #2 M3): se fuerza
    // oscuro mientras se está en ese modo y se restaura la preferencia al volver.
    const prefersLight = localStorage.getItem('deckshado_theme') === 'light';
    document.body.classList.toggle('light-theme', mode === 'myl' && prefersLight);
  }
}
