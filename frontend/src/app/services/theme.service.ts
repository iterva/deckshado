import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly STORAGE_KEY = 'deckshado_theme';
  isDark = signal(true);

  constructor() {
    const saved = localStorage.getItem(this.STORAGE_KEY);
    if (saved === 'light') {
      this.isDark.set(false);
      document.body.classList.add('light-theme');
    }
  }

  toggle() {
    const dark = !this.isDark();
    this.isDark.set(dark);
    if (dark) {
      document.body.classList.remove('light-theme');
      localStorage.setItem(this.STORAGE_KEY, 'dark');
    } else {
      document.body.classList.add('light-theme');
      localStorage.setItem(this.STORAGE_KEY, 'light');
    }
  }
}
