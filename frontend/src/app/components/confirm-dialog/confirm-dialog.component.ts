import { Component, ElementRef, HostListener, effect, inject } from '@angular/core';
import { ConfirmDialogService } from '../../services/confirm-dialog.service';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  template: `
    @if (dialog.state(); as s) {
      <div class="cd-backdrop" (click)="dialog.close(null)">
        <div class="cd-panel" role="alertdialog" aria-modal="true"
             aria-labelledby="cd-title" aria-describedby="cd-message"
             (click)="$event.stopPropagation()">
          <h2 id="cd-title">{{ s.title }}</h2>
          <p id="cd-message">{{ s.message }}</p>
          <div class="cd-actions">
            @for (a of s.actions; track a.value) {
              <button type="button" class="cd-btn" [class]="'cd-btn cd-' + (a.style || 'secondary')"
                      (click)="dialog.close(a.value)">{{ a.label }}</button>
            }
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .cd-backdrop {
      position: fixed; inset: 0; z-index: 10000;
      background: var(--ui-overlay, rgba(9, 13, 20, 0.85));
      display: flex; align-items: center; justify-content: center; padding: 1rem;
    }
    .cd-panel {
      width: 100%; max-width: 440px;
      background: var(--ui-surface-elevated, #18181b);
      border: 1px solid var(--ui-border, #27272a);
      border-radius: 12px; padding: 1.5rem;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
    }
    h2 { margin: 0 0 0.5rem; font-size: 1.15rem; color: var(--ui-text, #fafafa); }
    p { margin: 0 0 1.25rem; color: var(--ui-text-secondary, #a1a1aa); white-space: pre-line; line-height: 1.5; }
    .cd-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: flex-end; }
    .cd-btn {
      min-height: 44px; padding: 0.5rem 1rem; border-radius: 8px; font: inherit; font-weight: 600;
      cursor: pointer; border: 1px solid var(--ui-border, #27272a);
    }
    .cd-btn:focus-visible { outline: 2px solid var(--ui-accent, #f59e0b); outline-offset: 2px; }
    .cd-secondary { background: transparent; color: var(--ui-text, #fafafa); }
    .cd-primary { background: var(--ui-accent, #f59e0b); border-color: transparent; color: #111; }
    .cd-danger { background: var(--ui-danger, #dc2626); border-color: transparent; color: #fff; }
    @media (max-width: 480px) { .cd-actions { flex-direction: column-reverse; } .cd-btn { width: 100%; } }
  `],
})
export class ConfirmDialogComponent {
  readonly dialog = inject(ConfirmDialogService);
  private readonly host: ElementRef<HTMLElement> = inject(ElementRef);
  private previousFocus: HTMLElement | null = null;

  constructor() {
    effect(() => {
      if (this.dialog.state()) {
        this.previousFocus = document.activeElement as HTMLElement | null;
        // Focus the last (primary) action once rendered.
        setTimeout(() => {
          const buttons = this.host.nativeElement.querySelectorAll<HTMLButtonElement>('.cd-btn');
          buttons[buttons.length - 1]?.focus();
        });
      } else if (this.previousFocus) {
        this.previousFocus.focus?.();
        this.previousFocus = null;
      }
    });
  }

  @HostListener('document:keydown', ['$event'])
  onKeydown(event: KeyboardEvent) {
    if (!this.dialog.state()) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      this.dialog.close(null);
    } else if (event.key === 'Tab') {
      const buttons = Array.from(this.host.nativeElement.querySelectorAll<HTMLButtonElement>('.cd-btn'));
      if (!buttons.length) return;
      const idx = buttons.indexOf(document.activeElement as HTMLButtonElement);
      const next = event.shiftKey ? (idx <= 0 ? buttons.length - 1 : idx - 1) : (idx + 1) % buttons.length;
      event.preventDefault();
      buttons[next].focus();
    }
  }
}
