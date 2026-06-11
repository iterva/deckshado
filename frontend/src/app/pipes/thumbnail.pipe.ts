import { Pipe, PipeTransform } from '@angular/core';
import { environment } from '../../environments/environment';

@Pipe({ name: 'thumb', standalone: true })
export class ThumbnailPipe implements PipeTransform {
  /**
   * Generates an optimized thumbnail URL via wsrv.nl proxy.
   * In local development, it returns direct backend URLs to avoid
   * depending on external image proxy services.
   * @param url Original image URL
   * @param width Desired width in pixels (default 150)
   */
  transform(url: string | null | undefined, width: number = 150): string {
    if (!url) return '';

    const normalized = this.normalizeImageUrl(url.trim());
    if (!normalized) return '';

    // Local mode requested by user: serve direct URLs while developing.
    if (this.isLocalDevMode()) {
      return normalized;
    }

    const q = width <= 100 ? 55 : width <= 150 ? 60 : 70;
    return `https://wsrv.nl/?url=${encodeURIComponent(normalized)}&w=${width}&output=webp&q=${q}&we`;
  }

  private isLocalDevMode(): boolean {
    if (environment.production) return false;
    if (typeof window === 'undefined') return false;
    const host = window.location.hostname;
    return host === 'localhost' || host === '127.0.0.1';
  }

  private normalizeImageUrl(raw: string): string {
    if (!raw) return '';

    if (raw.startsWith('/')) {
      return `${this.backendOrigin()}${raw}`;
    }

    if (raw.startsWith('//')) {
      return `https:${raw}`;
    }

    // In local development, prefer local media when URL points to production backend.
    if (!environment.production && raw.includes('iterva.pythonanywhere.com/media/')) {
      return raw.replace('https://iterva.pythonanywhere.com', 'http://localhost:8000');
    }

    return raw;
  }

  private backendOrigin(): string {
    const api = environment.apiUrl || '';
    return api.endsWith('/api') ? api.slice(0, -4) : api;
  }
}
