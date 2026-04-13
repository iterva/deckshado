import { ApplicationConfig, ErrorHandler, provideBrowserGlobalErrorListeners, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';

import { routes } from './app.routes';
import { authInterceptor } from './interceptors/auth.interceptor';

class GlobalErrorHandler implements ErrorHandler {
  handleError(error: any) {
    const chunkError = /Loading chunk|Failed to fetch dynamically imported module|ChunkLoadError/;
    if (chunkError.test(error?.message || error?.toString())) {
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
    provideHttpClient(withInterceptors([authInterceptor])),
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
  ]
};
