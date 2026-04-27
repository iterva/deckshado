import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Card, BanlistEntry } from '../../models';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';

/**
 * Componente "tonto" (presentational) que muestra una carta en el listado del
 * constructor de mazos. No conoce el estado global del deck: el padre le pasa
 * todos los flags ya calculados y emite eventos con la acción del usuario.
 */
@Component({
  selector: 'app-mini-card',
  standalone: true,
  imports: [CommonModule, ThumbnailPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './mini-card.component.html',
  styleUrl: './mini-card.component.scss',
})
export class MiniCardComponent {
  @Input({ required: true }) card!: Card;
  @Input() qtyInDeck = 0;
  @Input() qtyInSide = 0;
  @Input() banStatus: BanlistEntry | null = null;
  /** Bloquea ambos botones + porque ya se alcanzó el máximo por nombre. */
  @Input() nameMaxed = false;
  /** Existe otra versión de esta carta en el mazo. */
  @Input() nameTaken = false;
  /** Carta no permitida por el filtro de raza del mazo. */
  @Input() raceBlocked = false;
  /** Mazo principal lleno (50). */
  @Input() mainFull = false;
  /** Sidedeck lleno (15). */
  @Input() sideFull = false;
  /** Texto de búsqueda por habilidad para mostrar el extracto. */
  @Input() abilitySearch = '';
  /** Marca para animar la carta cuando se acaba de añadir. */
  @Input() recentlyAdded = false;

  @Output() add = new EventEmitter<void>();
  @Output() remove = new EventEmitter<void>();
  @Output() addSide = new EventEmitter<void>();
  @Output() removeSide = new EventEmitter<void>();
  @Output() preview = new EventEmitter<MouseEvent>();
  @Output() holdStart = new EventEmitter<MouseEvent | TouchEvent>();
  @Output() holdEnd = new EventEmitter<void>();
  @Output() holdCancel = new EventEmitter<void>();

  get banned(): boolean {
    return this.banStatus?.status === 'banned';
  }

  get addDisabled(): boolean {
    return this.banned || this.nameMaxed || this.mainFull || this.raceBlocked;
  }

  get sideAddDisabled(): boolean {
    return this.banned || this.nameMaxed || this.sideFull || this.raceBlocked;
  }

  /** Extracto de la habilidad (≤80 chars) cuando hay búsqueda por habilidad. */
  get abilityExcerpt(): string | null {
    if (!this.abilitySearch || !this.card.ability) return null;
    const txt = this.card.ability;
    return txt.length > 80 ? txt.substring(0, 80) + '...' : txt;
  }
}
