import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'thumb', standalone: true })
export class ThumbnailPipe implements PipeTransform {
  /**
   * Generates an optimized thumbnail URL via wsrv.nl proxy.
   * Converts PNG to WebP and resizes to the specified width.
   * Quality scales with size for faster small thumbnails.
   * @param url  Original image URL
   * @param width  Desired width in pixels (default 150)
   */
  transform(url: string | null | undefined, width: number = 150): string {
    if (!url) return '';
    const q = width <= 100 ? 55 : width <= 150 ? 60 : 70;
    return `https://wsrv.nl/?url=${encodeURIComponent(url)}&w=${width}&output=webp&q=${q}&we`;
  }
}
