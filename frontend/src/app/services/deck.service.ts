import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Deck, DeckEntry, PaginatedResponse } from '../models';

@Injectable({ providedIn: 'root' })
export class DeckService {
  private readonly apiUrl = `${environment.apiUrl}/decks`;

  constructor(private http: HttpClient) {}

  getPublicDecks(search?: string, page?: number, format?: string, race?: string): Observable<PaginatedResponse<Deck>> {
    let params: any = {};
    if (search) params.search = search;
    if (page) params.page = page;
    if (format) params.format = format;
    if (race) params.race = race;
    return this.http.get<PaginatedResponse<Deck>>(`${this.apiUrl}/public/`, { params });
  }

  getPublicDeck(id: number): Observable<Deck> {
    return this.http.get<Deck>(`${this.apiUrl}/public/${id}/`);
  }

  getTeamDecks(): Observable<PaginatedResponse<Deck>> {
    return this.http.get<PaginatedResponse<Deck>>(`${this.apiUrl}/team/`);
  }

  getTeamDeck(id: number): Observable<Deck> {
    return this.http.get<Deck>(`${this.apiUrl}/team/${id}/`);
  }

  getMyDecks(): Observable<PaginatedResponse<Deck>> {
    return this.http.get<PaginatedResponse<Deck>>(`${this.apiUrl}/my/`);
  }

  createDeck(data: { name: string; description?: string; is_public?: boolean }): Observable<Deck> {
    return this.http.post<Deck>(`${this.apiUrl}/my/`, data);
  }

  getDeck(id: number): Observable<Deck> {
    return this.http.get<Deck>(`${this.apiUrl}/my/${id}/`);
  }

  updateDeck(id: number, data: Partial<Deck>): Observable<Deck> {
    return this.http.patch<Deck>(`${this.apiUrl}/my/${id}/`, data);
  }

  deleteDeck(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/my/${id}/`);
  }

  addCardToDeck(deckId: number, cardId: number, quantity: number = 1): Observable<DeckEntry> {
    return this.http.post<DeckEntry>(`${this.apiUrl}/my/${deckId}/entries/`, {
      card_id: cardId,
      quantity,
    });
  }

  removeCardFromDeck(deckId: number, cardId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/my/${deckId}/entries/`, {
      body: { card_id: cardId },
    });
  }
}
