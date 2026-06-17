import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
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

  /** Login / signup con id_token de Google. */
  loginWithGoogle(credential: string) {
    return this.http.post<AuthTokens & { linked?: boolean; created?: boolean }>(
      `${this.apiUrl}/google/`, { credential }
    );
  }

  /** Vincula Google a la cuenta autenticada. */
  linkGoogle(credential: string) {
    return this.http.post<{ linked: boolean; email: string }>(
      `${this.apiUrl}/google/link/`, { credential }
    );
  }

  /** Desvincula Google de la cuenta autenticada. */
  unlinkGoogle() {
    return this.http.delete<{ unlinked: boolean }>(`${this.apiUrl}/google/unlink/`);
  }

  /** Estado de cuentas sociales del usuario actual. */
  getSocialStatus() {
    return this.http.get<{
      has_usable_password: boolean;
      accounts: { provider: string; email: string; linked_at: string }[];
    }>(`${this.apiUrl}/social/`);
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
        this.loggedIn.set(true);
        this.isLoadingUser.set(false);
      },
      error: (err) => {
        console.error('Error loading user:', err);
        this.isLoadingUser.set(false);
        // Si no se pudo verificar la sesión (token inválido/expirado, o el
        // interceptor ya borró los tokens al fallar el refresh), limpiamos
        // el estado de autenticación para evitar mostrar UI de usuario logueado
        // sin datos. Solo conservamos la sesión si fue un error transitorio
        // (servidor 5xx) y aún tenemos token guardado.
        const stillHasToken = !!localStorage.getItem('access_token');
        const isServerError = err.status >= 500 && err.status < 600;
        if (!stillHasToken || !isServerError) {
          this.logout(false);
        }
      },
    });
  }

  logout(hardReload = false) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.loggedIn.set(false);
    this.currentUser.set(null);
    if (hardReload) {
      window.location.href = '/';
    } else {
      this.router.navigate(['/']);
    }
  }

  updateProfile(data: { first_name?: string; last_name?: string; league_code?: string }): Observable<User> {
    return this.http.patch<User>(`${this.apiUrl}/profile/`, data).pipe(
      tap(user => this.currentUser.set(user)),
    );
  }

  uploadAvatar(file: File): Observable<User> {
    const fd = new FormData();
    fd.append('file', file);
    return this.http.post<User>(`${this.apiUrl}/avatar/`, fd).pipe(
      tap(user => this.currentUser.set(user)),
    );
  }

  changePassword(oldPassword: string, newPassword: string): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(`${this.apiUrl}/change-password/`, {
      old_password: oldPassword,
      new_password: newPassword,
    });
  }
}
