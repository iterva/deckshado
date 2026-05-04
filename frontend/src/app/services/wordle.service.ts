import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface WordleGuess {
  letters: string[];
  statuses: ('correct' | 'present' | 'absent')[];
}

export interface WordleState {
  date: string;
  length: number;
  max_attempts: number;
  hint: string | null;
  hint_available: boolean;
  hint_revealed: boolean;
  guesses: WordleGuess[];
  attempts_used: number;
  won: boolean;
  finished: boolean;
  score: number;
  answer: string | null;
  card_image: string | null;
  card_id: number | null;
}

export interface WordleLeaderboardEntry {
  user_id: number;
  username: string;
  score: number;
  wins: number;
  played: number;
}

export interface WordleLeaderboard {
  year: number;
  month: number;
  leaderboard: WordleLeaderboardEntry[];
}

export interface WordleWinner {
  year: number;
  month: number;
  winner: { user_id: number; username: string; score: number } | null;
}

@Injectable({ providedIn: 'root' })
export class WordleService {
  private readonly api = `${environment.apiUrl}/wordle`;

  constructor(private http: HttpClient) {}

  today(): Observable<WordleState> {
    return this.http.get<WordleState>(`${this.api}/today/`);
  }

  guess(word: string): Observable<WordleState> {
    return this.http.post<WordleState>(`${this.api}/guess/`, { guess: word });
  }

  hint(): Observable<{ hint: string; hint_revealed: boolean }> {
    return this.http.post<{ hint: string; hint_revealed: boolean }>(
      `${this.api}/hint/`,
      {}
    );
  }

  leaderboard(year?: number, month?: number): Observable<WordleLeaderboard> {
    const params: Record<string, string> = {};
    if (year) params['year'] = String(year);
    if (month) params['month'] = String(month);
    return this.http.get<WordleLeaderboard>(`${this.api}/leaderboard/`, { params });
  }

  previousWinner(): Observable<WordleWinner> {
    return this.http.get<WordleWinner>(`${this.api}/winner/`);
  }
}
