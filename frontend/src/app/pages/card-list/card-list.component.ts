import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CardService } from '../../services/card.service';
import { Card, Edition, CardType, Race, Rarity } from '../../models';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';

@Component({
  selector: 'app-card-list',
  standalone: true,
  imports: [FormsModule, ThumbnailPipe],
  templateUrl: './card-list.component.html',
  styleUrl: './card-list.component.scss',
})
export class CardListComponent implements OnInit {
  cards: Card[] = [];
  editions: Edition[] = [];
  types: CardType[] = [];
  races: Race[] = [];
  rarities: Rarity[] = [];

  search = '';
  selectedEdition = '';
  selectedType = '';
  selectedRace = '';
  selectedRarity = '';

  totalCards = 0;
  currentPage = 1;
  loading = false;
  selectedCard: Card | null = null;
  viewMode: 'grid' | 'table' = 'grid';

  constructor(private cardService: CardService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadFilters();
    this.loadCards();
  }

  loadFilters() {
    this.cardService.getEditions().subscribe(d => { this.editions = d; this.cdr.detectChanges(); });
    this.cardService.getTypes().subscribe(d => { this.types = d; this.cdr.detectChanges(); });
    this.cardService.getRaces().subscribe(d => { this.races = d; this.cdr.detectChanges(); });
    this.cardService.getRarities().subscribe(d => { this.rarities = d; this.cdr.detectChanges(); });
  }

  loadCards() {
    this.loading = true;
    this.cardService.getCards({
      search: this.search || undefined,
      edition: this.selectedEdition || undefined,
      type: this.selectedType || undefined,
      race: this.selectedRace || undefined,
      rarity: this.selectedRarity || undefined,
      page: this.currentPage,
    }).subscribe({
      next: (res) => {
        this.cards = res.results;
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

  selectCard(card: Card) {
    this.selectedCard = this.selectedCard?.id === card.id ? null : card;
  }

  get totalPages(): number {
    return Math.ceil(this.totalCards / 20);
  }
}
