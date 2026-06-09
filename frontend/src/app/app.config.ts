import { ApplicationConfig, ErrorHandler, provideBrowserGlobalErrorListeners, provideZoneChangeDetection, isDevMode, LOCALE_ID } from '@angular/core';
import { provideRouter, TitleStrategy } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideServiceWorker } from '@angular/service-worker';
import { registerLocaleData } from '@angular/common';
import localeEsCL from '@angular/common/locales/es-CL';

import { routes } from './app.routes';
import { authInterceptor } from './interceptors/auth.interceptor';
import { SeoTitleStrategy } from './seo-title-strategy';

registerLocaleData(localeEsCL);

class GlobalErrorHandler implements ErrorHandler {
  handleError(error: any) {
    const message = error?.message || error?.toString?.() || '';

    // Angular puede emitir esta excepción cuando una navegación es reemplazada
    // por otra (p.ej. redirección/guard). No es un fallo funcional.
    if (
      error?.name === 'NavigationCancelingError' ||
      /NavigationCancelingError|Navigation canceled/i.test(message)
    ) {
      return;
    }

    const chunkError = /Loading chunk|Failed to fetch dynamically imported module|ChunkLoadError/;
    if (chunkError.test(message)) {
      if (!sessionStorage.getItem('chunk_reload')) {
        sessionStorage.setItem('chunk_reload', '1');
        window.location.reload();
        return;
      }
      sessionStorage.removeItem('chunk_reload');
    }
    console.error(error);
  }
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    { provide: TitleStrategy, useClass: SeoTitleStrategy },
    provideHttpClient(withInterceptors([authInterceptor])),
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
    { provide: LOCALE_ID, useValue: 'es-CL' },
    provideServiceWorker('ngsw-worker.js', {
      enabled: !isDevMode(),
      registrationStrategy: 'registerWhenStable:30000',
    }),
  ]
};
