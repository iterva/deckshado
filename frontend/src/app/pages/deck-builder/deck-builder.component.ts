import { Component, OnInit, ChangeDetectorRef, ViewChild, ElementRef, HostListener, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime } from 'rxjs/operators';
import { CardService } from '../../services/card.service';
import { DeckService } from '../../services/deck.service';
import { AuthService } from '../../services/auth.service';
import { Card, Edition, CardType, DeckEntry, BanlistEntry, Rarity } from '../../models';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';
import { CanComponentDeactivate } from '../../guards/unsaved-changes.guard';

interface DeckCard {
  card: Card;
  quantity: number;
}

/**
 * Normaliza un nombre de carta para hacer comparaciones tolerantes:
 * - minúsculas
 * - sin acentos / diacríticos
 * - sin guiones, puntos ni signos de puntuación (los reemplaza por espacio)
 * - colapsa espacios múltiples
 * Esto permite que "Dragón Dorado" == "dragon dorado",
 * "Cienpies-SP" == "cienpies sp", etc., y que la banlist aplique
 * a todas las versiones de la carta.
 */
function normalizeName(name: string): string {
  if (!name) return '';
  return name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // strip accents
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

@Component({
  selector: 'app-deck-builder',
  standalone: true,
  imports: [FormsModule, RouterLink, ThumbnailPipe],
  templateUrl: './deck-builder.component.html',
  styleUrl: './deck-builder.component.scss',
})
export class DeckBuilderComponent implements OnInit {
  // Deck info
  deckId: number | null = null;
  deckName = '';
  deckDescription = '';
  deckIsPublic = true;
  sharedWithTeam = false;
  deckCards: DeckCard[] = [];
  sideCards: DeckCard[] = [];

  // Validation & toast
  toastMessage = '';
  toastType: 'error' | 'success' = 'error';
  toastVisible = false;
  private toastTimer: any = null;
  fieldErrors: { name?: boolean; cards?: boolean } = {};

  // UI flags
  /** Vista compacta del panel del mazo (lista densa sin imagen). */
  compactView = false;
  /** Set de IDs de cartas recién añadidas, para animar la entrada en el panel. */
  recentlyAdded = new Set<number>();
  /** Marca el panel del mazo cuando se añade una carta (pulse animation). */
  deckPanelPulse = false;

  // Autosave (#9)
  /** Indica si hay cambios sin guardar respecto al último save oficial. */
  hasUnsavedChanges = false;
  lastAutosavedAt: Date | null = null;
  private autosaveTimer: any = null;
  private readonly AUTOSAVE_KEY_PREFIX = 'deckshado_autosave_';

  // Hold-to-preview (#17): mantener el botón / dedo presionado abre el preview.
  private holdPreviewTimer: any = null;
  private readonly HOLD_DELAY_MS = 450;
  /** True cuando el preview se abrió por hold (para suprimir el "click" siguiente). */
  private holdTriggered = false;

  // Card browser
  availableCards: Card[] = [];
  editions: Edition[] = [];
  allEditions: Edition[] = [];
  types: CardType[] = [];
  allRarities: Rarity[] = [];
  search = '';
  abilitySearch = '';
  /** Texto único introducido por el usuario; se distribuye según `searchMode`. */
  searchQuery = '';
  /** Modo de búsqueda: por nombre, por habilidad, o ambos. */
  searchMode: 'name' | 'ability' | 'all' = 'name';
  /** Sets de filtros multi-selección. Vacío = sin filtro (= todos). */
  selectedTypes = new Set<string>();
  selectedEditions = new Set<string>();
  selectedRarities = new Set<string>();
  selectedCosts = new Set<string>();
  /** Compatibilidad: se siguen usando para serializar al backend (CSV). */
  selectedEdition = '';
  selectedType = '';
  selectedRarity = '';
  selectedCost = '';
  /** Estado de popovers de filtros. */
  openFilter: 'edition' | 'rarity' | 'cost' | null = null;
  selectedFormat = 'imp';
  formatName = 'Imperio';

  private readonly escEditionSlugs = [
    'bushido', 'sol-naciente',
    'dominio', 'contraataque', 'aguila-imperial', 'axis-mundi',
    'hijos-del-sol', 'legado-gotico', 'escuelas_elementales',
    'steampunk', 'heroes_de_dharma',
  ];
  currentPage = 1;
  totalCards = 0;
  loading = false;
  saving = false;

  // Banlist
  banlistEntries: BanlistEntry[] = [];
  /** card_name (lowercase) → BanlistEntry for quick lookup */
  banlistMap = new Map<string, BanlistEntry>();
  /** card_id → BanlistEntry for matched cards */
  banlistByCardId = new Map<number, BanlistEntry>();
  selectedSubFormat = 'racial';

  // Race restriction
  selectedRace = '';
  raceName = '';

  // Card preview popover
  previewCard = signal<Card | null>(null);
  previewAbility = signal<string | null>(null);
  /** Estado: cargando habilidad. */
  previewAbilityLoading = signal<boolean>(false);
  private abilityCache = new Map<number, string>();

  // Mobile deck panel toggle
  showDeckPanel = false;

  /** Subject para debounce del input de búsqueda. */
  private searchSubject = new Subject<void>();

  @ViewChild('searchInput') searchInput!: ElementRef<HTMLInputElement>;

  constructor(
    private cardService: CardService,
    private deckService: DeckService,
    private auth: AuthService,
    private route: ActivatedRoute,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    // Debounce de búsqueda en vivo (#21).
    this.searchSubject.pipe(debounceTime(300)).subscribe(() => this.onSearch());

    // Check authentication after a short delay to allow user loading
    setTimeout(() => {
      if (!this.auth.isAuthenticated()) {
        this.router.navigate(['/login']);
        return;
      }

      // Read format from route: /builder/new/:format or default 'imp'
      const fmt = this.route.snapshot.paramMap.get('format');
      if (fmt) {
        this.selectedFormat = fmt;
      }

      // Read race from query param
      const race = this.route.snapshot.queryParamMap.get('race');
      if (race) {
        this.selectedRace = race;
        const raceNames: Record<string, string> = {
          dream: 'Dream', totem: 'Tótem', eterno: 'Eterno', faerie: 'Faerie',
          dragon: 'Dragón', sombra: 'Sombra', heroe: 'Héroe', sacerdote: 'Sacerdote',
          guerrero: 'Guerrero', bestia: 'Bestia', caballero: 'Caballero',
          ancestral: 'Ancestral', barbaro: 'Bárbaro', samurai: 'Samurái', oni: 'Oni',
          'culto-tenebris': 'Culto Tenebris', 'vigilantes-etereos': 'Vigilantes Etéreos',
          'gremio-paladin': 'Gremio Paladín', 'clan-desafiante': 'Clan Desafiante',
          oscuridad: 'Oscuridad', luz: 'Luz',
        };
        this.raceName = raceNames[race] || race;
      }

      // Read sub_fmt from query param (vcr for VCR sub-format)
      const subFmt = this.route.snapshot.queryParamMap.get('sub_fmt');
      if (subFmt) {
        this.selectedSubFormat = subFmt;
      }

      this.cardService.getFormats().subscribe(formats => {
        const found = formats.find(f => f.code === this.selectedFormat);
        if (found) this.formatName = found.name;
        this.cdr.detectChanges();
      });

      this.cardService.getEditions().subscribe(d => {
        this.allEditions = d;
        this.filterEditions();
        this.cdr.detectChanges();
      });
      this.cardService.getTypes().subscribe(d => {
        this.types = d;
        this.cdr.detectChanges();
      });
      this.cardService.getRarities().subscribe(d => {
        this.allRarities = d;
        this.cdr.detectChanges();
      });
      this.loadBanlist();
      this.loadCards();

      const id = this.route.snapshot.paramMap.get('id');
      if (id && id !== 'new') {
        this.deckId = Number(id);
        this.loadDeck();
      } else {
        const copyFrom = history.state?.copyFrom;
        if (copyFrom) {
          this.loadFromCopy(copyFrom);
        }
      }
    }, 100);
  }

  private loadFromCopy(deck: any) {
    this.deckName = 'Copia de ' + (deck.name || '');
    this.deckDescription = deck.description || '';
    this.deckIsPublic = false;
    this.deckCards = (deck.entries || []).map((e: any) => ({
      card: e.card_detail,
      quantity: e.quantity,
    }));
    this.sideCards = (deck.sideboard_entries || []).map((e: any) => ({
      card: e.card_detail,
      quantity: e.quantity,
    }));

    if (deck.format) this.selectedFormat = deck.format;
    if (deck.sub_format) this.selectedSubFormat = deck.sub_format;
  }

  loadDeck() {
    if (!this.deckId) return;
    this.deckService.getDeck(this.deckId).subscribe({
      next: (deck) => {
        this.deckName = deck.name;
        this.deckDescription = deck.description;
        this.deckIsPublic = deck.is_public;
        this.sharedWithTeam = deck.shared_with_team || false;
        this.deckCards = (deck.entries || []).map(e => ({
          card: e.card_detail,
          quantity: e.quantity,
        }));
        this.sortDeckCards(this.deckCards);
        this.sideCards = (deck.sideboard_entries || []).map(e => ({
          card: e.card_detail,
          quantity: e.quantity,
        }));
        this.sortDeckCards(this.sideCards);

        // Restore format, sub_format and race from saved deck
        const needsReload =
          (deck.format && deck.format !== this.selectedFormat) ||
          (deck.sub_format && deck.sub_format !== this.selectedSubFormat) ||
          (deck.race && deck.race !== this.selectedRace);

        if (deck.format) {
          this.selectedFormat = deck.format;
        }
        if (deck.sub_format) {
          this.selectedSubFormat = deck.sub_format;
        }
        if (deck.race) {
          this.selectedRace = deck.race;
          const raceNames: Record<string, string> = {
            dream: 'Dream', totem: 'Tótem', eterno: 'Eterno', faerie: 'Faerie',
            dragon: 'Dragón', sombra: 'Sombra', heroe: 'Héroe', sacerdote: 'Sacerdote',
            guerrero: 'Guerrero', bestia: 'Bestia', caballero: 'Caballero',
            ancestral: 'Ancestral', barbaro: 'Bárbaro', samurai: 'Samurái', oni: 'Oni',
            'culto-tenebris': 'Culto Tenebris', 'vigilantes-etereos': 'Vigilantes Etéreos',
            'gremio-paladin': 'Gremio Paladín', 'clan-desafiante': 'Clan Desafiante',
            oscuridad: 'Oscuridad', luz: 'Luz',
          };
          this.raceName = raceNames[deck.race] || deck.race;
        }

        if (needsReload) {
          this.cardService.getFormats().subscribe(formats => {
            const found = formats.find(f => f.code === this.selectedFormat);
            if (found) this.formatName = found.name;
            this.cdr.detectChanges();
          });
          this.filterEditions();
          this.loadBanlist();
          this.loadCards();
        }
      },
      error: () => this.router.navigate(['/decks']),
    });
  }

  loadCards() {
    this.loading = true;
    this.cardService.getCards({
      search: this.search || undefined,
      ability_search: this.abilitySearch || undefined,
      edition: this.selectedEdition || undefined,
      type: this.selectedType || undefined,
      rarity: this.selectedRarity || undefined,
      cost: this.selectedCost || undefined,
      format: this.selectedFormat,
      page: this.currentPage,
      deck_race: this.selectedRace || undefined,
      sub_fmt: this.selectedSubFormat === 'vcr' ? 'vcr' : undefined,
    }).subscribe({
      next: (res) => {
        this.availableCards = res.results;
        this.totalCards = res.count;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  onSearch() {
    // Distribuir `searchQuery` en los campos según el modo seleccionado.
    const q = (this.searchQuery || '').trim();
    if (this.searchMode === 'name') {
      this.search = q;
      this.abilitySearch = '';
    } else if (this.searchMode === 'ability') {
      this.search = '';
      this.abilitySearch = q;
    } else {
      this.search = q;
      this.abilitySearch = q;
    }
    this.currentPage = 1;
    this.loadCards();
  }

  setSearchMode(mode: 'name' | 'ability' | 'all') {
    if (this.searchMode === mode) return;
    this.searchMode = mode;
    if ((this.searchQuery || '').trim()) {
      this.onSearch();
    }
  }

  /** Toggle de chip de tipo: si ya está activo lo quita. Vacío = todos. */
  toggleType(slug: string) {
    if (!slug) {
      // Click en "Todos": limpia la selección.
      this.selectedTypes.clear();
    } else if (this.selectedTypes.has(slug)) {
      this.selectedTypes.delete(slug);
    } else {
      this.selectedTypes.add(slug);
    }
    this.selectedType = [...this.selectedTypes].join(',');
    this.onFilterChange();
  }

  /** Toggle genérico para sets de multi-select (edición, rareza, coste). */
  toggleMulti(set: Set<string>, value: string) {
    if (set.has(value)) set.delete(value);
    else set.add(value);
    this.selectedEdition = [...this.selectedEditions].join(',');
    this.selectedRarity = [...this.selectedRarities].join(',');
    this.selectedCost = [...this.selectedCosts].join(',');
    this.onFilterChange();
  }

  clearMulti(which: 'edition' | 'rarity' | 'cost') {
    if (which === 'edition') { this.selectedEditions.clear(); this.selectedEdition = ''; }
    if (which === 'rarity') { this.selectedRarities.clear(); this.selectedRarity = ''; }
    if (which === 'cost') { this.selectedCosts.clear(); this.selectedCost = ''; }
    this.onFilterChange();
  }

  toggleFilterPopover(which: 'edition' | 'rarity' | 'cost', event?: MouseEvent) {
    event?.stopPropagation();
    this.openFilter = this.openFilter === which ? null : which;
  }

  closeFilterPopover() {
    this.openFilter = null;
  }

  @HostListener('document:click')
  onDocumentClick() {
    if (this.openFilter) this.openFilter = null;
  }

  @HostListener('document:keydown.escape')
  onEscape() {
    if (this.openFilter) this.openFilter = null;
  }

  filterLabel(which: 'edition' | 'rarity' | 'cost'): string {
    const set = which === 'edition' ? this.selectedEditions
      : which === 'rarity' ? this.selectedRarities
      : this.selectedCosts;
    if (set.size === 0) {
      return which === 'edition' ? 'Todas las ediciones'
        : which === 'rarity' ? 'Todas las rarezas'
        : 'Todos los costes';
    }
    if (set.size === 1) {
      const v = [...set][0];
      if (which === 'edition') return this.editions.find(e => e.slug === v)?.title || v;
      if (which === 'rarity') return this.filteredRarities.find(r => r.slug === v)?.name || v;
      return `Coste ${v}`;
    }
    return `${set.size} seleccionad${which === 'edition' ? 'as' : which === 'rarity' ? 'as' : 'os'}`;
  }

  onFilterChange() {
    this.currentPage = 1;
    this.loadCards();
  }

  filterEditions() {
    if (this.selectedFormat === 'esc') {
      this.editions = this.allEditions.filter(e => this.escEditionSlugs.includes(e.slug));
    } else {
      this.editions = this.allEditions.filter(e => e.format_code === this.selectedFormat);
    }
  }

  nextPage() {
    if (this.currentPage * 20 < this.totalCards) {
      this.currentPage++;
      this.loadCards();
    }
  }

  prevPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadCards();
    }
  }

  loadBanlist() {
    this.cardService.getBanlist(this.selectedFormat, this.selectedSubFormat).subscribe(entries => {
      this.banlistEntries = entries;
      this.banlistMap.clear();
      this.banlistByCardId.clear();
      for (const e of entries) {
        this.banlistMap.set(normalizeName(e.card_name), e);
        if (e.card_id) {
          this.banlistByCardId.set(e.card_id, e);
        }
      }
      this.cdr.detectChanges();
    });
  }

  onSubFormatChange() {
    this.currentPage = 1;
    this.selectedRarity = '';  // reset rarity filter since options change per sub-format
    this.loadBanlist();
    this.loadCards();
  }

  getBanStatus(card: Card): BanlistEntry | null {
    return this.banlistByCardId.get(card.id)
      || this.banlistMap.get(normalizeName(card.name))
      || null;
  }

  getMaxCopies(card: Card): number {
    const ban = this.getBanStatus(card);
    if (ban) return ban.max_copies;
    return card.is_unique ? 1 : 3;
  }

  /**
   * Effective max copies for a card name, considering ALL versions in the deck.
   * Takes the minimum of the card's own limit and the limits of versions already in deck.
   * e.g. if Cthulhu Promo (Única=1) is in deck, Cthulhu LEG also gets max=1.
   */
  getEffectiveMaxCopies(card: Card): number {
    let max = this.getMaxCopies(card);
    const key = normalizeName(card.name);
    for (const dc of this.deckCards) {
      if (normalizeName(dc.card.name) === key && dc.card.id !== card.id) {
        max = Math.min(max, this.getMaxCopies(dc.card));
      }
    }
    for (const dc of this.sideCards) {
      if (normalizeName(dc.card.name) === key && dc.card.id !== card.id) {
        max = Math.min(max, this.getMaxCopies(dc.card));
      }
    }
    return max;
  }

  /** Total copies across main + side for all cards sharing the same name. */
  getNameCount(name: string): number {
    const key = normalizeName(name);
    const mainCount = this.deckCards
      .filter(dc => normalizeName(dc.card.name) === key)
      .reduce((sum, dc) => sum + dc.quantity, 0);
    const sideCount = this.sideCards
      .filter(dc => normalizeName(dc.card.name) === key)
      .reduce((sum, dc) => sum + dc.quantity, 0);
    return mainCount + sideCount;
  }

  /** Check if a different version of this card name is already in main or side. */
  hasDifferentVersion(card: Card): boolean {
    const key = normalizeName(card.name);
    return this.deckCards.some(dc => normalizeName(dc.card.name) === key && dc.card.id !== card.id)
      || this.sideCards.some(dc => normalizeName(dc.card.name) === key && dc.card.id !== card.id);
  }

  /** Total copies of a specific card across main + side. */
  getTotalCopies(cardId: number): number {
    const mainQty = this.deckCards.find(dc => dc.card.id === cardId)?.quantity || 0;
    const sideQty = this.sideCards.find(dc => dc.card.id === cardId)?.quantity || 0;
    return mainQty + sideQty;
  }

  // --- Race restriction logic ---

  private readonly escMultiRace: Record<string, string[]> = {
    'culto-tenebris': ['sombra', 'oni'],
    'vigilantes-etereos': ['eterno', 'faerie'],
    'gremio-paladin': ['caballero', 'sacerdote'],
    'clan-desafiante': ['dragon', 'guerrero'],
  };

  private isRaceless(card: Card): boolean {
    return !card.race_name || card.race_name === 'Sin Raza';
  }

  private isAlly(card: Card): boolean {
    return card.type_name === 'Aliado';
  }

  private cardMatchesRace(card: Card, raceSlug: string): boolean {
    // Multi-race archetypes
    const multiRaces = this.escMultiRace[raceSlug];
    if (multiRaces) {
      return multiRaces.some(r => this.cardMatchesSingleRace(card, r));
    }
    // Ability-based: Luz / Oscuridad
    if (raceSlug === 'luz' || raceSlug === 'oscuridad') {
      const keyword = raceSlug === 'luz' ? 'Luz' : 'Oscuridad';
      if (card.ability) {
        const firstLine = card.ability.split('\n')[0];
        return firstLine.toLowerCase().startsWith(keyword.toLowerCase());
      }
      return false;
    }
    return this.cardMatchesSingleRace(card, raceSlug);
  }

  private cardMatchesSingleRace(card: Card, raceSlug: string): boolean {
    // Primary: match by slug (accent-safe)
    if (card.race_slug) {
      const rs = card.race_slug.toLowerCase();
      return rs === raceSlug || rs.includes(raceSlug);
    }
    // Fallback: match by name (for cached responses without race_slug)
    if (card.race_name) {
      const rn = card.race_name.toLowerCase();
      return rn.includes(raceSlug);
    }
    return false;
  }

  /** Count raceless allies across main + side. */
  getRacelessAllyCount(): number {
    const count = (list: DeckCard[]) => list
      .filter(dc => this.isAlly(dc.card) && this.isRaceless(dc.card))
      .reduce((sum, dc) => sum + dc.quantity, 0);
    return count(this.deckCards) + count(this.sideCards);
  }

  /** Check if a card is allowed by the selected race. */
  isCardAllowedByRace(card: Card): boolean {
    if (!this.selectedRace) return true;

    // Non-allies (Oro, Arma, Talismán, Tótem) are always allowed
    if (!this.isAlly(card)) return true;

    // Dream: all allies allowed
    if (this.selectedRace === 'dream') return true;

    // Tótem race: only raceless allies
    if (this.selectedRace === 'totem') {
      return this.isRaceless(card);
    }

    // Specific race: allies of that race are allowed
    if (this.cardMatchesRace(card, this.selectedRace)) return true;

    // Raceless allies: max 4 across main + side
    if (this.isRaceless(card)) {
      return this.getRacelessAllyCount() < 4;
    }

    // Different race ally: not allowed
    return false;
  }

  /** Filter card list to only show cards matching the selected race. */
  private filterByRace(cards: Card[]): Card[] {
    if (!this.selectedRace) return cards;

    return cards.filter(card => {
      // Non-allies always shown
      if (!this.isAlly(card)) return true;
      // Dream: show all
      if (this.selectedRace === 'dream') return true;
      // Tótem: only raceless allies
      if (this.selectedRace === 'totem') return this.isRaceless(card);
      // Specific race: show matching race + raceless
      return this.cardMatchesRace(card, this.selectedRace) || this.isRaceless(card);
    });
  }

  addCard(card: Card) {
    const maxQty = this.getEffectiveMaxCopies(card);
    if (maxQty === 0) return; // banned

    // Check combined total across main + side for all versions of this card name
    if (this.getNameCount(card.name) >= maxQty) return;

    // Main deck limit: 50 cards
    if (this.totalDeckCards >= 50) return;

    // Race restriction
    if (!this.isCardAllowedByRace(card)) return;

    const existing = this.deckCards.find(dc => dc.card.id === card.id);
    if (existing) {
      existing.quantity++;
    } else {
      this.deckCards.push({ card, quantity: 1 });
      this.sortDeckCards(this.deckCards);
    }
    this.flashRecentlyAdded(card.id);
    this.markDirty();
  }

  removeCard(cardId: number) {
    const idx = this.deckCards.findIndex(dc => dc.card.id === cardId);
    if (idx !== -1) {
      if (this.deckCards[idx].quantity > 1) {
        this.deckCards[idx].quantity--;
      } else {
        this.deckCards.splice(idx, 1);
      }
      this.markDirty();
    }
  }

  getQuantityInDeck(cardId: number): number {
    return this.deckCards.find(dc => dc.card.id === cardId)?.quantity || 0;
  }

  getQuantityInSide(cardId: number): number {
    return this.sideCards.find(dc => dc.card.id === cardId)?.quantity || 0;
  }

  addToSide(card: Card) {
    const maxQty = this.getEffectiveMaxCopies(card);
    if (maxQty === 0) return;
    if (this.getNameCount(card.name) >= maxQty) return;
    if (this.totalSideCards >= 15) return;
    if (!this.isCardAllowedByRace(card)) return;

    const existing = this.sideCards.find(dc => dc.card.id === card.id);
    if (existing) {
      existing.quantity++;
    } else {
      this.sideCards.push({ card, quantity: 1 });
      this.sortDeckCards(this.sideCards);
    }
    this.flashRecentlyAdded(card.id);
    this.markDirty();
  }

  removeFromSide(cardId: number) {
    const idx = this.sideCards.findIndex(dc => dc.card.id === cardId);
    if (idx !== -1) {
      if (this.sideCards[idx].quantity > 1) {
        this.sideCards[idx].quantity--;
      } else {
        this.sideCards.splice(idx, 1);
      }
      this.markDirty();
    }
  }

  get totalDeckCards(): number {
    return this.deckCards.reduce((sum, dc) => sum + dc.quantity, 0);
  }

  get totalSideCards(): number {
    return this.sideCards.reduce((sum, dc) => sum + dc.quantity, 0);
  }

  private readonly typeOrder = ['Oro', 'Aliado', 'Arma', 'Tótem', 'Talismán'];

  private sortDeckCards(arr: DeckCard[]) {
    arr.sort((a, b) => {
      const ai = this.typeOrder.indexOf(a.card.type_name ?? '');
      const bi = this.typeOrder.indexOf(b.card.type_name ?? '');
      const oa = ai === -1 ? this.typeOrder.length : ai;
      const ob = bi === -1 ? this.typeOrder.length : bi;
      return oa - ob;
    });
  }

  get typeCounts(): { label: string; count: number }[] {
    const order = this.typeOrder;
    const map: Record<string, number> = {};
    for (const dc of this.deckCards) {
      const t = dc.card.type_name || 'Otro';
      map[t] = (map[t] || 0) + dc.quantity;
    }
    return order.filter(t => map[t]).map(t => ({ label: t, count: map[t] }));
  }

  /**
   * Curva de coste: cantidad de cartas (no-Oro) por bucket de coste 0..6 y 7+.
   * Devuelve siempre los 8 buckets (con count 0 si no hay), para que el gráfico
   * mantenga su forma incluso en mazos pequeños.
   */
  get costCurve(): { label: string; count: number; pct: number }[] {
    const buckets = [0, 0, 0, 0, 0, 0, 0, 0]; // 0..6, 7+
    for (const dc of this.deckCards) {
      if (dc.card.type_name === 'Oro') continue;
      const raw = dc.card.cost;
      if (raw === null || raw === undefined || raw === '') continue;
      const n = Number(raw);
      if (!Number.isFinite(n)) continue;
      const idx = n >= 7 ? 7 : Math.max(0, Math.min(7, Math.floor(n)));
      buckets[idx] += dc.quantity;
    }
    const max = Math.max(1, ...buckets);
    return buckets.map((count, i) => ({
      label: i === 7 ? '7+' : String(i),
      count,
      pct: Math.round((count / max) * 100),
    }));
  }

  get hasAnyCost(): boolean {
    return this.costCurve.some(b => b.count > 0);
  }

  get totalPages(): number {
    return Math.ceil(this.totalCards / 20);
  }

  /** VCR only shows promo, real, vasallo, cortesano */
  private readonly vcrRaritySlugs = ['promo', 'real', 'vasallo', 'cortesano'];
  readonly costOptions = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'];

  get filteredRarities(): Rarity[] {
    if (this.selectedSubFormat === 'vcr') {
      return this.allRarities.filter(r => this.vcrRaritySlugs.includes(r.slug));
    }
    return this.allRarities;
  }

  showPreview(card: Card, event: MouseEvent) {
    event.stopPropagation();
    this.previewCard.set(card);
    // Fetch ability if not cached
    if (this.abilityCache.has(card.id)) {
      this.previewAbility.set(this.abilityCache.get(card.id) || null);
      this.previewAbilityLoading.set(false);
    } else {
      this.previewAbility.set(null);
      this.previewAbilityLoading.set(true);
      this.cardService.getCard(card.id).subscribe(detail => {
        const ability = detail.ability || null;
        this.abilityCache.set(card.id, ability || '');
        if (this.previewCard()?.id === card.id) {
          this.previewAbility.set(ability);
          this.previewAbilityLoading.set(false);
        }
      });
    }
  }

  hidePreview() {
    this.previewCard.set(null);
    this.previewAbility.set(null);
    this.previewAbilityLoading.set(false);
  }

  saveDeck() {
    this.fieldErrors = {};
    const errors: string[] = [];

    if (!this.deckName.trim()) {
      this.fieldErrors.name = true;
      errors.push('Tu mazo necesita un nombre');
    }
    if (this.deckCards.length === 0) {
      this.fieldErrors.cards = true;
      errors.push('Agrega al menos una carta al mazo');
    }

    if (errors.length) {
      this.showToast(errors.join('. '), 'error');
      return;
    }

    this.saving = true;

    const entries = this.deckCards.map(dc => ({
      card: dc.card.id,
      quantity: dc.quantity,
      is_sideboard: false,
    }));

    const sideEntries = this.sideCards.map(dc => ({
      card: dc.card.id,
      quantity: dc.quantity,
      is_sideboard: true,
    }));

    const data: any = {
      name: this.deckName,
      description: this.deckDescription,
      is_public: this.deckIsPublic,
      shared_with_team: this.sharedWithTeam,
      format: this.selectedFormat,
      sub_format: this.selectedSubFormat,
      race: this.selectedRace || '',
      entries: [...entries, ...sideEntries],
    };

    const obs = this.deckId
      ? this.deckService.updateDeck(this.deckId, data)
      : this.deckService.createDeck(data);

    obs.subscribe({
      next: (deck) => {
        this.saving = false;
        this.clearDraft();
        this.showToast('¡Mazo guardado exitosamente!', 'success');
        setTimeout(() => this.router.navigate(['/decks', deck.id]), 1200);
      },
      error: (err) => {
        this.saving = false;
        let msg = 'No se pudo guardar el mazo. Intenta de nuevo.';
        if (err.status === 401) {
          msg = 'Tu sesión expiró. Inicia sesión de nuevo.';
        } else if (err.status === 400 && err.error) {
          const detail = typeof err.error === 'object'
            ? Object.values(err.error).flat().join(', ')
            : String(err.error);
          msg = `Error en los datos: ${detail}`;
        } else if (err.status === 0) {
          msg = 'Sin conexión al servidor. Verifica que esté corriendo.';
        }
        this.showToast(msg, 'error');
        this.cdr.detectChanges();
      },
    });
  }

  showToast(message: string, type: 'error' | 'success' = 'error') {
    clearTimeout(this.toastTimer);
    this.toastMessage = message;
    this.toastType = type;
    this.toastVisible = true;
    this.cdr.detectChanges();
    this.toastTimer = setTimeout(() => {
      this.toastVisible = false;
      this.cdr.detectChanges();
    }, 5000);
  }

  toggleDeckPanel() {
    this.showDeckPanel = !this.showDeckPanel;
  }

  focusSearch() {
    this.showDeckPanel = false;
    this.searchInput.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => this.searchInput.nativeElement.focus(), 300);
  }

  // ====== #15 Vista compacta ======
  toggleCompactView() {
    this.compactView = !this.compactView;
  }

  // ====== #16 Agrupar entradas del mazo por tipo ======
  get groupedDeckCards(): { type: string; total: number; cards: DeckCard[] }[] {
    return this.buildGroups(this.deckCards);
  }

  get groupedSideCards(): { type: string; total: number; cards: DeckCard[] }[] {
    return this.buildGroups(this.sideCards);
  }

  private buildGroups(arr: DeckCard[]): { type: string; total: number; cards: DeckCard[] }[] {
    const map = new Map<string, { type: string; total: number; cards: DeckCard[] }>();
    for (const dc of arr) {
      const t = dc.card.type_name || 'Otro';
      if (!map.has(t)) map.set(t, { type: t, total: 0, cards: [] });
      const g = map.get(t)!;
      g.cards.push(dc);
      g.total += dc.quantity;
    }
    return [...map.values()].sort((a, b) => {
      const ai = this.typeOrder.indexOf(a.type);
      const bi = this.typeOrder.indexOf(b.type);
      const oa = ai === -1 ? this.typeOrder.length : ai;
      const ob = bi === -1 ? this.typeOrder.length : bi;
      return oa - ob;
    });
  }

  // ====== #21 Debounce de búsqueda en vivo ======
  onSearchInput() {
    this.searchSubject.next();
  }

  // ====== #17 Hold-to-preview (mantener click/touch) ======
  /** Inicia el timer al apretar el botón / dedo sobre la mini-card. */
  holdStart(card: Card, event: MouseEvent | TouchEvent) {
    // Solo botón izquierdo en mouse.
    if (event instanceof MouseEvent && event.button !== 0) return;
    this.cancelHold();
    this.holdTriggered = false;
    this.holdPreviewTimer = setTimeout(() => {
      this.holdTriggered = true;
      // Reusamos el mismo flujo que showPreview pero sin requerir el click.
      this.previewCard.set(card);
      if (this.abilityCache.has(card.id)) {
        this.previewAbility.set(this.abilityCache.get(card.id) || null);
        this.previewAbilityLoading.set(false);
      } else {
        this.previewAbility.set(null);
        this.previewAbilityLoading.set(true);
        this.cardService.getCard(card.id).subscribe(detail => {
          const ability = detail.ability || null;
          this.abilityCache.set(card.id, ability || '');
          if (this.previewCard()?.id === card.id) {
            this.previewAbility.set(ability);
            this.previewAbilityLoading.set(false);
          }
        });
      }
    }, this.HOLD_DELAY_MS);
  }

  /** Cancela el timer si se suelta antes del umbral. */
  holdEnd() {
    this.cancelHold();
  }

  /** Si el mouse sale de la carta, cancelamos también. */
  holdCancel() {
    this.cancelHold();
  }

  private cancelHold() {
    if (this.holdPreviewTimer) {
      clearTimeout(this.holdPreviewTimer);
      this.holdPreviewTimer = null;
    }
  }

  /** True si el último gesto fue un hold (usado para evitar que el ojito haga showPreview duplicado). */
  consumeHoldFlag(): boolean {
    const flag = this.holdTriggered;
    this.holdTriggered = false;
    return flag;
  }

  // ====== #20 Swipe-to-remove en deck-entry ======
  private swipeStartX: number | null = null;
  swipeOffset: Record<number, number> = {};

  onSwipeStart(event: TouchEvent, _cardId: number) {
    this.swipeStartX = event.touches[0].clientX;
  }

  onSwipeMove(event: TouchEvent, cardId: number) {
    if (this.swipeStartX === null) return;
    const dx = event.touches[0].clientX - this.swipeStartX;
    // Solo permitir swipe a la izquierda (dx negativo).
    this.swipeOffset[cardId] = Math.max(-160, Math.min(0, dx));
  }

  onSwipeEnd(cardId: number, side: 'main' | 'side') {
    const offset = this.swipeOffset[cardId] || 0;
    if (offset < -80) {
      if (side === 'main') this.removeCard(cardId);
      else this.removeFromSide(cardId);
    }
    delete this.swipeOffset[cardId];
    this.swipeStartX = null;
  }

  // ====== #12 Animaciones add/remove ======
  private flashRecentlyAdded(cardId: number) {
    this.recentlyAdded.add(cardId);
    this.deckPanelPulse = true;
    setTimeout(() => {
      this.recentlyAdded.delete(cardId);
      this.deckPanelPulse = false;
      this.cdr.detectChanges();
    }, 600);
  }

  // ====== #9 Auto-save en localStorage ======
  /** Marca el mazo como "sucio" y dispara autosave debounced. */
  markDirty() {
    this.hasUnsavedChanges = true;
    if (this.autosaveTimer) clearTimeout(this.autosaveTimer);
    this.autosaveTimer = setTimeout(() => this.saveDraft(), 1500);
  }

  private autosaveKey(): string {
    return this.AUTOSAVE_KEY_PREFIX + (this.deckId ?? 'new') + '_' + this.selectedFormat;
  }

  private saveDraft() {
    try {
      const payload = {
        deckName: this.deckName,
        deckDescription: this.deckDescription,
        deckIsPublic: this.deckIsPublic,
        sharedWithTeam: this.sharedWithTeam,
        selectedFormat: this.selectedFormat,
        selectedSubFormat: this.selectedSubFormat,
        selectedRace: this.selectedRace,
        deckCards: this.deckCards.map(dc => ({ cardId: dc.card.id, quantity: dc.quantity })),
        sideCards: this.sideCards.map(dc => ({ cardId: dc.card.id, quantity: dc.quantity })),
        savedAt: new Date().toISOString(),
      };
      localStorage.setItem(this.autosaveKey(), JSON.stringify(payload));
      this.lastAutosavedAt = new Date();
      this.cdr.detectChanges();
    } catch {
      // localStorage puede fallar en modo privado; no rompemos la UX.
    }
  }

  loadDraft(): boolean {
    try {
      const raw = localStorage.getItem(this.autosaveKey());
      if (!raw) return false;
      const data = JSON.parse(raw);
      // Solo restaurar si el usuario confirma.
      if (!confirm('Hay un borrador local sin guardar. ¿Quieres restaurarlo?')) {
        localStorage.removeItem(this.autosaveKey());
        return false;
      }
      this.deckName = data.deckName ?? '';
      this.deckDescription = data.deckDescription ?? '';
      this.deckIsPublic = !!data.deckIsPublic;
      this.sharedWithTeam = !!data.sharedWithTeam;
      // Las cartas se rehidratan tras cargar el listado de cartas (no podemos cargar Card completos desde el storage)
      // Para simplificar, solo restauramos los IDs y los re-pedimos:
      const ids = [...data.deckCards.map((d: any) => d.cardId), ...data.sideCards.map((d: any) => d.cardId)];
      if (ids.length > 0) {
        // Cargar cartas individuales y armar los arrays.
        Promise.all(ids.map(id => this.cardService.getCard(id).toPromise())).then(cards => {
          const byId = new Map<number, any>();
          for (const c of cards) if (c) byId.set(c.id, c);
          this.deckCards = data.deckCards
            .map((d: any) => ({ card: byId.get(d.cardId), quantity: d.quantity }))
            .filter((d: any) => d.card);
          this.sideCards = data.sideCards
            .map((d: any) => ({ card: byId.get(d.cardId), quantity: d.quantity }))
            .filter((d: any) => d.card);
          this.sortDeckCards(this.deckCards);
          this.sortDeckCards(this.sideCards);
          this.cdr.detectChanges();
        });
      }
      return true;
    } catch {
      return false;
    }
  }

  private clearDraft() {
    try { localStorage.removeItem(this.autosaveKey()); } catch {}
    this.lastAutosavedAt = null;
    this.hasUnsavedChanges = false;
  }

  /** Texto humano "Guardado hace 5s" para mostrar en la UI. */
  get autosaveLabel(): string {
    if (!this.lastAutosavedAt) return '';
    const diff = Math.round((Date.now() - this.lastAutosavedAt.getTime()) / 1000);
    if (diff < 5) return 'Borrador guardado';
    if (diff < 60) return `Borrador guardado hace ${diff}s`;
    const m = Math.round(diff / 60);
    return `Borrador guardado hace ${m}m`;
  }

  // ====== #10 CanDeactivate ======
  canDeactivate(): boolean {
    if (!this.hasUnsavedChanges) return true;
    return confirm('Hay cambios sin guardar en tu mazo. ¿Salir de todas formas?');
  }

  @HostListener('window:beforeunload', ['$event'])
  beforeUnload(e: BeforeUnloadEvent) {
    if (this.hasUnsavedChanges) {
      e.preventDefault();
      e.returnValue = '';
    }
  }
}
