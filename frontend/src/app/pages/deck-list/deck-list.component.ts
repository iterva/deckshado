import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DeckService } from '../../services/deck.service';
import { AuthService } from '../../services/auth.service';
import { Deck } from '../../models';

@Component({
  selector: 'app-deck-list',
  standalone: true,
  imports: [RouterLink, FormsModule],
  templateUrl: './deck-list.component.html',
  styleUrl: './deck-list.component.scss',
})
export class DeckListComponent implements OnInit {
  publicDecks: Deck[] = [];
  myDecks: Deck[] = [];
  teamDecks: Deck[] = [];
  search = '';
  activeTab: 'public' | 'mine' | 'team' = 'public';

  private readonly raceLabels: Record<string, string> = {
    dream: 'Dream', totem: 'Tótem', eterno: 'Eterno', faerie: 'Faerie',
    dragon: 'Dragón', sombra: 'Sombra', heroe: 'Héroe', sacerdote: 'Sacerdote',
    guerrero: 'Guerrero', bestia: 'Bestia', caballero: 'Caballero',
  };

  private readonly formatLabels: Record<string, string> = {
    imp: 'Imperial', fx: 'FX',
  };

  private readonly subFormatLabels: Record<string, string> = {
    vcr: 'VCR',
  };

  getRaceLabel(race?: string): string {
    if (!race) return 'Dream';
    return this.raceLabels[race] || race;
  }

  getFormatLabel(format?: string): string {
    if (!format) return 'Imperial';
    return this.formatLabels[format] || format;
  }

  getSubFormatLabel(subFormat?: string): string {
    if (!subFormat) return subFormat || '';
    return this.subFormatLabels[subFormat] || subFormat;
  }

  constructor(public deckService: DeckService, public auth: AuthService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadPublicDecks();
    if (this.auth.isAuthenticated()) {
      this.loadMyDecks();
      this.loadTeamDecks();
    }
  }

  loadPublicDecks() {
    this.deckService.getPublicDecks(this.search || undefined).subscribe(res => {
      this.publicDecks = res.results;
      this.cdr.detectChanges();
    });
  }

  loadMyDecks() {
    this.deckService.getMyDecks().subscribe(res => {
      this.myDecks = res.results;
      this.cdr.detectChanges();
    });
  }

  loadTeamDecks() {
    this.deckService.getTeamDecks().subscribe({
      next: (res) => {
        this.teamDecks = res.results;
        this.cdr.detectChanges();
      },
      error: () => {},
    });
  }

  onSearch() {
    this.loadPublicDecks();
  }

  deleteDeck(id: number) {
    if (confirm('¿Estás seguro de eliminar este mazo?')) {
      this.deckService.deleteDeck(id).subscribe(() => this.loadMyDecks());
    }
  }
}
