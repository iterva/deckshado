import { Component, OnInit, signal, ChangeDetectionStrategy } from '@angular/core';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

const DISMISSED_KEY = 'pwa_install_dismissed_at';
const DISMISS_COOLDOWN_DAYS = 14;

@Component({
  selector: 'app-pwa-install-hint',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (visible()) {
      <div class="pwa-install-toast" role="dialog" aria-live="polite" aria-labelledby="pwa-install-title">
        <button class="close-btn" (click)="dismiss()" aria-label="Cerrar aviso de instalación">
          <i class="bi bi-x-lg" aria-hidden="true"></i>
        </button>
        <div class="hint-icon" aria-hidden="true">
          <img src="icon-192.png" alt="" />
        </div>
        <div class="hint-body">
          <strong id="pwa-install-title">Instalar ShadowForge</strong>
          <p>Añádela a tu pantalla de inicio para acceso rápido y uso sin conexión.</p>
        </div>
        <button class="install-btn" (click)="install()">Instalar</button>
      </div>
    }
  `,
  styles: [`
    .pwa-install-toast {
      position: fixed;
      bottom: 84px;
      left: 16px;
      right: 16px;
      max-width: 420px;
      margin: 0 auto;
      background: linear-gradient(135deg, #1a1a2e 0%, #2a2a3e 100%);
      border: 1px solid rgba(233, 69, 96, 0.4);
      border-radius: 14px;
      box-shadow: 0 10px 32px rgba(0, 0, 0, 0.45);
      padding: 14px 16px 14px 14px;
      display: flex;
      align-items: center;
      gap: 12px;
      z-index: 9000;
      animation: slideUp .3s ease-out;
    }
    @keyframes slideUp { from { transform: translateY(20px); opacity: 0 } to { transform: translateY(0); opacity: 1 } }
    .close-btn {
      position: absolute; top: 6px; right: 6px;
      background: transparent; border: 0; color: #999; cursor: pointer;
      padding: 4px 6px; font-size: 14px;
    }
    .close-btn:hover { color: #fff; }
    .hint-icon img { width: 44px; height: 44px; border-radius: 10px; }
    .hint-body { flex: 1; min-width: 0; }
    .hint-body strong { display: block; color: #fff; font-size: 14px; margin-bottom: 2px; }
    .hint-body p { color: #bbb; font-size: 12px; margin: 0; line-height: 1.35; }
    .install-btn {
      background: linear-gradient(90deg, #e94560, #c73652);
      color: #fff; border: 0; border-radius: 8px;
      padding: 8px 14px; font-weight: 600; font-size: 13px;
      cursor: pointer; white-space: nowrap;
    }
    .install-btn:hover { filter: brightness(1.1); }
    body.light-theme .pwa-install-toast {
      background: #fff;
      border-color: #e94560;
    }
    body.light-theme .hint-body strong { color: #1a1a2e; }
    body.light-theme .hint-body p { color: #555; }
    body.light-theme .close-btn { color: #888; }
    body.light-theme .close-btn:hover { color: #000; }
  `],
})
export class PwaInstallHintComponent implements OnInit {
  visible = signal(false);
  private deferredPrompt: BeforeInstallPromptEvent | null = null;

  ngOnInit(): void {
    // Si ya está instalada (modo standalone) no mostrar.
    if (window.matchMedia('(display-mode: standalone)').matches) return;

    // Cooldown: si fue rechazada hace menos de N días no mostrar.
    const dismissedAt = Number(localStorage.getItem(DISMISSED_KEY) || 0);
    if (dismissedAt && Date.now() - dismissedAt < DISMISS_COOLDOWN_DAYS * 86400_000) return;

    window.addEventListener('beforeinstallprompt', (e: Event) => {
      e.preventDefault();
      this.deferredPrompt = e as BeforeInstallPromptEvent;
      this.visible.set(true);
    });

    window.addEventListener('appinstalled', () => {
      this.visible.set(false);
      this.deferredPrompt = null;
    });
  }

  async install(): Promise<void> {
    if (!this.deferredPrompt) {
      this.visible.set(false);
      return;
    }
    await this.deferredPrompt.prompt();
    const result = await this.deferredPrompt.userChoice;
    if (result.outcome === 'dismissed') {
      localStorage.setItem(DISMISSED_KEY, String(Date.now()));
    }
    this.visible.set(false);
    this.deferredPrompt = null;
  }

  dismiss(): void {
    localStorage.setItem(DISMISSED_KEY, String(Date.now()));
    this.visible.set(false);
  }
}
