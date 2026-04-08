import { Component, OnInit, ChangeDetectorRef, ViewChild, ElementRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CardService } from '../../services/card.service';
import { DeckService } from '../../services/deck.service';
import { AuthService } from '../../services/auth.service';
import { Card, Edition, CardType, DeckEntry, BanlistEntry } from '../../models';

interface DeckCard {
  card: Card;
  quantity: number;
}

@Component({
  selector: 'app-deck-builder',
  standalone: true,
  imports: [FormsModule, RouterLink],
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

  // Card browser
  availableCards: Card[] = [];
  editions: Edition[] = [];
  allEditions: Edition[] = [];
  types: CardType[] = [];
  search = '';
  selectedEdition = '';
  selectedType = '';
  selectedFormat = 'imp';
  formatName = 'Imperio';
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
  previewCard: Card | null = null;
  previewAbility: string | null = null;
  private abilityCache = new Map<number, string>();

  // Mobile deck panel toggle
  showDeckPanel = false;

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
        };
        this.raceName = raceNames[race] || race;
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
        this.sideCards = (deck.sideboard_entries || []).map(e => ({
          card: e.card_detail,
          quantity: e.quantity,
        }));
      },
      error: () => this.router.navigate(['/decks']),
    });
  }

  loadCards() {
    this.loading = true;
    this.cardService.getCards({
      search: this.search || undefined,
      edition: this.selectedEdition || undefined,
      type: this.selectedType || undefined,
      format: this.selectedFormat,
      page: this.currentPage,
      deck_race: this.selectedRace || undefined,
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
    this.currentPage = 1;
    this.loadCards();
  }

  onFilterChange() {
    this.currentPage = 1;
    this.loadCards();
  }

  filterEditions() {
    this.editions = this.allEditions.filter(e => e.format_code === this.selectedFormat);
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
        this.banlistMap.set(e.card_name.toLowerCase(), e);
        if (e.card_id) {
          this.banlistByCardId.set(e.card_id, e);
        }
      }
      this.cdr.detectChanges();
    });
  }

  onSubFormatChange() {
    this.loadBanlist();
  }

  getBanStatus(card: Card): BanlistEntry | null {
    return this.banlistByCardId.get(card.id)
      || this.banlistMap.get(card.name.toLowerCase())
      || null;
  }

  getMaxCopies(card: Card): number {
    const ban = this.getBanStatus(card);
    if (ban) return ban.max_copies;
    return card.is_unique ? 1 : 3;
  }

  /** Total copies across main + side for all cards sharing the same name. */
  getNameCount(name: string): number {
    const lower = name.toLowerCase();
    const mainCount = this.deckCards
      .filter(dc => dc.card.name.toLowerCase() === lower)
      .reduce((sum, dc) => sum + dc.quantity, 0);
    const sideCount = this.sideCards
      .filter(dc => dc.card.name.toLowerCase() === lower)
      .reduce((sum, dc) => sum + dc.quantity, 0);
    return mainCount + sideCount;
  }

  /** Check if a different version of this card name is already in main or side. */
  hasDifferentVersion(card: Card): boolean {
    const lower = card.name.toLowerCase();
    return this.deckCards.some(dc => dc.card.name.toLowerCase() === lower && dc.card.id !== card.id)
      || this.sideCards.some(dc => dc.card.name.toLowerCase() === lower && dc.card.id !== card.id);
  }

  /** Total copies of a specific card across main + side. */
  getTotalCopies(cardId: number): number {
    const mainQty = this.deckCards.find(dc => dc.card.id === cardId)?.quantity || 0;
    const sideQty = this.sideCards.find(dc => dc.card.id === cardId)?.quantity || 0;
    return mainQty + sideQty;
  }

  // --- Race restriction logic ---

  private isRaceless(card: Card): boolean {
    return !card.race_name || card.race_name === 'Sin Raza';
  }

  private isAlly(card: Card): boolean {
    return card.type_name === 'Aliado';
  }

  private cardMatchesRace(card: Card, raceSlug: string): boolean {
    if (!card.race_slug) return false;
    const rs = card.race_slug.toLowerCase();
    return rs === raceSlug || rs.includes(raceSlug);
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
    const maxQty = this.getMaxCopies(card);
    if (maxQty === 0) return; // banned

    // Rule: only one version of a card name allowed
    if (this.hasDifferentVersion(card)) return;

    // Check combined total across main + side
    if (this.getTotalCopies(card.id) >= maxQty) return;

    // Main deck limit: 50 cards
    if (this.totalDeckCards >= 50) return;

    // Race restriction
    if (!this.isCardAllowedByRace(card)) return;

    const existing = this.deckCards.find(dc => dc.card.id === card.id);
    if (existing) {
      existing.quantity++;
    } else {
      this.deckCards.push({ card, quantity: 1 });
    }
  }

  removeCard(cardId: number) {
    const idx = this.deckCards.findIndex(dc => dc.card.id === cardId);
    if (idx !== -1) {
      if (this.deckCards[idx].quantity > 1) {
        this.deckCards[idx].quantity--;
      } else {
        this.deckCards.splice(idx, 1);
      }
    }
  }

  getQuantityInDeck(cardId: number): number {
    return this.deckCards.find(dc => dc.card.id === cardId)?.quantity || 0;
  }

  getQuantityInSide(cardId: number): number {
    return this.sideCards.find(dc => dc.card.id === cardId)?.quantity || 0;
  }

  addToSide(card: Card) {
    const maxQty = this.getMaxCopies(card);
    if (maxQty === 0) return;
    if (this.hasDifferentVersion(card)) return;
    if (this.getTotalCopies(card.id) >= maxQty) return;
    if (this.totalSideCards >= 15) return;
    if (!this.isCardAllowedByRace(card)) return;

    const existing = this.sideCards.find(dc => dc.card.id === card.id);
    if (existing) {
      existing.quantity++;
    } else {
      this.sideCards.push({ card, quantity: 1 });
    }
  }

  removeFromSide(cardId: number) {
    const idx = this.sideCards.findIndex(dc => dc.card.id === cardId);
    if (idx !== -1) {
      if (this.sideCards[idx].quantity > 1) {
        this.sideCards[idx].quantity--;
      } else {
        this.sideCards.splice(idx, 1);
      }
    }
  }

  get totalDeckCards(): number {
    return this.deckCards.reduce((sum, dc) => sum + dc.quantity, 0);
  }

  get totalSideCards(): number {
    return this.sideCards.reduce((sum, dc) => sum + dc.quantity, 0);
  }

  get totalPages(): number {
    return Math.ceil(this.totalCards / 20);
  }

  showPreview(card: Card, event: MouseEvent) {
    event.stopPropagation();
    this.previewCard = card;
    // Fetch ability if not cached
    if (this.abilityCache.has(card.id)) {
      this.previewAbility = this.abilityCache.get(card.id) || null;
      this.cdr.detectChanges();
    } else {
      this.previewAbility = null;
      this.cdr.detectChanges();
      this.cardService.getCard(card.id).subscribe(detail => {
        const ability = detail.ability || null;
        this.abilityCache.set(card.id, ability || '');
        if (this.previewCard?.id === card.id) {
          this.previewAbility = ability;
          this.cdr.detectChanges();
        }
      });
    }
  }

  hidePreview() {
    this.previewCard = null;
    this.previewAbility = null;
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
      race: this.selectedRace || '',
      entries: [...entries, ...sideEntries],
    };

    const obs = this.deckId
      ? this.deckService.updateDeck(this.deckId, data)
      : this.deckService.createDeck(data);

    obs.subscribe({
      next: (deck) => {
        this.saving = false;
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
}
