import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'thumb', standalone: true })
export class ThumbnailPipe implements PipeTransform {
  /**
   * Generates an optimized image URL.
   * - Cloudinary images: apply native Cloudinary transformations.
   * - Other hosts: keep original URL to avoid proxy bottlenecks.
   * @param url  Original image URL
   * @param width  Desired width in pixels (default 150)
   */
  transform(url: string | null | undefined, width: number = 150): string {
    if (!url) return '';
    const secureUrl = url.trim().replace(/^http:\/\//i, 'https://');
    if (!secureUrl) return '';

    // Use Cloudinary CDN transforms directly for speed and reliability.
    if (/res\.cloudinary\.com/i.test(secureUrl)) {
      return this.cloudinaryThumb(secureUrl, width);
    }

    return secureUrl;
  }

  private cloudinaryThumb(url: string, width: number): string {
    const marker = '/image/upload/';
    const markerIndex = url.indexOf(marker);
    if (markerIndex === -1) return url;

    const prefix = url.slice(0, markerIndex + marker.length);
    const suffix = url.slice(markerIndex + marker.length);
    const firstSegment = suffix.split('/')[0] ?? '';

    // If URL already has an explicit transform segment, keep it unchanged.
    const hasExistingTransform =
      !/^v\d+$/.test(firstSegment) &&
      /(^|,)(w_\d+|q_auto|f_auto|c_[a-z]+)/.test(firstSegment);
    if (hasExistingTransform) return url;

    const safeWidth = Math.max(40, Math.round(width || 150));
    const quality = safeWidth <= 120 ? 'q_auto:eco' : 'q_auto:good';
    const transform = `f_auto,dpr_auto,c_limit,w_${safeWidth},${quality}`;

    return `${prefix}${transform}/${suffix}`;
  }
}
