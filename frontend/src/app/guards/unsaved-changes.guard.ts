import { CanDeactivateFn } from '@angular/router';

/** Cualquier componente que implemente este contrato puede vetar la salida. */
export interface CanComponentDeactivate {
  canDeactivate: () => boolean | Promise<boolean>;
}

export const unsavedChangesGuard: CanDeactivateFn<CanComponentDeactivate> = (component) => {
  return component.canDeactivate ? component.canDeactivate() : true;
};
