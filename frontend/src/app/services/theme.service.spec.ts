import { TestBed } from '@angular/core/testing';
import { ThemeService } from './theme.service';

describe('ThemeService', () => {
  beforeEach(() => {
    localStorage.clear();
    document.body.classList.remove('light-theme');
  });

  it('starts in dark mode by default', () => {
    TestBed.configureTestingModule({});
    const svc = TestBed.inject(ThemeService);
    expect(svc.isDark()).toBe(true);
    expect(document.body.classList.contains('light-theme')).toBe(false);
  });

  it('restores light theme from localStorage', () => {
    localStorage.setItem('deckshado_theme', 'light');
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({});
    const svc = TestBed.inject(ThemeService);
    expect(svc.isDark()).toBe(false);
    expect(document.body.classList.contains('light-theme')).toBe(true);
  });

  it('toggle switches dark <-> light and persists to localStorage', () => {
    TestBed.configureTestingModule({});
    const svc = TestBed.inject(ThemeService);
    svc.toggle();
    expect(svc.isDark()).toBe(false);
    expect(document.body.classList.contains('light-theme')).toBe(true);
    expect(localStorage.getItem('deckshado_theme')).toBe('light');
    svc.toggle();
    expect(svc.isDark()).toBe(true);
    expect(document.body.classList.contains('light-theme')).toBe(false);
    expect(localStorage.getItem('deckshado_theme')).toBe('dark');
  });
});
