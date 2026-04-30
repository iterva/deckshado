import 'zone.js';
import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { environment } from './environments/environment';

// Inicializa Sentry solo si hay DSN configurado (lazy import para no aumentar el bundle si no se usa).
if (environment.sentryDsn) {
  import('@sentry/angular').then((Sentry) => {
    Sentry.init({
      dsn: environment.sentryDsn,
      environment: environment.production ? 'production' : 'development',
      tracesSampleRate: 0.1,
      replaysSessionSampleRate: 0.0,
      replaysOnErrorSampleRate: 1.0,
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({ maskAllText: false, blockAllMedia: false }),
      ],
    });
  }).catch((e) => console.warn('[Sentry] no se pudo cargar:', e));
}

bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));
