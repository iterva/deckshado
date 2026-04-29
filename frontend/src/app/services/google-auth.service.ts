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

  /** Espera a que el SDK de Google esté disponible. */
  private waitForSdk(): Promise<void> {
    return new Promise((resolve, reject) => {
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
    });
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
    google.accounts.id.renderButton(container, {
      theme: 'filled_black',
      size: 'large',
      type: 'standard',
      text: 'continue_with',
      shape: 'pill',
      logo_alignment: 'left',
      width: 320,
    });
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
