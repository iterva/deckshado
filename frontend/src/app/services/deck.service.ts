import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Deck, DeckEntry, PaginatedResponse } from '../models';

@Injectable({ providedIn: 'root' })
export class DeckService {
  private readonly apiUrl = `${environment.apiUrl}/decks`;

  constructor(private http: HttpClient) {}

  getPublicDecks(search?: string, page?: number, format?: string, race?: string, ordering?: string): Observable<PaginatedResponse<Deck>> {
    let params: any = {};
    if (search) params.search = search;
    if (page) params.page = page;
    if (format) params.format = format;
    if (race) params.race = race;
    if (ordering) params.ordering = ordering;
    return this.http.get<PaginatedResponse<Deck>>(`${this.apiUrl}/public/`, { params });
  }

  getPublicDeck(id: number): Observable<Deck> {
    return this.http.get<Deck>(`${this.apiUrl}/public/${id}/`);
  }

  getTeamDecks(page?: number, search?: string, format?: string, race?: string, ordering?: string): Observable<PaginatedResponse<Deck>> {
    let params: any = {};
    if (page) params.page = page;
    if (search) params.search = search;
    if (format) params.format = format;
    if (race) params.race = race;
    if (ordering) params.ordering = ordering;
    return this.http.get<PaginatedResponse<Deck>>(`${this.apiUrl}/team/`, { params });
  }

  getTeamDeck(id: number): Observable<Deck> {
    return this.http.get<Deck>(`${this.apiUrl}/team/${id}/`);
  }

  getMyDecks(page?: number, search?: string, format?: string, race?: string, ordering?: string): Observable<PaginatedResponse<Deck>> {
    let params: any = {};
    if (page) params.page = page;
    if (search) params.search = search;
    if (format) params.format = format;
    if (race) params.race = race;
    if (ordering) params.ordering = ordering;
    return this.http.get<PaginatedResponse<Deck>>(`${this.apiUrl}/my/`, { params });
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

  getChangelog(deckId: number): Observable<{ id: number; summary: string; created_at: string }[]> {
    return this.http.get<{ id: number; summary: string; created_at: string }[]>(`${this.apiUrl}/my/${deckId}/changelog/`);
  }

  setCoverCard(deckId: number, cardId: number): Observable<{ cover_card: number | null }> {
    return this.http.post<{ cover_card: number | null }>(`${this.apiUrl}/my/${deckId}/cover/`, { card_id: cardId });
  }

  clearCoverCard(deckId: number): Observable<{ cover_card: number | null }> {
    return this.http.delete<{ cover_card: number | null }>(`${this.apiUrl}/my/${deckId}/cover/`);
  }

  // Likes
  toggleLike(deckId: number): Observable<{ liked: boolean; like_count: number }> {
    return this.http.post<{ liked: boolean; like_count: number }>(`${this.apiUrl}/public/${deckId}/like/`, {});
  }

  // Comments
  getComments(deckId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/public/${deckId}/comments/`);
  }

  addComment(deckId: number, text: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/public/${deckId}/comments/`, { text });
  }

  deleteComment(commentId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/comments/${commentId}/`);
  }

  // Snapshots
  getSnapshots(deckId: number): Observable<{ id: number; label: string; created_at: string }[]> {
    return this.http.get<any[]>(`${this.apiUrl}/my/${deckId}/snapshots/`);
  }

  createSnapshot(deckId: number, label?: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/my/${deckId}/snapshots/`, { label });
  }

  restoreSnapshot(snapshotId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/snapshots/${snapshotId}/restore/`, {});
  }

  // Suggestions
  getSuggestions(deckId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/my/${deckId}/suggestions/`);
  }

  // Import
  importDeck(payload: any): Observable<{ id: number; name: string; imported_entries: number; missing_myl_ids: string[] }> {
    return this.http.post<{ id: number; name: string; imported_entries: number; missing_myl_ids: string[] }>(
      `${this.apiUrl}/import/`, payload,
    );
  }
}
