import { Component, OnInit, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { DeckService } from '../../services/deck.service';
import { Deck, DeckEntry } from '../../models';

interface CostBucket { label: string; count: number; pct: number; }
interface CompareCardRow {
  cardId: number;
  name: string;
  type: string;
  cost: string | null;
  imageUrl: string;
  /** Cantidades por mazo, indexado igual que `decks`. */
  quantities: number[];
  /** En cuantos mazos aparece (1..N). */
  presentIn: number;
}

@Component({
  selector: 'app-compare-decks',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './compare-decks.component.html',
  styleUrl: './compare-decks.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CompareDecksComponent implements OnInit {
  decks: Deck[] = [];
  loading = true;
  error: string | null = null;

  /** Curvas de coste por mazo (mismo índice que `decks`). */
  costCurves: CostBucket[][] = [];
  /** Coste promedio por mazo. */
  avgCosts: number[] = [];
  /** Total de cartas en el main por mazo. */
  cardCounts: number[] = [];
  /** Total de cartas en el sideboard por mazo. */
  sideCounts: number[] = [];
  /** Filas comparativas, agrupadas por tipo. */
  groupedRows: { type: string; rows: CompareCardRow[] }[] = [];
  /** Resumen: copias en común (intersección) y diferencias por mazo. */
  summary: { common: number; diffPerDeck: number[] } = { common: 0, diffPerDeck: [] };

  /** Mostrar solo diferencias en la tabla (oculta filas comunes con misma cantidad). */
  showDiffOnly = false;

  private readonly typeOrder: Record<string, number> = {
    'Oro': 1,
    'Aliado': 2,
    'Arma': 3,
    'Talismán': 4,
    'Talisman': 4,
    'Tótem': 5,
    'Totem': 5,
    'Monumento': 6,
  };

  private readonly raceLabels: Record<string, string> = {
    dream: 'Dream', totem: 'Tótem', eterno: 'Eterno', faerie: 'Faerie',
    dragon: 'Dragón', sombra: 'Sombra', heroe: 'Héroe', sacerdote: 'Sacerdote',
    guerrero: 'Guerrero', bestia: 'Bestia', caballero: 'Caballero',
  };
  private readonly formatLabels: Record<string, string> = { imp: 'Imperial', fx: 'FX', esc: 'Escuelas Elementales', imp_r: 'Imperio Retro' };

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private deckService: DeckService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    const idsParam = this.route.snapshot.queryParamMap.get('ids') ?? '';
    const source = (this.route.snapshot.queryParamMap.get('source') ?? 'mine') as 'mine' | 'public' | 'team';
    const ids = idsParam.split(',').map(s => parseInt(s, 10)).filter(n => !isNaN(n));
    if (ids.length < 2) {
      this.error = 'Necesitas al menos 2 mazos para comparar.';
      this.loading = false;
      this.cdr.detectChanges();
      return;
    }
    if (ids.length > 3) ids.length = 3;

    const requests = ids.map(id => {
      const obs = source === 'public'
        ? this.deckService.getPublicDeck(id)
        : source === 'team'
          ? this.deckService.getTeamDeck(id)
          : this.deckService.getDeck(id);
      return obs.pipe(catchError(() => of(null as any)));
    });

    forkJoin(requests).subscribe(results => {
      this.decks = results.filter((d: Deck | null): d is Deck => !!d);
      if (this.decks.length < 2) {
        this.error = 'No se pudieron cargar los mazos solicitados.';
        this.loading = false;
        this.cdr.detectChanges();
        return;
      }
      this.computeStats();
      this.loading = false;
      this.cdr.detectChanges();
    });
  }

  private computeStats() {
    this.costCurves = this.decks.map(d => this.buildCostCurve(d));
    this.avgCosts = this.decks.map(d => this.buildAvgCost(d));
    this.cardCounts = this.decks.map(d => (d.entries ?? []).reduce((s, e) => s + e.quantity, 0));
    this.sideCounts = this.decks.map(d => (d.sideboard_entries ?? []).reduce((s, e) => s + e.quantity, 0));
    this.buildGroupedRows();
    this.buildSummary();
  }

  private buildCostCurve(deck: Deck): CostBucket[] {
    const buckets = [0, 0, 0, 0, 0, 0, 0, 0];
    for (const entry of deck.entries ?? []) {
      const card = entry.card_detail;
      if (card.type_name === 'Oro') continue;
      const raw = card.cost;
      if (raw === null || raw === undefined || raw === '') continue;
      const n = Number(raw);
      if (!Number.isFinite(n)) continue;
      const idx = n >= 7 ? 7 : Math.max(0, Math.min(7, Math.floor(n)));
      buckets[idx] += entry.quantity;
    }
    const max = Math.max(1, ...buckets);
    return buckets.map((count, i) => ({
      label: i === 7 ? '7+' : String(i),
      count,
      pct: Math.round((count / max) * 100),
    }));
  }

  private buildAvgCost(deck: Deck): number {
    let sum = 0, n = 0;
    for (const entry of deck.entries ?? []) {
      const card = entry.card_detail;
      if (card.type_name === 'Oro') continue;
      const raw = card.cost;
      if (raw === null || raw === undefined || raw === '') continue;
      const v = Number(raw);
      if (!Number.isFinite(v)) continue;
      sum += v * entry.quantity;
      n += entry.quantity;
    }
    return n === 0 ? 0 : Math.round((sum / n) * 10) / 10;
  }

  private buildGroupedRows() {
    const N = this.decks.length;
    const byKey = new Map<string, CompareCardRow>();
    this.decks.forEach((deck, i) => {
      for (const entry of deck.entries ?? []) {
        const card = entry.card_detail;
        // Agrupar por nombre normalizado para fusionar duplicados de distintas ediciones.
        const key = (card.name ?? '').trim().toLowerCase();
        if (!byKey.has(key)) {
          byKey.set(key, {
            cardId: card.id,
            name: card.name,
            type: card.type_name ?? 'Otro',
            cost: card.cost ?? null,
            imageUrl: card.image_url,
            quantities: Array(N).fill(0),
            presentIn: 0,
          });
        }
        const row = byKey.get(key)!;
        row.quantities[i] += entry.quantity;
      }
    });
    for (const row of byKey.values()) {
      row.presentIn = row.quantities.filter(q => q > 0).length;
    }

    // Group by type
    const byType = new Map<string, CompareCardRow[]>();
    for (const row of byKey.values()) {
      if (!byType.has(row.type)) byType.set(row.type, []);
      byType.get(row.type)!.push(row);
    }
    this.groupedRows = [...byType.entries()]
      .map(([type, rows]) => ({
        type,
        rows: rows.sort((a, b) => {
          // Por exclusividad desc (cartas únicas primero), luego por nombre
          if (a.presentIn !== b.presentIn) return a.presentIn - b.presentIn;
          return a.name.localeCompare(b.name);
        }),
      }))
      .sort((a, b) => (this.typeOrder[a.type] ?? 99) - (this.typeOrder[b.type] ?? 99));
  }

  private buildSummary() {
    const N = this.decks.length;
    // Copias en común = sum por fila de min(quantities) entre todos los mazos.
    let common = 0;
    for (const group of this.groupedRows) {
      for (const row of group.rows) {
        const min = Math.min(...row.quantities);
        if (min > 0) common += min;
      }
    }
    // Diferencias por mazo = total[i] - common (lo que sobra en cada mazo).
    const diffPerDeck = this.cardCounts.map(total => Math.max(0, total - common));
    this.summary = { common, diffPerDeck };
  }

  /** Filas visibles según el toggle "solo diferencias". */
  visibleRows(rows: CompareCardRow[]): CompareCardRow[] {
    if (!this.showDiffOnly) return rows;
    return rows.filter(r => {
      if (r.presentIn < this.decks.length) return true;
      // Misma cantidad en todos = común "puro"
      const first = r.quantities[0];
      return r.quantities.some(q => q !== first);
    });
  }

  toggleDiffOnly() {
    this.showDiffOnly = !this.showDiffOnly;
    this.cdr.detectChanges();
  }

  goBack() {
    this.router.navigate(['/decks']);
  }

  getRaceLabel(race?: string): string {
    if (!race) return 'Dream';
    return this.raceLabels[race] || race;
  }

  getFormatLabel(format?: string): string {
    if (!format) return 'Imperial';
    return this.formatLabels[format] || format;
  }

  /** Diferentes formatos entre los mazos comparados → mostrar warning. */
  get hasFormatMismatch(): boolean {
    if (this.decks.length < 2) return false;
    const first = this.decks[0].format ?? '';
    return this.decks.some(d => (d.format ?? '') !== first);
  }

  /** Para alturas relativas en la curva combinada. */
  combinedMaxCount(bucketIdx: number): number {
    return Math.max(1, ...this.costCurves.map(c => c[bucketIdx]?.count ?? 0));
  }

  costPctForDeck(deckIdx: number, bucketIdx: number): number {
    const all = this.costCurves.flatMap(c => c.map(b => b.count));
    const max = Math.max(1, ...all);
    const count = this.costCurves[deckIdx]?.[bucketIdx]?.count ?? 0;
    return Math.round((count / max) * 100);
  }
}
