import { Component, OnInit, signal } from '@angular/core';

@Component({
  selector: 'app-ios-install-hint',
  standalone: true,
  template: `
    @if (visible()) {
      <div class="ios-hint-toast" role="dialog" aria-live="polite">
        <button class="close-btn" (click)="dismiss()" aria-label="Cerrar">
          <i class="bi bi-x-lg"></i>
        </button>
        <div class="hint-icon">
          <img src="icon-192.png" alt="ShadowForge" />
        </div>
        <div class="hint-body">
          <strong>Instalar ShadowForge</strong>
          <p>
            Toca <i class="bi bi-box-arrow-up share-icon"></i> y luego
            <strong>"Añadir a pantalla de inicio"</strong>
          </p>
        </div>
      </div>
    }
  `,
  styles: [`
    .ios-hint-toast {
      position: fixed;
      bottom: 16px;
      left: 16px;
      right: 16px;
      max-width: 420px;
      margin: 0 auto;
      background: linear-gradient(135deg, #1a1a3a 0%, #0f0f23 100%);
      color: #fff;
      border: 1px solid rgba(233, 69, 96, 0.4);
      border-radius: 14px;
      padding: 14px 40px 14px 14px;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
      display: flex;
      align-items: center;
      gap: 12px;
      z-index: 9999;
      animation: slideUp 0.35s ease-out;
    }
    @keyframes slideUp {
      from { transform: translateY(120%); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
    .hint-icon img {
      width: 48px;
      height: 48px;
      border-radius: 10px;
      display: block;
    }
    .hint-body { flex: 1; min-width: 0; }
    .hint-body strong { display: block; font-size: 0.95rem; margin-bottom: 2px; }
    .hint-body p { margin: 0; font-size: 0.82rem; opacity: 0.85; line-height: 1.3; }
    .share-icon { color: #4da6ff; vertical-align: -1px; }
    .close-btn {
      position: absolute;
      top: 6px;
      right: 6px;
      background: transparent;
      border: none;
      color: rgba(255, 255, 255, 0.6);
      width: 28px;
      height: 28px;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.85rem;
    }
    .close-btn:hover { color: #fff; background: rgba(255, 255, 255, 0.08); }
  `],
})
export class IosInstallHintComponent implements OnInit {
  private readonly STORAGE_KEY = 'ios-install-hint-dismissed';
  visible = signal(false);

  ngOnInit() {
    if (typeof window === 'undefined' || typeof navigator === 'undefined') return;
    if (localStorage.getItem(this.STORAGE_KEY)) return;

    const ua = navigator.userAgent || '';
    const isIOS = /iPad|iPhone|iPod/.test(ua) && !(window as any).MSStream;
    const isSafari = !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua);
    const isStandalone =
      (navigator as any).standalone === true ||
      window.matchMedia('(display-mode: standalone)').matches;

    if (isIOS && isSafari && !isStandalone) {
      setTimeout(() => this.visible.set(true), 3500);
    }
  }

  dismiss() {
    this.visible.set(false);
    try { localStorage.setItem(this.STORAGE_KEY, '1'); } catch {}
  }
}
