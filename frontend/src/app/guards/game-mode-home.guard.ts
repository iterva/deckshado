import { CanMatchFn, Router, UrlSegment } from '@angular/router';
import { inject } from '@angular/core';

/**
 * Si el usuario tiene Riftbound como modo de juego preferido (guardado en
 * localStorage), redirige la home raíz (`/`) a `/riftbound`.
 *
 * Esto evita que abrir la URL principal "tire" al usuario a la home de MYL
 * cuando en realidad está usando Riftbound.
 */
export const gameModeHomeGuard: CanMatchFn = (_route, segments: UrlSegment[]) => {
  // Solo aplica a la ruta raíz exacta.
  if (segments.length !== 0) return true;

  try {
    const saved = localStorage.getItem('deckshado_game_mode');
    if (saved === 'riftbound') {
      const router = inject(Router);
      return router.parseUrl('/riftbound');
    }
  } catch {
    // localStorage puede no estar disponible (SSR, modo privado); ignorar.
  }
  return true;
};
