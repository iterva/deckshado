import {
  AfterViewInit,
  Component,
  OnDestroy,
  OnInit,
  ChangeDetectorRef,
  ElementRef,
  ViewChild,
  HostListener,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute } from '@angular/router';
import { CardService } from '../../services/card.service';
import { Card, Edition, CardType, Race, Rarity } from '../../models';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';
import { IconComponent } from '../../components/icon/icon.component';

@Component({
  selector: 'app-card-list',
  standalone: true,
  imports: [FormsModule, ThumbnailPipe, IconComponent],
  templateUrl: './card-list.component.html',
  styleUrl: './card-list.component.scss',
})
export class CardListComponent implements OnInit, AfterViewInit, OnDestroy {
  cards: Card[] = [];
  editions: Edition[] = [];
  types: CardType[] = [];
  races: Race[] = [];
  rarities: Rarity[] = [];

  search = '';
  selectedEdition = '';
  selectedType = '';
  selectedRace = '';
  selectedRarity = '';

  totalCards = 0;
  currentPage = 1;
  readonly pageSize = 20;
  hasMore = false;
  loading = false;
  selectedCard: Card | null = null;
  viewMode: 'grid' | 'table' = 'grid';

  @ViewChild('searchInput') searchInput?: ElementRef<HTMLInputElement>;
  @ViewChild('cardsSentinel')
  set cardsSentinelSetter(el: ElementRef<HTMLElement> | undefined) {
    this.cardsSentinelRef = el;
    this.setupCardsObserver();
  }
  private cardsSentinelRef?: ElementRef<HTMLElement>;
  private cardsObserver?: IntersectionObserver;
  private contentScrollEl: HTMLElement | null = null;
  private searchDebounceTimer: number | null = null;
  private readonly searchDebounceMs = 2000;

  constructor(private cardService: CardService, private cdr: ChangeDetectorRef, private titleService: Title, private route: ActivatedRoute) {}

  /** Atajo: "/" enfoca el buscador (ignora si ya estás tipeando en otro input). */
  @HostListener('document:keydown', ['$event'])
  onKeydown(ev: KeyboardEvent) {
    if (ev.key === '/' && !this.isTypingTarget(ev.target)) {
      ev.preventDefault();
      this.searchInput?.nativeElement.focus();
      this.searchInput?.nativeElement.select();
    }
  }

  private isTypingTarget(t: EventTarget | null): boolean {
    if (!t) return false;
    const el = t as HTMLElement;
    const tag = (el.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || el.isContentEditable;
  }

  ngOnInit() {
    this.titleService.setTitle('Colección de Cartas — ShadowForge');
    this.loadFilters();
    this.route.queryParamMap.subscribe(params => {
      const q = params.get('search') ?? '';
      this.search = q;
      this.reloadCards();
    });
  }

  ngAfterViewInit() {
    this.setupCardsObserver();
    this.attachContentScrollListener();
    this.tryInfiniteScrollFallback();
  }

  ngOnDestroy() {
    this.cardsObserver?.disconnect();
    this.detachContentScrollListener();
    this.clearSearchDebounce();
  }

  loadFilters() {
    this.cardService.getEditions().subscribe(d => { this.editions = d; this.cdr.detectChanges(); });
    this.cardService.getTypes().subscribe(d => { this.types = d; this.cdr.detectChanges(); });
    this.cardService.getRaces().subscribe(d => { this.races = d; this.cdr.detectChanges(); });
    this.cardService.getRarities().subscribe(d => { this.rarities = d; this.cdr.detectChanges(); });
  }

  loadCards(append = false) {
    this.loading = true;
    this.cardService.getCards({
      search: this.search || undefined,
      edition: this.selectedEdition || undefined,
      type: this.selectedType || undefined,
      deck_race: this.selectedRace || undefined,
      rarity: this.selectedRarity || undefined,
      page: this.currentPage,
    }).subscribe({
      next: (res) => {
        this.cards = append ? [...this.cards, ...res.results] : res.results;
        this.totalCards = res.count;
        this.hasMore = !!res.next;
        this.loading = false;
        this.cdr.detectChanges();
        queueMicrotask(() => {
          this.setupCardsObserver();
          this.tryInfiniteScrollFallback();
        });
      },
      error: () => {
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  reloadCards() {
    this.currentPage = 1;
    this.cards = [];
    this.hasMore = false;
    this.loadCards();
  }

  loadMoreCards() {
    if (this.loading || !this.hasMore) return;
    this.currentPage++;
    this.loadCards(true);
  }

  onSearch() {
    this.clearSearchDebounce();
    this.reloadCards();
  }

  onSearchInput() {
    this.clearSearchDebounce();
    this.searchDebounceTimer = window.setTimeout(() => {
      this.searchDebounceTimer = null;
      this.reloadCards();
    }, this.searchDebounceMs);
  }

  onFilterChange() {
    this.clearSearchDebounce();
    this.reloadCards();
  }

  @HostListener('window:scroll')
  onWindowScroll() { this.tryInfiniteScrollFallback(); }

  @HostListener('window:resize')
  onWindowResize() { this.tryInfiniteScrollFallback(); }

  private setupCardsObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.cardsObserver?.disconnect();
    const sentinel = this.cardsSentinelRef?.nativeElement;
    if (!sentinel) return;
    this.cardsObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          this.loadMoreCards();
          break;
        }
      }
    }, { rootMargin: '320px 0px' });
    this.cardsObserver.observe(sentinel);
  }

  private attachContentScrollListener() {
    this.detachContentScrollListener();
    const el = document.querySelector('main.content') as HTMLElement | null;
    if (!el) return;
    this.contentScrollEl = el;
    this.contentScrollEl.addEventListener('scroll', this.onContentScroll, { passive: true });
  }

  private detachContentScrollListener() {
    if (!this.contentScrollEl) return;
    this.contentScrollEl.removeEventListener('scroll', this.onContentScroll);
    this.contentScrollEl = null;
  }

  private onContentScroll = () => {
    this.tryInfiniteScrollFallback();
  };

  private clearSearchDebounce() {
    if (this.searchDebounceTimer === null) return;
    window.clearTimeout(this.searchDebounceTimer);
    this.searchDebounceTimer = null;
  }

  private tryInfiniteScrollFallback() {
    if (!this.isNearPageBottom()) return;
    this.loadMoreCards();
  }

  private isNearPageBottom(offset = 900): boolean {
    const container = this.contentScrollEl;
    if (container && container.scrollHeight > container.clientHeight) {
      return container.scrollTop + container.clientHeight >= container.scrollHeight - 420;
    }
    const doc = document.documentElement;
    const body = document.body;
    const scrollTop = window.scrollY || doc.scrollTop || 0;
    const viewport = window.innerHeight || doc.clientHeight || 0;
    const fullHeight = Math.max(doc.scrollHeight, body?.scrollHeight || 0);
    return scrollTop + viewport >= fullHeight - offset;
  }

  selectCard(card: Card) {
    this.selectedCard = this.selectedCard?.id === card.id ? null : card;
  }

  get totalPages(): number {
    return Math.ceil(this.totalCards / this.pageSize);
  }
}
