import { Injectable, signal, computed } from '@angular/core';

export interface TourStep {
  target: string;
  title: string;
  description: string;
}

@Injectable({ providedIn: 'root' })
export class TourService {
  private readonly _tourId = signal<string | null>(null);
  private readonly _steps = signal<TourStep[]>([]);
  private readonly _stepIndex = signal(0);
  private onComplete: (() => void) | null = null;

  readonly tourId = this._tourId.asReadonly();
  readonly steps = this._steps.asReadonly();
  readonly stepIndex = this._stepIndex.asReadonly();
  readonly active = computed(() => this._steps().length > 0);
  readonly currentStep = computed<TourStep | null>(() => this._steps()[this._stepIndex()] ?? null);
  readonly isFirst = computed(() => this._stepIndex() === 0);
  readonly isLast = computed(() => this._stepIndex() >= this._steps().length - 1);
  readonly total = computed(() => this._steps().length);

  start(tourId: string, steps: TourStep[], onComplete?: () => void) {
    this.onComplete = onComplete ?? null;
    this._tourId.set(tourId);
    this._steps.set(steps);
    this._stepIndex.set(0);
  }

  next() {
    if (this.isLast()) {
      this.finish();
      return;
    }
    this._stepIndex.update(i => i + 1);
  }

  prev() {
    this._stepIndex.update(i => Math.max(0, i - 1));
  }

  finish() {
    const cb = this.onComplete;
    this.close();
    cb?.();
  }

  close() {
    this._steps.set([]);
    this._stepIndex.set(0);
    this._tourId.set(null);
    this.onComplete = null;
  }
}
