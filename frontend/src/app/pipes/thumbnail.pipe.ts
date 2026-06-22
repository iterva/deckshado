import { Pipe, PipeTransform } from '@angular/core';
import { environment } from '../../environments/environment';

@Pipe({ name: 'thumb', standalone: true })
export class ThumbnailPipe implements PipeTransform {
  /**
   * Returns a reliable thumbnail URL without external proxy dependency.
   * - Cloudinary images are optimized via native Cloudinary transformations.
   * - Other hosts keep direct URL to avoid third-party proxy failures.
   * @param url Original image URL
   * @param width Desired width in pixels (default 150)
   */
  transform(url: string | null | undefined, width: number = 150): string {
    if (!url) return '';

    const normalized = this.normalizeImageUrl(url.trim());
    if (!normalized) return '';

    return this.optimizeCloudinaryUrl(normalized, width);
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

  private optimizeCloudinaryUrl(url: string, width: number): string {
    const marker = '/image/upload/';
    const markerIndex = url.indexOf(marker);
    if (markerIndex === -1 || !url.includes('res.cloudinary.com/')) {
      return url;
    }

    const prefix = url.slice(0, markerIndex + marker.length);
    const suffix = url.slice(markerIndex + marker.length);

    // Keep existing transformed URLs as-is to avoid stacking transformations.
    if (/^(?:[a-z]{1,3}_[^/]+,?)+\//i.test(suffix)) {
      return url;
    }

    const safeWidth = Math.max(80, Math.min(900, Math.round(width || 150)));
    const quality = safeWidth <= 120 ? 'q_auto:low' : safeWidth <= 260 ? 'q_auto:good' : 'q_auto';
    const transform = `f_auto,${quality},dpr_auto,w_${safeWidth},c_limit`;

    return `${prefix}${transform}/${suffix}`;
  }
}
