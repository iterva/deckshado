import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { IconComponent } from '../../../../components/icon/icon.component';

interface TutorialStep {
  id: number;
  icon: string;
  title: string;
  description: string;
  tourId?: string;
}

const STEPS: TutorialStep[] = [
  { id: 1, icon: 'eye', title: 'Explorar Cartas', description: 'Filtra y visualiza todas las cartas disponibles de Mitos y Leyendas desde la pestaña Colección.', tourId: 'codex' },
  { id: 2, icon: 'folder', title: 'Mi Carpeta', description: 'Gestiona las copias que posees: toca una carta para editar cantidad, precio y estado.', tourId: 'carpeta' },
  { id: 3, icon: 'heart', title: 'Mi Wishlist', description: 'Marca las cartas que deseas conseguir para tus mazos.', tourId: 'wishlist' },
  { id: 4, icon: 'globe', title: 'Mercado', description: 'Publica y revisa las cartas que tienes a la venta, con foto real incluida.', tourId: 'mercado' },
  { id: 5, icon: 'tag', title: 'Pedidos', description: 'Acepta o rechaza pedidos de compradores y revisa el historial de transacciones.', tourId: 'pedidos' },
  { id: 6, icon: 'bar-chart-3', title: 'Estadísticas', description: 'Revisa tu progreso: cartas totales, valor estimado y distribución por rareza.', tourId: 'stats' },
];

@Component({
  selector: 'app-carpeta-guide-modal',
  imports: [IconComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
  @if (isOpen()) {
    <div class="modal-overlay" (click)="closeModal()">
      <div class="modal-container" (click)="$event.stopPropagation()">

        <header class="modal-header">
          <h2>Guía de la Carpeta</h2>
          <button class="close-btn" (click)="closeModal()" aria-label="Cerrar modal">
            <app-icon name="x" [size]="16"></app-icon>
          </button>
        </header>

        <div class="cards-grid">
          @for (step of steps; track step.id) {
            <div class="step-card"
                 [class.has-tour]="!!step.tourId"
                 [class.completed]="!!step.tourId && completedTours().has(step.tourId)"
                 [attr.role]="step.tourId ? 'button' : null"
                 [attr.tabindex]="step.tourId ? 0 : null"
                 (click)="step.tourId && onCardClick(step.tourId)"
                 (keydown.enter)="step.tourId && onCardClick(step.tourId)">
              <div class="card-top">
                <span class="step-badge">{{ step.id }}</span>
                <div class="step-icon"><app-icon [name]="step.icon" [size]="22"></app-icon></div>
              </div>
              <div class="card-content">
                <h3>{{ step.title }}</h3>
                <p>{{ step.description }}</p>
              </div>
              @if (step.tourId) {
                <div class="card-tour-hint">
                  @if (completedTours().has(step.tourId)) {
                    <app-icon name="check-circle" [size]="13"></app-icon> Completado · Ver de nuevo
                  } @else {
                    <app-icon name="arrow-right" [size]="13"></app-icon> Recorrer esta sección
                  }
                </div>
              }
            </div>
          }
        </div>

        <footer class="modal-footer">
          <div class="footer-left">
            <div class="help-icon"><app-icon name="help-circle" [size]="14"></app-icon></div>
            <span class="progress-text">{{ steps.length }} secciones</span>
          </div>
          <div class="footer-actions">
            <button class="btn-secondary" (click)="closeModal()">Ya conozco el sistema</button>
            <button class="btn-primary" (click)="onStartTour()">Entendido</button>
          </div>
        </footer>

      </div>
    </div>
  }
  `,
  styles: [`
    .modal-overlay {
      position: fixed; inset: 0;
      background-color: var(--ui-overlay, rgba(9, 13, 20, 0.85));
      display: flex; align-items: center; justify-content: center;
      z-index: 9999; backdrop-filter: blur(4px); padding: 1rem;
    }

    .modal-container {
      background-color: var(--ui-surface-elevated, #1e1e3a);
      border-radius: var(--ui-radius-lg, 14px);
      width: 100%; max-width: 900px;
      box-shadow: var(--ui-shadow-sm, 0 20px 40px rgba(0,0,0,.4));
      border: 1px solid var(--ui-border, #333);
      display: flex; flex-direction: column;
    }

    .modal-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 24px 32px; border-bottom: 1px solid var(--ui-border, #333);
    }
    .modal-header h2 { margin: 0; font-size: 1.5rem; font-weight: 600; color: var(--ui-text, #fff); }
    .close-btn {
      background: transparent; border: none; color: var(--ui-text-muted, #888); cursor: pointer;
      transition: color 0.2s ease; display: flex; align-items: center; justify-content: center;
    }
    .close-btn:hover { color: var(--ui-text, #fff); }

    .cards-grid {
      display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; padding: 32px;
    }
    @media (max-width: 768px) { .cards-grid { grid-template-columns: repeat(2, 1fr); padding: 20px; } }
    @media (max-width: 480px) { .cards-grid { grid-template-columns: 1fr; } }

    .step-card {
      background-color: var(--ui-card, #171e2d); border: 1px solid var(--ui-border, #333); border-radius: var(--ui-radius-md, 10px);
      padding: 24px; transition: all 0.3s ease; cursor: default; display: flex; flex-direction: column; gap: 16px;
    }
    .step-card:hover {
      border-color: var(--ui-accent, #f59e0b); transform: translateY(-4px); box-shadow: var(--ui-shadow-sm, 0 10px 24px rgba(0,0,0,.3));
    }
    .step-card:hover .step-icon { color: var(--ui-accent, #f59e0b); }
    .step-card.has-tour { cursor: pointer; }
    .step-card.has-tour:focus-visible { outline: 2px solid var(--ui-accent, #f59e0b); outline-offset: 2px; }
    .step-card.completed { border-color: var(--ui-accent, #f59e0b); }
    .card-top { display: flex; justify-content: space-between; align-items: flex-start; }
    .card-tour-hint {
      display: flex; align-items: center; gap: .35rem; font-size: .78rem; font-weight: 600;
      color: var(--ui-accent, #f59e0b); margin-top: -4px;
    }
    .step-badge {
      background-color: var(--ui-accent, #f59e0b); color: #101226; font-weight: bold; width: 28px; height: 28px;
      border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.875rem;
    }
    .step-icon {
      width: 48px; height: 48px; border-radius: var(--ui-radius-md, 10px); background-color: var(--ui-accent-glow, rgba(245,158,11,.15));
      display: flex; align-items: center; justify-content: center; color: var(--ui-accent, #f59e0b);
      transition: all 0.3s ease;
    }
    .card-content h3 { margin: 0 0 8px 0; font-size: 1.125rem; color: var(--ui-text, #fff); font-weight: 500; }
    .card-content p { margin: 0; font-size: 0.875rem; color: var(--ui-text-muted, #888); line-height: 1.5; }

    .modal-footer {
      display: flex; justify-content: space-between; align-items: center;
      padding: 24px 32px; border-top: 1px solid var(--ui-border, #333);
    }
    @media (max-width: 600px) { .modal-footer { flex-direction: column; gap: 20px; } }
    .footer-left { display: flex; align-items: center; gap: 12px; }
    .help-icon {
      width: 24px; height: 24px; border: 1px solid var(--ui-text-muted, #888); color: var(--ui-text-muted, #888);
      border-radius: 50%; display: flex; align-items: center; justify-content: center;
    }
    .progress-text { color: var(--ui-text-muted, #888); font-size: 0.875rem; }
    .footer-actions { display: flex; gap: 16px; }
    @media (max-width: 600px) { .footer-actions { width: 100%; flex-direction: column; } }
    .footer-actions button {
      padding: 10px 20px; border-radius: var(--ui-radius-sm, 8px); font-weight: 500; font-size: 0.95rem;
      cursor: pointer; transition: all 0.2s ease; font-family: inherit;
    }
    .btn-secondary { background: transparent; border: none; color: var(--ui-text-muted, #888); }
    .btn-secondary:hover { color: var(--ui-text, #fff); background-color: var(--ui-surface, #171e2d); }
    .btn-primary {
      background-color: var(--ui-accent, #f59e0b); color: #101226; border: none;
      box-shadow: 0 4px 12px var(--ui-accent-glow, rgba(245,158,11,.15));
    }
    .btn-primary:hover { background-color: var(--ui-accent-strong, #d97706); transform: translateY(-1px); }
  `],
})
export class CarpetaGuideModalComponent {
  isOpen = input(false);
  completedTours = input<Set<string>>(new Set());
  close = output<void>();
  startTour = output<void>();
  startCardTour = output<string>();

  readonly steps = STEPS;

  closeModal() {
    this.close.emit();
  }

  onStartTour() {
    this.startTour.emit();
    this.closeModal();
  }

  onCardClick(tourId: string) {
    this.startCardTour.emit(tourId);
    this.closeModal();
  }
}
