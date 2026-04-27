import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Card, BanlistEntry } from '../../models';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';

/**
 * Entrada del mazo (panel derecho del constructor). Componente "tonto":
 * recibe los datos calculados y emite eventos. Mantiene el swipe-to-remove
 * dentro del propio componente para no contaminar al padre con el estado
 * por-tarjeta del gesto.
 */
@Component({
  selector: 'app-deck-entry',
  standalone: true,
  imports: [CommonModule, ThumbnailPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './deck-entry.component.html',
  styleUrl: './deck-entry.component.scss',
})
export class DeckEntryComponent {
  @Input({ required: true }) card!: Card;
  @Input({ required: true }) quantity!: number;
  @Input() banStatus: BanlistEntry | null = null;
  @Input() addDisabled = false;
  @Input() recentlyAdded = false;
  /** True para entradas del sidedeck (estilo distinto). */
  @Input() side = false;

  @Output() add = new EventEmitter<void>();
  @Output() remove = new EventEmitter<void>();

  // Swipe state local — no necesita salir del componente.
  private swipeStartX: number | null = null;
  swipeOffset = 0;

  onTouchStart(event: TouchEvent) {
    this.swipeStartX = event.touches[0].clientX;
  }

  onTouchMove(event: TouchEvent) {
    if (this.swipeStartX === null) return;
    const dx = event.touches[0].clientX - this.swipeStartX;
    this.swipeOffset = Math.max(-160, Math.min(0, dx));
  }

  onTouchEnd() {
    if (this.swipeOffset < -80) {
      this.remove.emit();
    }
    this.swipeOffset = 0;
    this.swipeStartX = null;
  }
}
