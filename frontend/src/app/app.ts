import { Component, HostListener, signal, OnInit, ViewChild, ElementRef } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { AuthService } from './services/auth.service';
import { ThemeService } from './services/theme.service';
import { GameModeService } from './services/game-mode.service';
import { NotificationService } from './services/notification.service';
import { IosInstallHintComponent } from './components/ios-install-hint/ios-install-hint.component';
import { PwaInstallHintComponent } from './components/pwa-install-hint/pwa-install-hint.component';
import { IconComponent } from './components/icon/icon.component';
import { ThumbnailPipe } from './pipes/thumbnail.pipe';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    FormsModule,
    DatePipe,
    IosInstallHintComponent,
    PwaInstallHintComponent,
    ThumbnailPipe,
    IconComponent,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit {
  @ViewChild('globalSearchInput') globalSearchInput?: ElementRef<HTMLInputElement>;

  showDropdown = signal(false);
  showNotifs = signal(false);
  showSearch = signal(false);
  showMobileMenu = signal(false);
  readonly appVersion = environment.appVersion;
  hardReloading = signal(false);
  searchQuery = '';
  searchResults: any = null;

  constructor(
    public auth: AuthService,
    public theme: ThemeService,
    public gameMode: GameModeService,
    public notifs: NotificationService,
    private router: Router,
    private http: HttpClient,
  ) {
    sessionStorage.removeItem('chunk_reload');
  }

  ngOnInit() {
    if (this.auth.isAuthenticated()) {
      this.notifs.load();
    }

    this.router.events.subscribe((event) => {
      if (event instanceof NavigationEnd && !this.canUseGlobalSearch()) {
        this.showSearch.set(false);
        this.searchResults = null;
        this.searchQuery = '';
      }
    });
  }

  canUseGlobalSearch(): boolean {
    if (!this.isMobileViewport()) {
      return true;
    }

    const blockedMobileRoutes = [
      '/riftbound/cards',
      '/riftbound/carpeta',
      '/riftbound/colaborar',
      '/riftbound/tienda',
      '/carpeta',
      '/tienda',
    ];

    return !blockedMobileRoutes.some(route => this.router.url.startsWith(route));
  }

  private isMobileViewport(): boolean {
    return typeof window !== 'undefined' && window.innerWidth <= 768;
  }

  toggleDropdown() {
    this.showDropdown.update(v => !v);
    this.showNotifs.set(false);
  }

  toggleNotifs() {
    this.showNotifs.update(v => !v);
    this.showDropdown.set(false);
  }

  toggleSearch() {
    this.showSearch.update(v => !v);
    this.searchResults = null;
    this.searchQuery = '';
    if (this.showSearch()) {
      setTimeout(() => this.globalSearchInput?.nativeElement?.focus(), 50);
    }
  }

  openSearch() {
    this.showSearch.set(true);
    this.searchResults = null;
    this.searchQuery = '';
    setTimeout(() => this.globalSearchInput?.nativeElement?.focus(), 50);
  }

  closeSearch() {
    this.showSearch.set(false);
    this.searchResults = null;
    this.searchQuery = '';
  }

  toggleMobileMenu() {
    this.showMobileMenu.update(v => !v);
  }

  closeMobileMenu() {
    this.showMobileMenu.set(false);
  }

  onSearch() {
    const q = this.searchQuery.trim();
    if (q.length < 2) { this.searchResults = null; return; }
    const game = this.gameMode.isRiftbound() ? 'riftbound' : 'myl';
    this.http.get(`${environment.apiUrl}/search/`, { params: { q, game } }).subscribe((res: any) => {
      this.searchResults = res;
    });
  }

  goToResult(type: string, item: any) {
    this.showSearch.set(false);
    this.searchResults = null;
    this.searchQuery = '';
    const isRiftbound = this.gameMode.isRiftbound();
    if (type === 'card') {
      if (isRiftbound) this.router.navigate(['/riftbound/cards', item.card_number]);
      else this.router.navigate(['/cards'], { queryParams: { highlight: item.id } });
    } else if (type === 'deck') {
      if (isRiftbound) this.router.navigate(['/riftbound/decks', item.id]);
      else this.router.navigate(['/decks', item.id]);
    }
  }

  onNotifClick(notif: any) {
    if (!notif.is_read) this.notifs.markRead(notif.id);
    this.showNotifs.set(false);
    if (notif.link) this.router.navigateByUrl(notif.link);
  }

  async hardRefresh(closeMenu = false) {
    if (this.hardReloading()) return;
    if (closeMenu) this.closeMobileMenu();
    if (typeof window === 'undefined') return;

    this.hardReloading.set(true);

    try {
      if ('serviceWorker' in navigator) {
        const regs = await navigator.serviceWorker.getRegistrations();
        await Promise.all(regs.map(r => r.unregister()));
      }

      if ('caches' in window) {
        const cacheKeys = await caches.keys();
        await Promise.all(cacheKeys.map(key => caches.delete(key)));
      }
    } catch {
      // No bloquea recarga si falla limpieza de caché.
    }

    const url = new URL(window.location.href);
    url.searchParams.set('_rf', Date.now().toString());
    window.location.replace(url.toString());
  }

  @HostListener('window:keydown', ['$event'])
  onKeyDown(event: KeyboardEvent) {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      this.toggleSearch();
    } else if (event.key === 'Escape') {
      if (this.showSearch()) this.closeSearch();
      if (this.showDropdown()) this.showDropdown.set(false);
      if (this.showNotifs()) this.showNotifs.set(false);
      if (this.showMobileMenu()) this.closeMobileMenu();
    }
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest('.avatar-wrapper')) this.showDropdown.set(false);
    if (!target.closest('.notif-wrapper')) this.showNotifs.set(false);
    if (!target.closest('.search-wrapper') && !target.closest('.search-toggle') && !target.closest('.cmd-search-bar')) this.showSearch.set(false);
  }
}
