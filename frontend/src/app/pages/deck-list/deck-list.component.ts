import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { NgTemplateOutlet } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { DeckService } from '../../services/deck.service';
import { AuthService } from '../../services/auth.service';
import { Deck, Card } from '../../models';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';
import { RelativeTimePipe } from '../../pipes/relative-time.pipe';
import { IconComponent } from '../../components/icon/icon.component';

type Tab = 'public' | 'mine' | 'team';
type SortKey = 'recent' | 'created' | 'popular' | 'cards' | 'name' | 'name_desc';

@Component({
  selector: 'app-deck-list',
  standalone: true,
  imports: [RouterLink, FormsModule, NgTemplateOutlet, ThumbnailPipe, RelativeTimePipe, IconComponent],
  templateUrl: './deck-list.component.html',
  styleUrl: './deck-list.component.scss',
})
export class DeckListComponent implements OnInit {
  publicDecks: Deck[] = [];
  myDecks: Deck[] = [];
  teamDecks: Deck[] = [];

  search = '';
  filterFormat = '';
  filterRace = '';
  sort: SortKey = 'recent';

  activeTab: Tab = 'public';
  readonly pageSize = 20;

  // Pagination
  publicPage = 1;
  publicTotal = 0;
  minePage = 1;
  mineTotal = 0;
  teamPage = 1;
  teamTotal = 0;

  // Loading states (skeletons)
  loadingPublic = false;
  loadingMine = false;
  loadingTeam = false;

  // ===== Comparar mazos =====
  compareMode = false;
  selectedForCompare = new Set<number>();
  readonly MAX_COMPARE = 3;

  readonly skeletonRange = Array.from({ length: 6 });

  readonly sortOptions: { value: SortKey; label: string }[] = [
    { value: 'recent', label: 'Recientes' },
    { value: 'created', label: 'Creación' },
    { value: 'popular', label: 'Populares' },
    { value: 'cards', label: 'Más cartas' },
    { value: 'name', label: 'A â†’ Z' },
    { value: 'name_desc', label: 'Z â†’ A' },
  ];

  private readonly raceLabels: Record<string, string> = {
    dream: 'Dream', totem: 'Tótem', eterno: 'Eterno', faerie: 'Faerie',
    dragon: 'Dragón', sombra: 'Sombra', heroe: 'Héroe', sacerdote: 'Sacerdote',
    guerrero: 'Guerrero', bestia: 'Bestia', caballero: 'Caballero',
  };

  /** Color/acento por raza para el strip lateral de la tarjeta. */
  readonly raceAccents: Record<string, string> = {
    dream: '#7dd3fc',
    totem: '#a3e635',
    eterno: '#fbbf24',
    faerie: '#f472b6',
    dragon: '#ef4444',
    sombra: '#a855f7',
    heroe: '#f59e0b',
    sacerdote: '#e0e7ff',
    guerrero: '#dc2626',
    bestia: '#84cc16',
    caballero: '#60a5fa',
  };

  private readonly formatLabels: Record<string, string> = {
    imp: 'Imperial', fx: 'FX', esc: 'Escuelas Elementales', imp_r: 'Imperio Retro',
    pb: 'Primer Bloque', pe: 'Primera Era',
  };

  private readonly subFormatLabels: Record<string, string> = { vcr: 'VCR' };

  getRaceLabel(race?: string): string {
    if (!race) return 'Dream';
    return this.raceLabels[race] || race;
  }

  getRaceAccent(race?: string): string {
    return this.raceAccents[race || ''] || '#e94560';
  }

  getFormatLabel(format?: string): string {
    if (!format) return 'Imperial';
    return this.formatLabels[format] || format;
  }

  getSubFormatLabel(subFormat?: string): string {
    if (!subFormat) return subFormat || '';
    return this.subFormatLabels[subFormat] || subFormat;
  }

  /** Carta de portada (cover_card_detail si existe; si no, primera del cover_preview). */
  getCoverCard(deck: Deck): Card | null {
    if (deck.cover_card_detail) return deck.cover_card_detail;
    if (deck.cover_preview && deck.cover_preview.length > 0) return deck.cover_preview[0];
    return null;
  }

  /** Hasta 3 cartas para mosaico cuando no hay portada explícita. */
  getMosaic(deck: Deck): Card[] {
    if (deck.cover_card_detail) return [];
    return (deck.cover_preview || []).slice(0, 3);
  }

  /** ¿Hay algún filtro activo (excluye orden)? */
  get activeFilterCount(): number {
    let n = 0;
    if (this.search.trim()) n++;
    if (this.filterFormat) n++;
    if (this.filterRace) n++;
    return n;
  }

  constructor(
    public deckService: DeckService,
    public auth: AuthService,
    private cdr: ChangeDetectorRef,
    private router: Router,
    private titleService: Title,
  ) {}

  ngOnInit() {
    this.titleService.setTitle('Mazos â€” ShadowForge');
    this.loadPublicDecks();
    if (this.auth.isAuthenticated()) {
      this.loadMyDecks();
      this.loadTeamDecks();
    }
  }

  // â”€â”€ Loaders â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  loadPublicDecks() {
    this.loadingPublic = true;
    this.deckService.getPublicDecks(
      this.search || undefined,
      this.publicPage,
      this.filterFormat || undefined,
      this.filterRace || undefined,
      this.sort,
    ).subscribe({
      next: res => {
        this.publicDecks = res.results;
        this.publicTotal = res.count;
        this.loadingPublic = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loadingPublic = false; this.cdr.detectChanges(); },
    });
  }

  loadMyDecks() {
    this.loadingMine = true;
    this.deckService.getMyDecks(
      this.minePage,
      this.search || undefined,
      this.filterFormat || undefined,
      this.filterRace || undefined,
      this.sort,
    ).subscribe({
      next: res => {
        this.myDecks = res.results;
        this.mineTotal = res.count;
        this.loadingMine = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loadingMine = false; this.cdr.detectChanges(); },
    });
  }

  loadTeamDecks() {
    this.loadingTeam = true;
    this.deckService.getTeamDecks(
      this.teamPage,
      this.search || undefined,
      this.filterFormat || undefined,
      this.filterRace || undefined,
      this.sort,
    ).subscribe({
      next: (res) => {
        this.teamDecks = res.results;
        this.teamTotal = res.count;
        this.loadingTeam = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loadingTeam = false; this.cdr.detectChanges(); },
    });
  }

  /** Recargar la pestaña activa, reseteando a página 1. */
  private reloadActive() {
    if (this.activeTab === 'public') {
      this.publicPage = 1;
      this.loadPublicDecks();
    } else if (this.activeTab === 'mine') {
      this.minePage = 1;
      this.loadMyDecks();
    } else {
      this.teamPage = 1;
      this.loadTeamDecks();
    }
  }

  // â”€â”€ Pagination â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  get publicTotalPages(): number { return Math.max(1, Math.ceil(this.publicTotal / this.pageSize)); }
  get mineTotalPages(): number { return Math.max(1, Math.ceil(this.mineTotal / this.pageSize)); }
  get teamTotalPages(): number { return Math.max(1, Math.ceil(this.teamTotal / this.pageSize)); }

  publicNextPage() { if (this.publicPage < this.publicTotalPages) { this.publicPage++; this.loadPublicDecks(); } }
  publicPrevPage() { if (this.publicPage > 1) { this.publicPage--; this.loadPublicDecks(); } }
  mineNextPage() { if (this.minePage < this.mineTotalPages) { this.minePage++; this.loadMyDecks(); } }
  minePrevPage() { if (this.minePage > 1) { this.minePage--; this.loadMyDecks(); } }
  teamNextPage() { if (this.teamPage < this.teamTotalPages) { this.teamPage++; this.loadTeamDecks(); } }
  teamPrevPage() { if (this.teamPage > 1) { this.teamPage--; this.loadTeamDecks(); } }

  // â”€â”€ Filtering / Sorting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  onSearch() { this.reloadActive(); }
  onFilterChange() { this.reloadActive(); }
  onSortChange() { this.reloadActive(); }

  clearFilters() {
    if (!this.activeFilterCount) return;
    this.search = '';
    this.filterFormat = '';
    this.filterRace = '';
    this.reloadActive();
  }

  // â”€â”€ Tabs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  setTab(tab: Tab) {
    if (this.activeTab !== tab) {
      this.activeTab = tab;
      this.selectedForCompare.clear();
    }
  }

  // ── Actions ──
  deleteDeck(id: number) {
    if (confirm('¿Estás seguro de eliminar este mazo?')) {
      this.deckService.deleteDeck(id).subscribe(() => this.loadMyDecks());
    }
  }

  // ── Importar JSON ──
  importing = false;
  importMsg = '';

  triggerImport(input: HTMLInputElement) {
    input.value = '';
    input.click();
  }

  onImportFile(ev: Event) {
    const input = ev.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (file.size > 1_000_000) {
      this.importMsg = 'Archivo muy grande (máx. 1 MB).';
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      let payload: any;
      try {
        payload = JSON.parse(String(reader.result));
      } catch {
        this.importMsg = 'JSON inválido.';
        this.cdr.detectChanges();
        return;
      }
      this.importing = true;
      this.importMsg = '';
      this.deckService.importDeck(payload).subscribe({
        next: (res) => {
          this.importing = false;
          const msg = res.missing_myl_ids?.length
            ? `Importado con ${res.missing_myl_ids.length} carta(s) no encontrada(s).`
            : 'Mazo importado correctamente.';
          this.importMsg = msg;
          this.loadMyDecks();
          this.cdr.detectChanges();
          this.router.navigate(['/builder', res.id]);
        },
        error: (err) => {
          this.importing = false;
          this.importMsg = err?.error?.error || 'Error al importar el mazo.';
          this.cdr.detectChanges();
        },
      });
    };
    reader.readAsText(file);
  }

  // â”€â”€ Comparar mazos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  toggleCompareMode() {
    this.compareMode = !this.compareMode;
    if (!this.compareMode) this.selectedForCompare.clear();
  }

  isSelectedForCompare(id: number): boolean { return this.selectedForCompare.has(id); }

  toggleDeckCompare(event: Event, id: number) {
    event.preventDefault();
    event.stopPropagation();
    if (this.selectedForCompare.has(id)) {
      this.selectedForCompare.delete(id);
    } else {
      if (this.selectedForCompare.size >= this.MAX_COMPARE) return;
      this.selectedForCompare.add(id);
    }
  }

  startCompare() {
    if (this.selectedForCompare.size < 2) return;
    const ids = [...this.selectedForCompare].join(',');
    this.router.navigate(['/decks/compare'], { queryParams: { ids, source: this.activeTab } });
  }
}
