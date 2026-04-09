import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';
import { AuthTokens, User } from '../models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly apiUrl = `${environment.apiUrl}/auth`;
  private currentUser = signal<User | null>(null);
  private isLoadingUser = signal(false);
  private loggedIn = signal(!!localStorage.getItem('access_token'));

  user = this.currentUser.asReadonly();
  isAuthenticated = this.loggedIn.asReadonly();

  constructor(private http: HttpClient, private router: Router) {
    if (this.getToken()) {
      this.loadUser();
    }
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  login(username: string, password: string) {
    return this.http.post<AuthTokens>(`${this.apiUrl}/login/`, { username, password });
  }

  register(username: string, email: string, password: string) {
    return this.http.post<User>(`${this.apiUrl}/register/`, { username, email, password });
  }

  handleLoginSuccess(tokens: AuthTokens) {
    localStorage.setItem('access_token', tokens.access);
    localStorage.setItem('refresh_token', tokens.refresh);
    this.loggedIn.set(true);
    this.loadUser();
  }

  loadUser() {
    this.isLoadingUser.set(true);
    this.http.get<User>(`${this.apiUrl}/me/`).subscribe({
      next: (user) => {
        this.currentUser.set(user);
        this.isLoadingUser.set(false);
      },
      error: (err) => {
        console.error('Error loading user:', err);
        if (err.status === 401) {
          this.logout();
        }
        this.currentUser.set(null);
        this.isLoadingUser.set(false);
      },
    });
  }

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.loggedIn.set(false);
    this.currentUser.set(null);
    this.router.navigate(['/']);
  }
}
