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
  viewMode: 'grid' | 'list' = 'grid';
  groupedEntries: { type: string; total: number; entries: any[] }[] = [];
  groupedSideEntries: { type: string; total: number; entries: any[] }[] = [];
  previewCard: Card | null = null;
  previewAbility: string | null = null;
  exportOrientation: 'vertical' | 'horizontal' = 'vertical';
  exporting = false;
  @ViewChild('deckContent') deckContent!: ElementRef;
  private abilityCache = new Map<number, string>();

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private deckService: DeckService,
    private cardService: CardService,
    private auth: AuthService,
    private cdr: ChangeDetectorRef,
  ) {}

  get canCopy(): boolean {
    return this.auth.isAuthenticated();
  }

  copyDeck() {
    if (!this.deck) return;
    this.router.navigate(['/builder/new', 'imp'], {
      queryParams: this.deck.race ? { race: this.deck.race } : {},
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

  get formatLabel(): string {
    return 'Imperio';
  }

  get raceLabel(): string {
    if (!this.deck?.race) return '';
    const names: Record<string, string> = {
      dream: 'Dream', totem: 'Tótem', eterno: 'Eterno', faerie: 'Faerie',
      dragon: 'Dragón', sombra: 'Sombra', heroe: 'Héroe', sacerdote: 'Sacerdote',
      guerrero: 'Guerrero', bestia: 'Bestia', caballero: 'Caballero',
    };
    return names[this.deck.race] || this.deck.race;
  }

  get todayFormatted(): string {
    return new Date().toLocaleDateString('es-CL', { day: 'numeric', month: 'long', year: 'numeric' });
  }

  async exportImage() {
    if (!this.deckContent || this.exporting) return;
    this.exporting = true;
    this.cdr.detectChanges();
    try {
      const html2canvas = (await import('html2canvas')).default;
      const el = this.deckContent.nativeElement as HTMLElement;
      const canvas = await html2canvas(el, {
        backgroundColor: '#0f0f23',
        useCORS: true,
        allowTaint: true,
        scale: 2,
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
