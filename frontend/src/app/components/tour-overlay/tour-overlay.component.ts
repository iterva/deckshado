import { ChangeDetectionStrategy, Component, effect, inject, signal } from '@angular/core';
import { IconComponent } from '../icon/icon.component';
import { TourService } from '../../services/tour.service';

interface TourRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

const PADDING = 8;
const CALLOUT_GAP = 16;
const CALLOUT_WIDTH = 320;

@Component({
  selector: 'app-tour-overlay',
  imports: [IconComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '(window:resize)': 'measure()',
    '(window:scroll)': 'measure()',
  },
  template: `
  @if (tour.active()) {
    <div class="tour-veil"></div>
    @if (rect(); as r) {
      <div class="tour-spotlight"
           [style.top.px]="r.top - padding" [style.left.px]="r.left - padding"
           [style.width.px]="r.width + padding * 2" [style.height.px]="r.height + padding * 2"></div>
    }
    <div class="tour-callout" [style.top.px]="calloutTop()" [style.left.px]="calloutLeft()">
      <div class="tour-callout-head">
        <span class="tour-step-count">{{ tour.stepIndex() + 1 }} / {{ tour.total() }}</span>
        <button class="tour-close" (click)="tour.close()" aria-label="Cerrar guía">
          <app-icon name="x" [size]="14"></app-icon>
        </button>
      </div>
      <h4>{{ tour.currentStep()?.title }}</h4>
      <p>{{ tour.currentStep()?.description }}</p>
      <div class="tour-actions">
        <button class="btn-tour btn-tour-ghost" (click)="tour.prev()" [disabled]="tour.isFirst()">← Atrás</button>
        <button class="btn-tour btn-tour-primary" (click)="tour.next()">
          {{ tour.isLast() ? 'Finalizar' : 'Continuar →' }}
        </button>
      </div>
    </div>
  }
  `,
  styles: [`
    .tour-veil {
      position: fixed; inset: 0; z-index: 9997; background: transparent;
    }
    .tour-spotlight {
      position: fixed; z-index: 9998; border-radius: 12px; pointer-events: none;
      box-shadow: 0 0 0 9999px rgba(6, 8, 14, 0.78);
      border: 2px solid var(--ui-accent, #06b6d4);
      transition: top .25s ease, left .25s ease, width .25s ease, height .25s ease;
    }
    .tour-callout {
      position: fixed; z-index: 9999; width: 320px; max-width: calc(100vw - 24px);
      background: var(--ui-surface-elevated, #16213e); border: 1px solid var(--ui-border, #2a3a4a);
      border-radius: 12px; padding: 1rem 1.1rem; box-shadow: 0 20px 45px rgba(0,0,0,.5);
      transition: top .25s ease, left .25s ease;
    }
    .tour-callout-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: .5rem; }
    .tour-step-count {
      font-size: .72rem; font-weight: 700; color: var(--ui-accent, #06b6d4);
      background: var(--ui-accent-glow, rgba(6,182,212,.15)); border-radius: 999px; padding: .15rem .55rem;
    }
    .tour-close {
      background: transparent; border: none; color: var(--ui-text-muted, #9ba3b4); cursor: pointer;
      display: flex; align-items: center; justify-content: center;
    }
    .tour-close:hover { color: var(--ui-text, #fff); }
    .tour-callout h4 { margin: 0 0 .4rem; color: var(--ui-text, #fff); font-size: 1rem; }
    .tour-callout p { margin: 0 0 .9rem; color: var(--ui-text-secondary, #c8c8da); font-size: .85rem; line-height: 1.45; }
    .tour-actions { display: flex; justify-content: space-between; gap: .6rem; }
    .btn-tour {
      padding: .45rem .9rem; border-radius: 8px; font-size: .85rem; font-weight: 600; cursor: pointer;
      border: 1px solid var(--ui-border, #2a3a4a); background: transparent; color: var(--ui-text-secondary, #c8c8da);
    }
    .btn-tour:disabled { opacity: .4; cursor: not-allowed; }
    .btn-tour-ghost:hover:not(:disabled) { color: var(--ui-text, #fff); }
    .btn-tour-primary {
      background: var(--ui-accent, #06b6d4); border-color: var(--ui-accent, #06b6d4); color: #04222b;
      margin-left: auto;
    }
    .btn-tour-primary:hover { filter: brightness(1.08); }
  `],
})
export class TourOverlayComponent {
  readonly tour = inject(TourService);

  readonly padding = PADDING;
  readonly rect = signal<TourRect | null>(null);
  readonly calloutTop = signal(0);
  readonly calloutLeft = signal(0);

  constructor() {
    // Recompute whenever the active step (or tour) changes.
    effect(() => {
      const step = this.tour.currentStep();
      if (step) this.scrollToAndMeasure();
    }, { allowSignalWrites: true });
  }

  private scrollToAndMeasure() {
    const step = this.tour.currentStep();
    if (!step) return;
    const el = document.querySelector(step.target);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
    }
    setTimeout(() => this.measure(), 260);
    this.measure();
  }

  measure() {
    const step = this.tour.currentStep();
    if (!step) {
      this.rect.set(null);
      return;
    }
    const el = document.querySelector(step.target);
    if (!el) {
      this.rect.set(null);
      return;
    }
    const r = el.getBoundingClientRect();
    this.rect.set({ top: r.top, left: r.left, width: r.width, height: r.height });
    this.positionCallout(r);
  }

  private positionCallout(r: DOMRect) {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const spotBottom = r.bottom + PADDING;
    const spotTop = r.top - PADDING;

    let top: number;
    const fitsBelow = spotBottom + CALLOUT_GAP + 180 < vh;
    if (fitsBelow) {
      top = spotBottom + CALLOUT_GAP;
    } else {
      top = Math.max(12, spotTop - CALLOUT_GAP - 200);
    }
    top = Math.min(top, vh - 40);

    let left = r.left + r.width / 2 - CALLOUT_WIDTH / 2;
    left = Math.max(12, Math.min(left, vw - CALLOUT_WIDTH - 12));

    this.calloutTop.set(top);
    this.calloutLeft.set(left);
  }
}
