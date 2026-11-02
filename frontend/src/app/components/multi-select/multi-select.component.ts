import { ChangeDetectionStrategy, Component, ElementRef, computed, inject, input, output, signal } from '@angular/core';
import { IconComponent } from '../icon/icon.component';

export interface MultiSelectOption {
  value: string;
  label: string;
}

let nextId = 0;

/** Dropdown con casillas para elegir varias opciones. Sin selección = "todas". */
@Component({
  selector: 'app-multi-select',
  imports: [IconComponent],
  templateUrl: './multi-select.component.html',
  styleUrl: './multi-select.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    class: 'multi-select',
    '(document:click)': 'onDocumentClick($event)',
    '(keydown.escape)': 'closeAndFocus()',
  },
})
export class MultiSelectComponent {
  readonly options = input.required<MultiSelectOption[]>();
  readonly selected = input<string[]>([]);
  /** Texto cuando no hay nada elegido, p. ej. "Todos los tipos". */
  readonly placeholder = input.required<string>();
  /** Plural para el resumen, p. ej. "tipos" → "3 tipos". */
  readonly noun = input.required<string>();
  readonly ariaLabel = input<string>('');

  readonly selectedChange = output<string[]>();

  readonly open = signal(false);
  readonly panelId = `ms-panel-${nextId++}`;

  private readonly host = inject(ElementRef<HTMLElement>);

  readonly selectedSet = computed(() => new Set(this.selected()));

  readonly summary = computed(() => {
    const sel = this.selected();
    if (sel.length === 0) return this.placeholder();
    if (sel.length === 1) {
      return this.options().find(o => o.value === sel[0])?.label ?? this.placeholder();
    }
    return `${sel.length} ${this.noun()}`;
  });

  toggleOpen() {
    this.open.update(v => !v);
  }

  toggle(value: string) {
    const set = new Set(this.selected());
    if (set.has(value)) set.delete(value);
    else set.add(value);
    // Mantiene el orden de la lista de opciones.
    this.selectedChange.emit(this.options().map(o => o.value).filter(v => set.has(v)));
  }

  clear() {
    this.selectedChange.emit([]);
  }

  closeAndFocus() {
    if (!this.open()) return;
    this.open.set(false);
    this.host.nativeElement.querySelector('.ms-trigger')?.focus();
  }

  onDocumentClick(ev: MouseEvent) {
    if (this.open() && !this.host.nativeElement.contains(ev.target as Node)) {
      this.open.set(false);
    }
  }
}
