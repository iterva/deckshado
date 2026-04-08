import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CardService } from '../../services/card.service';
import { DeckService } from '../../services/deck.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent implements OnInit {
  totalCards: number | null = null;
  totalDecks: number | null = null;

  constructor(private cardService: CardService, private deckService: DeckService) {}

  ngOnInit() {
    this.cardService.getCards({ page: 1 }).subscribe(res => this.totalCards = res.count);
    this.deckService.getPublicDecks().subscribe(res => this.totalDecks = res.count);
  }
}
