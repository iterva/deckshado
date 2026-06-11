import { Pipe, PipeTransform } from '@angular/core';
import { environment } from '../../environments/environment';

@Pipe({ name: 'thumb', standalone: true })
export class ThumbnailPipe implements PipeTransform {
  /**
   * Returns a stable image URL without third-party proxy dependency.
   * This avoids broken-image flashes when wsrv is slow/unavailable.
   * @param url  Original image URL
   * @param width  Unused, kept for template compatibility
   */
  transform(url: string | null | undefined, width: number = 150): string {
    if (!url) return '';
    void width;
    return this.normalizeImageUrl(url.trim());
  }

  private normalizeImageUrl(raw: string): string {
    if (!raw) return '';

    if (raw.startsWith('//')) {
      return `https:${raw}`;
    }

    if (raw.startsWith('/')) {
      return `${this.backendOrigin()}${raw}`;
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
