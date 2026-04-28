import { Pipe, PipeTransform } from '@angular/core';

/**
 * Tiempo relativo en español. Ej: "hace 5 min", "hace 2 días".
 * Acepta string ISO o Date. Para fechas > 60 días usa el día/mes/año.
 */
@Pipe({ name: 'relativeTime', standalone: true, pure: true })
export class RelativeTimePipe implements PipeTransform {
  transform(value: string | Date | null | undefined): string {
    if (!value) return '';
    const date = value instanceof Date ? value : new Date(value);
    if (isNaN(date.getTime())) return '';
    const diffSec = Math.round((Date.now() - date.getTime()) / 1000);
    if (diffSec < 0) return 'recién';
    if (diffSec < 30) return 'hace unos segundos';
    if (diffSec < 60) return `hace ${diffSec} s`;
    const diffMin = Math.round(diffSec / 60);
    if (diffMin < 60) return `hace ${diffMin} min`;
    const diffH = Math.round(diffMin / 60);
    if (diffH < 24) return `hace ${diffH} h`;
    const diffD = Math.round(diffH / 24);
    if (diffD === 1) return 'ayer';
    if (diffD < 7) return `hace ${diffD} días`;
    const diffW = Math.round(diffD / 7);
    if (diffW < 5) return `hace ${diffW} sem`;
    const diffMo = Math.round(diffD / 30);
    if (diffMo < 12) return `hace ${diffMo} ${diffMo === 1 ? 'mes' : 'meses'}`;
    const diffY = Math.round(diffD / 365);
    return `hace ${diffY} ${diffY === 1 ? 'año' : 'años'}`;
  }
}
