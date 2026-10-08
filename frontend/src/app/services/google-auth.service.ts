import { Injectable } from '@angular/core';
import { environment } from '../../environments/environment';

declare const google: any;

interface CredentialResponse {
  credential: string;
}

/**
 * Helper para Google Identity Services (GSI).
 * Carga el SDK ya está incluido en index.html (script async).
 */
@Injectable({ providedIn: 'root' })
export class GoogleAuthService {
  private initialized = false;
  private callback: ((cred: string) => void) | null = null;

  /** Inyecta el script de GSI bajo demanda (no se carga en el index.html). */
  private loadSdk(): Promise<void> {
    if (typeof google !== 'undefined' && google.accounts?.id) return Promise.resolve();
    if (this._sdkPromise) return this._sdkPromise;
    this._sdkPromise = new Promise<void>((resolve, reject) => {
      const existing = document.querySelector<HTMLScriptElement>('script[data-gsi]');
      if (existing) {
        existing.addEventListener('load', () => resolve(), { once: true });
        existing.addEventListener('error', () => reject(new Error('GSI load error')), { once: true });
        return;
      }
      const s = document.createElement('script');
      s.src = 'https://accounts.google.com/gsi/client';
      s.async = true;
      s.defer = true;
      s.dataset['gsi'] = '1';
      s.onload = () => resolve();
      s.onerror = () => reject(new Error('GSI load error'));
      document.head.appendChild(s);
    });
    return this._sdkPromise;
  }
  private _sdkPromise: Promise<void> | null = null;

  /** Espera a que el SDK de Google esté disponible. */
  private waitForSdk(): Promise<void> {
    return this.loadSdk().then(() => new Promise((resolve, reject) => {
      if (typeof google !== 'undefined' && google.accounts?.id) {
        resolve();
        return;
      }
      let attempts = 0;
      const interval = setInterval(() => {
        attempts++;
        if (typeof google !== 'undefined' && google.accounts?.id) {
          clearInterval(interval);
          resolve();
        } else if (attempts > 50) {
          clearInterval(interval);
          reject(new Error('No se pudo cargar Google Identity Services'));
        }
      }, 100);
    }));
  }

  private init() {
    if (this.initialized) return;
    google.accounts.id.initialize({
      client_id: environment.googleClientId,
      callback: (resp: CredentialResponse) => {
        if (this.callback) this.callback(resp.credential);
      },
      auto_select: false,
      cancel_on_tap_outside: true,
    });
    this.initialized = true;
  }

  /**
   * Renderiza un botón "Sign in with Google" en el contenedor dado.
   * Llama a `onCredential` cuando el usuario completa el login.
   */
  async renderButton(container: HTMLElement, onCredential: (credential: string) => void): Promise<void> {
    await this.waitForSdk();
    this.init();
    this.callback = onCredential;
    // GSI requiere width en píxeles entre 200 y 400.
    // Calculamos el ancho del contenedor para evitar overflow horizontal en móviles.
    const measured = container.clientWidth || container.parentElement?.clientWidth || 0;
    const width = Math.max(220, Math.min(360, Math.floor(measured) || 320));
    const render = () => {
      google.accounts.id.renderButton(container, {
        theme: 'filled_black',
        size: 'large',
        type: 'standard',
        text: 'continue_with',
        shape: 'pill',
        logo_alignment: 'left',
        width,
      });
    };
    render();

    // Re-renderizar al rotar/redimensionar para mantener el ancho correcto.
    if (typeof ResizeObserver !== 'undefined') {
      let lastWidth = width;
      let timer: ReturnType<typeof setTimeout> | undefined;
      // Debounce: re-rendering on every resize step while GSI is still drawing left two buttons.
      const ro = new ResizeObserver(() => {
        clearTimeout(timer);
        timer = setTimeout(rerender, 200);
      });
      const rerender = () => {
        const m = container.clientWidth || container.parentElement?.clientWidth || 0;
        const w = Math.max(220, Math.min(360, Math.floor(m) || 320));
        if (w !== lastWidth) {
          lastWidth = w;
          container.innerHTML = '';
          google.accounts.id.renderButton(container, {
            theme: 'filled_black',
            size: 'large',
            type: 'standard',
            text: 'continue_with',
            shape: 'pill',
            logo_alignment: 'left',
            width: w,
          });
        }
      };
      ro.observe(container.parentElement || container);
    }
  }

  /** Abre el popup One Tap (opcional). */
  async prompt(onCredential: (credential: string) => void): Promise<void> {
    await this.waitForSdk();
    this.init();
    this.callback = onCredential;
    google.accounts.id.prompt();
  }

  /** Cierra cualquier sesión cacheada por GSI. */
  disableAutoSelect(): void {
    if (typeof google !== 'undefined' && google.accounts?.id) {
      google.accounts.id.disableAutoSelect();
    }
  }
}
