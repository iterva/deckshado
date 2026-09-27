import { Injectable, signal } from '@angular/core';

export interface ConfirmDialogAction {
  /** Value resolved when the user picks this action. */
  value: string;
  label: string;
  style?: 'primary' | 'secondary' | 'danger';
}

export interface ConfirmDialogOptions {
  title: string;
  message: string;
  actions: ConfirmDialogAction[];
}

interface ConfirmDialogState extends ConfirmDialogOptions {
  resolve: (value: string | null) => void;
}

/**
 * In-app replacement for `window.confirm`: explicit button labels and it keeps
 * working in webviews that block native dialogs. Resolves with the chosen
 * action's `value`, or `null` if the dialog is dismissed (Escape / backdrop).
 */
@Injectable({ providedIn: 'root' })
export class ConfirmDialogService {
  readonly state = signal<ConfirmDialogState | null>(null);

  open(options: ConfirmDialogOptions): Promise<string | null> {
    this.state()?.resolve(null);
    return new Promise(resolve => this.state.set({ ...options, resolve }));
  }

  /** Simple yes/no confirmation for destructive actions. */
  async confirm(title: string, message: string, confirmLabel = 'Confirmar', danger = true): Promise<boolean> {
    const result = await this.open({
      title,
      message,
      actions: [
        { value: 'cancel', label: 'Cancelar', style: 'secondary' },
        { value: 'ok', label: confirmLabel, style: danger ? 'danger' : 'primary' },
      ],
    });
    return result === 'ok';
  }

  close(value: string | null) {
    const current = this.state();
    if (!current) return;
    this.state.set(null);
    current.resolve(value);
  }
}
