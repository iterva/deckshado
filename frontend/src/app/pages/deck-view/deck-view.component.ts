import { Component, OnInit, ChangeDetectorRef, ElementRef, ViewChild } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DeckService } from '../../services/deck.service';
import { CardService } from '../../services/card.service';
import { AuthService } from '../../services/auth.service';
import { Deck, Card } from '../../models';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';

@Component({
  selector: 'app-deck-view',
  standalone: true,
  imports: [RouterLink, FormsModule, ThumbnailPipe],
  templateUrl: './deck-view.component.html',
  styleUrl: './deck-view.component.scss',
})
export class DeckViewComponent implements OnInit {
  deck: Deck | null = null;
  loading = true;
  viewMode: 'grid' | 'list' | 'stats' = 'grid';
  groupedEntries: { type: string; total: number; entries: any[] }[] = [];
  groupedSideEntries: { type: string; total: number; entries: any[] }[] = [];
  previewCard: Card | null = null;
  previewAbility: string | null = null;
  exportOrientation: 'vertical' | 'horizontal' = 'vertical';
  exporting = false;
  @ViewChild('deckContent') deckContent!: ElementRef;
  private abilityCache = new Map<number, string>();

  // Hand simulator
  handCards: Card[] = [];
  handSize = 0;
  handActive = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private deckService: DeckService,
    private cardService: CardService,
    private auth: AuthService,
    private cdr: ChangeDetectorRef,
  ) {}

  get isOwner(): boolean {
    const user = this.auth.user();
    return !!user && !!this.deck && user.username === this.deck.owner_username;
  }

  get canCopy(): boolean {
    return this.auth.isAuthenticated();
  }

  editDeck() {
    if (this.deck) {
      this.router.navigate(['/builder', this.deck.id]);
    }
  }

  deleteDeck() {
    if (!this.deck) return;
    if (!confirm('¿Estás seguro de que quieres eliminar este mazo?')) return;
    this.deckService.deleteDeck(this.deck.id).subscribe({
      next: () => this.router.navigate(['/decks']),
      error: (err: any) => console.error('Error eliminando mazo:', err),
    });
  }

  copyDeck() {
    if (!this.deck) return;
    const fmt = this.deck.format || 'imp';
    const qp: any = {};
    if (this.deck.race) qp.race = this.deck.race;
    if (this.deck.sub_format && this.deck.sub_format !== 'racial') qp.sub_fmt = this.deck.sub_format;
    this.router.navigate(['/builder/new', fmt], {
      queryParams: qp,
      state: { copyFrom: this.deck },
    });
  }

  private readonly typeOrder: Record<string, number> = {
    'Oro': 0, 'Aliado': 1, 'Talismán': 2, 'Arma': 3, 'Tótem': 4,
  };

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    const loadDeck = (deck: Deck) => {
      this.deck = deck;
      this.sortEntries();
      this.buildGroups();
      this.loading = false;
      this.preloadImages();
    };
    // Try owner endpoint first if authenticated, then team, then public
    if (this.auth.isAuthenticated()) {
      this.deckService.getDeck(id).subscribe({
        next: loadDeck,
        error: () => {
          this.deckService.getTeamDeck(id).subscribe({
            next: loadDeck,
            error: () => {
              this.deckService.getPublicDeck(id).subscribe({
                next: loadDeck,
                error: () => this.loading = false,
              });
            },
          });
        },
      });
    } else {
      this.deckService.getPublicDeck(id).subscribe({
        next: loadDeck,
        error: () => this.loading = false,
      });
    }
  }

  private sortEntries() {
    if (!this.deck?.entries) return;
    this.deck.entries.sort((a, b) => {
      const typeA = this.typeOrder[a.card_detail.type_name ?? ''] ?? 99;
      const typeB = this.typeOrder[b.card_detail.type_name ?? ''] ?? 99;
      if (typeA !== typeB) return typeA - typeB;
      return b.quantity - a.quantity;
    });
    if (this.deck.sideboard_entries) {
      this.deck.sideboard_entries.sort((a, b) => {
        const typeA = this.typeOrder[a.card_detail.type_name ?? ''] ?? 99;
        const typeB = this.typeOrder[b.card_detail.type_name ?? ''] ?? 99;
        if (typeA !== typeB) return typeA - typeB;
        return b.quantity - a.quantity;
      });
    }
  }

  private buildGroups() {
    if (!this.deck?.entries) return;
    const map = new Map<string, { type: string; total: number; entries: any[] }>();
    for (const entry of this.deck.entries) {
      const type = entry.card_detail.type_name ?? 'Otro';
      if (!map.has(type)) {
        map.set(type, { type, total: 0, entries: [] });
      }
      const group = map.get(type)!;
      group.entries.push(entry);
      group.total += entry.quantity;
    }
    // Sort groups by typeOrder
    this.groupedEntries = [...map.values()].sort(
      (a, b) => (this.typeOrder[a.type] ?? 99) - (this.typeOrder[b.type] ?? 99)
    );

    // Build sideboard groups
    if (this.deck.sideboard_entries) {
      const sideMap = new Map<string, { type: string; total: number; entries: any[] }>();
      for (const entry of this.deck.sideboard_entries) {
        const type = entry.card_detail.type_name ?? 'Otro';
        if (!sideMap.has(type)) {
          sideMap.set(type, { type, total: 0, entries: [] });
        }
        const group = sideMap.get(type)!;
        group.entries.push(entry);
        group.total += entry.quantity;
      }
      this.groupedSideEntries = [...sideMap.values()].sort(
        (a, b) => (this.typeOrder[a.type] ?? 99) - (this.typeOrder[b.type] ?? 99)
      );
    }
  }

  getRange(n: number): number[] {
    return Array.from({ length: n }, (_, i) => i);
  }

  /**
   * Curva de coste del mazo principal (excluye Oros y cartas sin coste).
   * Buckets 0..6 + 7+; siempre devuelve los 8 buckets para mantener forma.
   */
  get costCurve(): { label: string; count: number; pct: number }[] {
    const buckets = [0, 0, 0, 0, 0, 0, 0, 0];
    if (this.deck?.entries) {
      for (const entry of this.deck.entries) {
        const card = entry.card_detail;
        if (card.type_name === 'Oro') continue;
        const raw = card.cost;
        if (raw === null || raw === undefined || raw === '') continue;
        const n = Number(raw);
        if (!Number.isFinite(n)) continue;
        const idx = n >= 7 ? 7 : Math.max(0, Math.min(7, Math.floor(n)));
        buckets[idx] += entry.quantity;
      }
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

  /** Promedio de coste de cartas no-Oro con coste definido. */
  get avgCost(): number {
    let sum = 0;
    let n = 0;
    if (this.deck?.entries) {
      for (const entry of this.deck.entries) {
        const card = entry.card_detail;
        if (card.type_name === 'Oro') continue;
        const raw = card.cost;
        if (raw === null || raw === undefined || raw === '') continue;
        const v = Number(raw);
        if (!Number.isFinite(v)) continue;
        sum += v * entry.quantity;
        n += entry.quantity;
      }
    }
    return n === 0 ? 0 : Math.round((sum / n) * 10) / 10;
  }

  showPreview(card: Card, event: MouseEvent) {
    event.stopPropagation();
    this.previewCard = card;
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

  /** Flat list of cards expanded by quantity (for horizontal export) */
  get expandedEntries(): Card[] {
    if (!this.deck?.entries) return [];
    const cards: Card[] = [];
    for (const entry of this.deck.entries) {
      for (let i = 0; i < entry.quantity; i++) {
        cards.push(entry.card_detail);
      }
    }
    return cards;
  }

  get expandedSideEntries(): Card[] {
    if (!this.deck?.sideboard_entries) return [];
    const cards: Card[] = [];
    for (const entry of this.deck.sideboard_entries) {
      for (let i = 0; i < entry.quantity; i++) {
        cards.push(entry.card_detail);
      }
    }
    return cards;
  }

  private readonly formatNames: Record<string, string> = {
    imp: 'Imperio', esc: 'Escuelas Elementales', imp_r: 'Imperio Retro',
  };

  get formatLabel(): string {
    const base = this.formatNames[this.deck?.format || 'imp'] || 'Imperio';
    if (this.deck?.sub_format === 'vcr') return base + ' · VCR';
    return base;
  }

  get raceLabel(): string {
    if (!this.deck?.race) return '';
    const names: Record<string, string> = {
      dream: 'Dream', totem: 'Tótem', eterno: 'Eterno', faerie: 'Faerie',
      dragon: 'Dragón', sombra: 'Sombra', heroe: 'Héroe', sacerdote: 'Sacerdote',
      guerrero: 'Guerrero', bestia: 'Bestia', caballero: 'Caballero',
      ancestral: 'Ancestral', barbaro: 'Bárbaro', samurai: 'Samurái', oni: 'Oni',
      'culto-tenebris': 'Culto Tenebris', 'vigilantes-etereos': 'Vigilantes Etéreos',
      'gremio-paladin': 'Gremio Paladín', 'clan-desafiante': 'Clan Desafiante',
      oscuridad: 'Oscuridad', luz: 'Luz',
    };
    return names[this.deck.race] || this.deck.race;
  }

  get todayFormatted(): string {
    return new Date().toLocaleDateString('es-CL', { day: 'numeric', month: 'long', year: 'numeric' });
  }

  private thumbPipe = new ThumbnailPipe();

  // ── Hand Simulator ──

  /** Build a flat pool of cards expanded by quantity (main deck only) */
  private get cardPool(): Card[] {
    if (!this.deck?.entries) return [];
    const pool: Card[] = [];
    for (const entry of this.deck.entries) {
      for (let i = 0; i < entry.quantity; i++) {
        pool.push(entry.card_detail);
      }
    }
    return pool;
  }

  /** Pool without the starting gold (it starts on the field, never drawn). */
  private get shufflePool(): Card[] {
    const sgId = this.deck?.starting_gold;
    if (!sgId) return this.cardPool;
    const pool = this.cardPool;
    // Remove exactly one copy of the starting gold from the pool
    const idx = pool.findIndex(c => c.id === sgId);
    if (idx !== -1) pool.splice(idx, 1);
    return pool;
  }

  /** The starting gold Card object, if set and present in the deck. */
  get startingGoldCard(): Card | null {
    const sgId = this.deck?.starting_gold;
    if (!sgId || !this.deck?.entries) return null;
    const entry = this.deck.entries.find(e => e.card_detail.id === sgId);
    return entry ? entry.card_detail : null;
  }

  /** Fisher-Yates shuffle and take n */
  private drawRandom(pool: Card[], n: number): Card[] {
    const arr = [...pool];
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr.slice(0, Math.min(n, arr.length));
  }

  drawHand() {
    this.handSize = 8;
    this.handCards = this.drawRandom(this.shufflePool, 8);
    this.handActive = true;
  }

  mulligan() {
    if (this.handSize <= 1) return;
    this.handSize--;
    this.handCards = this.drawRandom(this.shufflePool, this.handSize);
  }

  resetHand() {
    this.handSize = 8;
    this.handCards = this.drawRandom(this.shufflePool, 8);
  }

  /** Preload card images in background so they're cached for viewing & export */
  private preloadImages() {
    if (!this.deck) return;
    const urls = new Set<string>();
    const allEntries = [...(this.deck.entries || []), ...(this.deck.sideboard_entries || [])];
    for (const entry of allEntries) {
      const url = entry.card_detail.image_url;
      if (url) {
        urls.add(this.thumbPipe.transform(url, 250)); // grid view
        urls.add(this.thumbPipe.transform(url, 350)); // export
      }
    }
    for (const url of urls) {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.src = url;
    }
  }

  async exportImage() {
    if (!this.deckContent || this.exporting) return;
    this.exporting = true;
    this.cdr.detectChanges();
    try {
      // Preload all images in the export area before capturing
      const el = this.deckContent.nativeElement as HTMLElement;
      const imgs = Array.from(el.querySelectorAll('img')) as HTMLImageElement[];
      await Promise.all(imgs.map(img => {
        if (img.complete && img.naturalWidth > 0) return Promise.resolve();
        return new Promise<void>((resolve) => {
          img.onload = () => resolve();
          img.onerror = () => resolve(); // don't block on broken images
          // Force load by reassigning src (handles lazy images)
          img.loading = 'eager';
          img.src = img.src;
        });
      }));

      const html2canvas = (await import('html2canvas')).default;
      // Fixed scale: always 2x regardless of device pixel ratio
      // This ensures the same output on mobile, 1080p, and 4K screens
      const canvas = await html2canvas(el, {
        backgroundColor: '#0f0f23',
        useCORS: true,
        allowTaint: true,
        scale: 2,
        windowWidth: el.scrollWidth,
        windowHeight: el.scrollHeight,
      });
      const link = document.createElement('a');
      link.download = `${this.deck?.name || 'mazo'}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (e) {
      console.error('Error exporting image:', e);
    }
    this.exporting = false;
    this.cdr.detectChanges();
  }
}
