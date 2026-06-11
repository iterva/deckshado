import { Component, HostListener, signal, OnInit } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { AuthService } from './services/auth.service';
import { ThemeService } from './services/theme.service';
import { GameModeService } from './services/game-mode.service';
import { NotificationService } from './services/notification.service';
import { RiftboundService } from './services/riftbound.service';
import { IosInstallHintComponent } from './components/ios-install-hint/ios-install-hint.component';
import { PwaInstallHintComponent } from './components/pwa-install-hint/pwa-install-hint.component';
import { ThumbnailPipe } from './pipes/thumbnail.pipe';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, FormsModule, DatePipe, IosInstallHintComponent, PwaInstallHintComponent, ThumbnailPipe],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit {
  showDropdown = signal(false);
  showNotifs = signal(false);
  showSearch = signal(false);
  showMobileMenu = signal(false);
  searchQuery = '';
  searchResults: any = null;
  riftboundCacheLoading = signal(false);
  riftboundCacheCount = signal(0);
  private needsRiftboundEntryWarmup = signal(false);
  private currentUrl = signal('/');
  private warmupStarted = false;

  constructor(
    public auth: AuthService,
    public theme: ThemeService,
    public gameMode: GameModeService,
    public notifs: NotificationService,
    private riftbound: RiftboundService,
    private router: Router,
    private http: HttpClient,
  ) {
    sessionStorage.removeItem('chunk_reload');
    this.currentUrl.set(this.router.url || '/');
    this.router.events.subscribe(event => {
      if (event instanceof NavigationEnd) {
        this.currentUrl.set(event.urlAfterRedirects || event.url || '/');
        this.maybeStartRiftboundWarmup();
      }
    });
  }

  ngOnInit() {
    if (this.auth.isAuthenticated()) {
      this.notifs.load();
    }

    const hasCacheSnapshot = this.riftbound.hasUsableCatalogSnapshot();
    this.needsRiftboundEntryWarmup.set(!hasCacheSnapshot);
    if (hasCacheSnapshot) {
      this.riftboundCacheCount.set(this.riftbound.cachedCatalogCountSnapshot());
    }

    this.maybeStartRiftboundWarmup();
  }

  showRiftboundEntryLoader(): boolean {
    return this.currentUrl().startsWith('/riftbound')
      && this.needsRiftboundEntryWarmup()
      && this.riftboundCacheLoading()
      && this.riftboundCacheCount() === 0;
  }

  private maybeStartRiftboundWarmup() {
    if (this.warmupStarted) return;
    if (!this.needsRiftboundEntryWarmup()) return;
    if (!this.currentUrl().startsWith('/riftbound')) return;

    this.warmupStarted = true;
    this.riftboundCacheLoading.set(true);
    this.riftbound.preloadCardsCatalog().subscribe({
      next: count => this.riftboundCacheCount.set(count),
      error: () => this.riftboundCacheLoading.set(false),
      complete: () => this.riftboundCacheLoading.set(false),
    });
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
    this.http.get(`${environment.apiUrl}/search/`, { params: { q } }).subscribe((res: any) => {
      this.searchResults = res;
    });
  }

  goToResult(type: string, id: number) {
    this.showSearch.set(false);
    this.searchResults = null;
    this.searchQuery = '';
    if (type === 'card') this.router.navigate(['/cards'], { queryParams: { highlight: id } });
    else if (type === 'deck') this.router.navigate(['/decks', id]);
  }

  onNotifClick(notif: any) {
    if (!notif.is_read) this.notifs.markRead(notif.id);
    this.showNotifs.set(false);
    if (notif.link) this.router.navigateByUrl(notif.link);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest('.avatar-wrapper')) this.showDropdown.set(false);
    if (!target.closest('.notif-wrapper')) this.showNotifs.set(false);
    if (!target.closest('.search-wrapper') && !target.closest('.search-toggle')) this.showSearch.set(false);
  }
}
