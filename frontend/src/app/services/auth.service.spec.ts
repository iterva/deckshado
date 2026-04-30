import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';

describe('AuthService', () => {
  let svc: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    });
    svc = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('starts unauthenticated when no token in localStorage', () => {
    expect(svc.isAuthenticated()).toBe(false);
    expect(svc.user()).toBeNull();
  });

  it('handleLoginSuccess stores tokens, marks authenticated and loads user', () => {
    svc.handleLoginSuccess({ access: 'a', refresh: 'r' } as any);
    expect(localStorage.getItem('access_token')).toBe('a');
    expect(localStorage.getItem('refresh_token')).toBe('r');
    expect(svc.isAuthenticated()).toBe(true);

    const req = httpMock.expectOne(`${environment.apiUrl}/auth/me/`);
    expect(req.request.method).toBe('GET');
    req.flush({ id: 1, username: 'kristal', email: 'k@x.com' });

    expect(svc.user()?.username).toBe('kristal');
  });

  it('logout clears tokens, state and navigates to /', () => {
    localStorage.setItem('access_token', 't');
    localStorage.setItem('refresh_token', 'r');
    svc.handleLoginSuccess({ access: 't', refresh: 'r' } as any);
    httpMock.expectOne(`${environment.apiUrl}/auth/me/`).flush({ id: 1, username: 'k' });

    const router = TestBed.inject(Router);
    const navSpy = vi.spyOn(router, 'navigate');
    svc.logout();
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(svc.isAuthenticated()).toBe(false);
    expect(svc.user()).toBeNull();
    expect(navSpy).toHaveBeenCalledWith(['/']);
  });
});
