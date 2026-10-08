import { Component, OnInit, AfterViewInit, OnDestroy, ChangeDetectorRef, HostListener, ElementRef, ViewChild } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DecimalPipe } from '@angular/common';
import { CarpetaService, StoreFilters } from '../../services/carpeta.service';
import { CardService } from '../../services/card.service';
import { AuthService } from '../../services/auth.service';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';
import {
  CollectionEntry,
  Card,
  PublicBinderProfile,
  Edition,
  Race,
  Rarity,
  CardType,
  WishlistEntry,
  StoreOrderCreatePayload,
} from '../../models';
import { ShareImageComponent, ShareImageItem } from '../../components/share-image/share-image.component';
import { CardPhotoCarouselComponent } from '../../components/card-photo-carousel/card-photo-carousel.component';
import { IconComponent } from '../../components/icon/icon.component';

interface CartItem {
  entryId: number;
  cardId: number;
  name: string;
  price: number | null;
  qty: number;
  available: number;
  image: string;
}

@Component({
  selector: 'app-tienda',
  standalone: true,
  imports: [FormsModule, ThumbnailPipe, DecimalPipe, RouterLink, ShareImageComponent, CardPhotoCarouselComponent, IconComponent],
  templateUrl: './tienda.component.html',
  styleUrl: './tienda.component.scss',
})
export class TiendaComponent implements OnInit, AfterViewInit, OnDestroy {
  token = '';
  store: PublicBinderProfile | null = null;
  entries: CollectionEntry[] = [];
  total = 0;
  loading = false;
  storeHasMore = false;
  notFound = false;
  previewCard: Card | null = null;
  previewImageStep = 0;
  viewPhotoUrl: string | null = null;
  showContactModal = false;
  showCart = false;
  viewMode: 'grid' | 'list' = 'grid';
  showFilterPanel = false;

  // Tabs
  activeTab: 'store' | 'wishlist' = 'store';
  wishlistEntries: WishlistEntry[] = [];
  wishlistTotal = 0;
  wishlistLoading = false;
  wishlistLoaded = false;
  wishlistSearch = '';

  // Filters
  filters: StoreFilters = { page: 1, ordering: '-id' };
  editions: Edition[] = [];
  races: Race[] = [];
  rarities: Rarity[] = [];
  types: CardType[] = [];
  openFilter: 'fmt' | 'edition' | 'race' | 'rarity' | 'type' | null = null;

  // Cart (localStorage scoped per token/slug)
  cart: CartItem[] = [];
  buyerName = '';
  buyerWhatsapp = '';
  buyerNote = '';
  orderSubmitting = false;
  orderError = '';
  createdOrderId: number | null = null;
  /** WhatsApp ya no se abre solo al crear el pedido: queda como botón opcional en el aviso. */
  createdOrderWhatsAppUrl: string | null = null;
  private storeSentinelRef?: ElementRef<HTMLElement>;
  private storeObserver?: IntersectionObserver;
  private contentScrollEl: HTMLElement | null = null;

  @ViewChild('storeSentinel')
  set storeSentinelSetter(el: ElementRef<HTMLElement> | undefined) {
    this.storeSentinelRef = el;
    this.setupStoreObserver();
  }

  constructor(
    private route: ActivatedRoute,
    private carpetaService: CarpetaService,
    private cardService: CardService,
    public auth: AuthService,
    private cdr: ChangeDetectorRef,
  ) {}

  @HostListener('document:click')
  onDocClick() { this.openFilter = null; }

  @HostListener('window:scroll')
  onWindowScroll() { this.tryInfiniteScrollFallback(); }

  @HostListener('window:resize')
  onWindowResize() { this.tryInfiniteScrollFallback(); }

  ngOnInit() {
    this.token = this.route.snapshot.paramMap.get('token') || this.route.snapshot.paramMap.get('slug') || '';
    if (!this.token) { this.notFound = true; return; }
    const dt = this.route.snapshot.data?.['defaultTab'];
    if (dt === 'wishlist') this.activeTab = 'wishlist';
    this.loadCart();
    this.loadViewMode();
    this.buyerName = this.auth.user()?.username || '';
    this.loadFilters();
    this.loadStore();
    if (this.activeTab === 'wishlist') this.loadWishlist();
  }

  ngAfterViewInit() {
    this.setupStoreObserver();
    this.attachContentScrollListener();
    this.tryInfiniteScrollFallback();
  }

  ngOnDestroy() {
    this.storeObserver?.disconnect();
    this.detachContentScrollListener();
  }

  loadFilters() {
    this.cardService.getEditions().subscribe(d => { this.editions = d; this.cdr.detectChanges(); });
    this.cardService.getRaces().subscribe(d => { this.races = d; this.cdr.detectChanges(); });
    this.cardService.getRarities().subscribe(d => { this.rarities = d; this.cdr.detectChanges(); });
    this.cardService.getTypes().subscribe(d => { this.types = d; this.cdr.detectChanges(); });
  }

  loadStore(append = false) {
    this.loading = true;
    this.carpetaService.getPublicStore(this.token, this.filters).subscribe({
      next: res => {
        this.entries = append ? [...this.entries, ...res.results] : res.results;
        this.total = res.count;
        this.storeHasMore = !!res.next;
        this.store = res.store;
        this.loading = false;
        this.syncCartAvailability();
        this.cdr.detectChanges();
        setTimeout(() => {
          this.setupStoreObserver();
          this.tryInfiniteScrollFallback();
        });
      },
      error: () => { this.notFound = true; this.loading = false; this.cdr.detectChanges(); },
    });
  }

  applyFilter() {
    this.filters.page = 1;
    this.entries = [];
    this.storeHasMore = false;
    this.loadStore();
  }

  get isOwner(): boolean {
    return !!this.store?.username && this.store.username === this.auth.user()?.username;
  }
  resetFilters() {
    this.filters = { page: 1, ordering: '-id' };
    this.entries = [];
    this.storeHasMore = false;
    this.loadStore();
  }

  toggleFilterPopover(filter: 'fmt' | 'edition' | 'race' | 'rarity' | 'type', event: Event) {
    event.stopPropagation();
    this.openFilter = this.openFilter === filter ? null : filter;
  }

  // ── View mode (grid/list) ──
  private viewModeKey(): string { return 'tienda-view-mode'; }

  loadViewMode() {
    try {
      const saved = localStorage.getItem(this.viewModeKey());
      if (saved === 'grid' || saved === 'list') this.viewMode = saved;
    } catch {}
  }

  setViewMode(mode: 'grid' | 'list') {
    if (this.viewMode === mode) return;
    this.viewMode = mode;
    try { localStorage.setItem(this.viewModeKey(), mode); } catch {}
  }

  toggleFilterPanel(event: Event) {
    event.stopPropagation();
    this.showFilterPanel = !this.showFilterPanel;
  }

  get activeFilterCount(): number {
    const keys: Array<'fmt' | 'edition' | 'race' | 'rarity' | 'type'> = ['fmt', 'edition', 'race', 'rarity', 'type'];
    return keys.reduce((n, k) => n + (this.filters[k] ? 1 : 0), 0);
  }

  filterLabel(filter: 'fmt' | 'edition' | 'race' | 'rarity' | 'type'): string {
    if (filter === 'fmt') {
      const val = this.filters.fmt;
      if (!val) return 'Todos los formatos';
      const map: Record<string, string> = { imp: 'Imperio', imp_r: 'Imperio Retro', esc: 'Escuelas Elementales', pb: 'Primer Bloque', pe: 'Primera Era' };
      return map[val] || val;
    }
    const val = this.filters[filter] as string | undefined;
    if (!val) {
      const labels = { edition: 'Todas las ediciones', race: 'Todas las razas', rarity: 'Todas las frecuencias', type: 'Todos los tipos' };
      return labels[filter];
    }
    if (filter === 'edition') return this.editions.find(e => e.slug === val)?.title || val;
    if (filter === 'race') return this.races.find(r => r.slug === val)?.name || val;
    if (filter === 'rarity') return this.rarities.find(r => r.slug === val)?.name || val;
    return this.types.find(t => t.slug === val)?.name || val;
  }

  selectFilter(filter: 'fmt' | 'edition' | 'race' | 'rarity' | 'type', value: string) {
    (this.filters as any)[filter] = this.filters[filter] === value ? '' : value;
    this.openFilter = null;
    this.applyFilter();
  }
  loadMoreStore() {
    if (this.activeTab !== 'store' || this.loading || !this.storeHasMore) return;
    this.filters.page = (this.filters.page || 1) + 1;
    this.loadStore(true);
  }

  private setupStoreObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.storeObserver?.disconnect();
    if (this.activeTab !== 'store') return;
    const sentinel = this.storeSentinelRef?.nativeElement;
    if (!sentinel) return;
    this.storeObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          this.loadMoreStore();
          break;
        }
      }
    }, { rootMargin: '320px 0px' });
    this.storeObserver.observe(sentinel);
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

  private tryInfiniteScrollFallback() {
    if (!this.isNearPageBottom()) return;
    if (this.activeTab === 'store') this.loadMoreStore();
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

  // ── Cart ──
  cartKey(): string { return `tienda-cart::${this.token}`; }

  loadCart() {
    try {
      const raw = localStorage.getItem(this.cartKey());
      this.cart = raw ? JSON.parse(raw) : [];
    } catch { this.cart = []; }
  }

  saveCart() {
    try { localStorage.setItem(this.cartKey(), JSON.stringify(this.cart)); } catch {}
  }

  syncCartAvailability() {
    // Update available counts based on latest fetch
    for (const ci of this.cart) {
      const e = this.entries.find(x => x.id === ci.entryId);
      if (e) ci.available = e.selling_quantity;
    }
    this.saveCart();
  }

  addToCart(entry: CollectionEntry, ev: MouseEvent) {
    ev.stopPropagation();
    const existing = this.cart.find(c => c.entryId === entry.id);
    if (existing) {
      if (existing.qty < entry.selling_quantity) existing.qty++;
    } else {
      this.cart.push({
        entryId: entry.id,
        cardId: entry.card_detail.id,
        name: entry.card_detail.name,
        price: entry.price,
        qty: 1,
        available: entry.selling_quantity,
        image: entry.card_detail.image_url,
      });
    }
    this.saveCart();
    this.createdOrderId = null;
    this.createdOrderWhatsAppUrl = null;
    this.orderError = '';
    this.cdr.detectChanges();
  }

  removeFromCart(item: CartItem) {
    this.cart = this.cart.filter(c => c.entryId !== item.entryId);
    this.saveCart();
  }

  changeCartQty(item: CartItem, delta: number) {
    const newQty = item.qty + delta;
    if (newQty <= 0) { this.removeFromCart(item); return; }
    if (newQty > item.available) return;
    item.qty = newQty;
    this.saveCart();
  }

  clearCart() { this.cart = []; this.saveCart(); }

  private syncCartWithLatestStock(latestEntries: CollectionEntry[]) {
    const latestByEntry = new Map<number, CollectionEntry>();
    for (const entry of latestEntries) latestByEntry.set(entry.id, entry);

    const removed: string[] = [];
    const reduced: string[] = [];
    const nextCart: CartItem[] = [];

    for (const item of this.cart) {
      const latest = latestByEntry.get(item.entryId);
      const available = latest?.selling_quantity ?? 0;

      if (available <= 0) {
        removed.push(item.name);
        continue;
      }

      const nextQty = Math.min(item.qty, available);
      if (nextQty < item.qty) {
        reduced.push(`${item.name} (${item.qty}->${nextQty})`);
      }

      nextCart.push({
        ...item,
        name: latest?.card_detail?.name || item.name,
        image: latest?.card_detail?.image_url || item.image,
        price: latest?.price ?? item.price,
        available,
        qty: nextQty,
      });
    }

    return { nextCart, removed, reduced };
  }

  canSubmitOrder(): boolean {
    return this.cart.length > 0
      && !this.orderSubmitting
      && !!this.buyerName.trim()
      && !!this.buyerWhatsapp.trim();
  }

  get cartCount(): number { return this.cart.reduce((s, c) => s + c.qty, 0); }
  get cartTotal(): number {
    return this.cart.reduce((s, c) => s + (c.price || 0) * c.qty, 0);
  }
  get cartHasUnpriced(): boolean { return this.cart.some(c => !c.price); }

  inCart(entryId: number): number {
    return this.cart.find(c => c.entryId === entryId)?.qty || 0;
  }

  buildOrderText(): string {
    const lines = [`Hola ${this.store?.display_name || this.store?.username}! Quiero comprar:`];
    for (const c of this.cart) {
      const priceTxt = c.price ? `— $${c.price.toLocaleString('es-CL')} c/u` : '— precio?';
      lines.push(`• ${c.qty}x ${c.name} ${priceTxt}`);
    }
    if (!this.cartHasUnpriced) {
      lines.push('');
      lines.push(`Total: $${this.cartTotal.toLocaleString('es-CL')}`);
    }
    lines.push('');
    lines.push(`(Pedido desde tienda Deckshado)`);
    return lines.join('\n');
  }

  sendWhatsApp() {
    const url = this.buildWhatsAppOrderUrl();
    if (!url) return;
    window.open(url, '_blank');
  }

  private buildWhatsAppOrderUrl(orderId?: number): string | null {
    if (!this.store?.whatsapp) return null;
    const number = this.store.whatsapp.replace(/[^0-9]/g, '');
    if (!number) return null;
    const orderSuffix = orderId ? `\n\nPedido #${orderId}` : '';
    const text = encodeURIComponent(`${this.buildOrderText()}${orderSuffix}`);
    return `https://wa.me/${number}?text=${text}`;
  }

  copyOrder() {
    navigator.clipboard.writeText(this.buildOrderText());
  }

  createOrder() {
    if (!this.canSubmitOrder()) return;
    this.orderSubmitting = true;
    this.orderError = '';

    const entryIds = Array.from(new Set(this.cart.map(c => c.entryId)));
    this.carpetaService.getPublicStore(this.token, {
      entry_ids: entryIds,
      page_size: Math.max(40, entryIds.length),
      ordering: 'id',
    }).subscribe({
      next: (res) => {
        const { nextCart, removed, reduced } = this.syncCartWithLatestStock(res.results);
        this.cart = nextCart;
        this.saveCart();

        if (removed.length > 0 || reduced.length > 0 || nextCart.length === 0) {
          const msg: string[] = ['Actualizamos el stock antes de enviar el pedido.'];
          if (removed.length > 0) {
            msg.push(`Sin stock: ${removed.slice(0, 3).join(', ')}${removed.length > 3 ? '...' : ''}.`);
          }
          if (reduced.length > 0) {
            msg.push(`Cantidades ajustadas: ${reduced.slice(0, 3).join(', ')}${reduced.length > 3 ? '...' : ''}.`);
          }
          if (nextCart.length === 0) {
            msg.push('El carrito quedo sin items disponibles.');
          } else {
            msg.push('Revisa el carrito y confirma nuevamente.');
          }

          this.orderSubmitting = false;
          this.orderError = msg.join(' ');
          this.loadStore();
          this.cdr.detectChanges();
          return;
        }

        const payload: StoreOrderCreatePayload = {
          buyer_name: this.buyerName.trim(),
          buyer_whatsapp: this.buyerWhatsapp.trim(),
          buyer_note: (this.buyerNote || '').trim(),
          items: nextCart.map((item) => ({ entry_id: item.entryId, quantity: item.qty })),
        };

        this.carpetaService.createPublicStoreOrder(this.token, payload).subscribe({
          next: (order) => {
            // El texto se arma con el carrito, así que la URL se calcula antes de vaciarlo.
            const waUrl = this.buildWhatsAppOrderUrl(order.id);
            this.orderSubmitting = false;
            this.clearCart();
            this.createdOrderId = order.id;
            this.createdOrderWhatsAppUrl = waUrl;
            this.showCart = false;
            this.loadStore();
            this.cdr.detectChanges();
          },
          error: (err) => {
            this.orderSubmitting = false;
            this.orderError = err?.error?.detail || 'No se pudo crear el pedido. Revisa stock y vuelve a intentar.';
            this.cdr.detectChanges();
          },
        });
      },
      error: (err) => {
        this.orderSubmitting = false;
        this.orderError = err?.error?.detail || 'No se pudo validar stock actualizado. Intenta nuevamente.';
        this.cdr.detectChanges();
      },
    });
  }

  // ── Tabs / Wishlist ──
  switchTab(tab: 'store' | 'wishlist') {
    if (this.activeTab === tab) return;
    this.activeTab = tab;
    if (tab === 'wishlist' && !this.wishlistLoaded) this.loadWishlist();
    if (tab === 'store') {
      setTimeout(() => {
        this.setupStoreObserver();
        this.tryInfiniteScrollFallback();
      });
    }
  }

  loadWishlist() {
    this.wishlistLoading = true;
    this.carpetaService.getPublicWishlist(this.token, { search: this.wishlistSearch || undefined }).subscribe({
      next: res => {
        this.wishlistEntries = res.results;
        this.wishlistTotal = res.count;
        // El backend siempre devuelve el store actualizado con flags
        if (res.store && !this.store) this.store = res.store;
        if (res.store) {
          this.store = { ...this.store, ...res.store } as PublicBinderProfile;
        }
        this.wishlistLoading = false;
        this.wishlistLoaded = true;
        this.cdr.detectChanges();
      },
      error: () => {
        this.wishlistLoading = false;
        this.wishlistLoaded = true;
        this.cdr.detectChanges();
      },
    });
  }

  applyWishlistFilter() {
    this.wishlistLoaded = false;
    this.loadWishlist();
  }

  shareWishlistLink() {
    const url = `${window.location.origin}/wishlist/${this.token}`;
    navigator.clipboard.writeText(url);
  }

  shareWishlistWhatsApp() {
    const url = `${window.location.origin}/wishlist/${this.token}`;
    const txt = encodeURIComponent(`Mira mi wishlist de cartas: ${url}`);
    window.open(`https://wa.me/?text=${txt}`, '_blank');
  }

  // ── Share ──
  copyLink() {
    navigator.clipboard.writeText(window.location.href);
  }

  shareWhatsApp() {
    const txt = encodeURIComponent(`Mira mi tienda de cartas: ${window.location.href}`);
    window.open(`https://wa.me/?text=${txt}`, '_blank');
  }

  // ── Contact ──
  contactWhatsAppDirect() {
    if (!this.store?.whatsapp) return;
    const number = this.store.whatsapp.replace(/[^0-9]/g, '');
    const text = encodeURIComponent(`Hola ${this.store.display_name || this.store.username}, te escribo desde tu tienda Deckshado.`);
    window.open(`https://wa.me/${number}?text=${text}`, '_blank');
  }

  exportPdf() { window.print(); }

  openPreviewCard(card: Card | null | undefined) {
    if (!card) return;
    this.previewCard = card;
    this.previewImageStep = 0;
  }

  closePreviewCard() {
    this.previewCard = null;
    this.previewImageStep = 0;
  }

  private normalizePreviewImageUrl(url: string | null | undefined): string {
    const value = (url || '').trim();
    if (!value) return '';
    return value.startsWith('http://') ? `https://${value.slice(7)}` : value;
  }

  private cloudinaryFetchProxy(url: string): string {
    return `https://res.cloudinary.com/daobfx9yb/image/fetch/f_auto,q_auto/${encodeURIComponent(url)}`;
  }

  private previewImageCandidates(card: Card | null | undefined): string[] {
    if (!card) return [];
    const raw = [
      this.normalizePreviewImageUrl(card.image_url),
      this.normalizePreviewImageUrl((card as any)?.image),
    ].filter(Boolean);

    const proxied = raw.map((url) => this.cloudinaryFetchProxy(url));
    return Array.from(new Set([...raw, ...proxied]));
  }

  previewModalImageUrl(card: Card | null | undefined): string {
    const candidates = this.previewImageCandidates(card);
    if (!candidates.length) return '';
    const step = Math.min(this.previewImageStep, candidates.length - 1);
    return candidates[step] || '';
  }

  onPreviewModalImageError(event: Event) {
    const candidates = this.previewImageCandidates(this.previewCard);
    if (!candidates.length) return;
    const nextStep = this.previewImageStep + 1;
    if (nextStep >= candidates.length) return;
    this.previewImageStep = nextStep;
    const img = event.target as HTMLImageElement | null;
    if (img) img.src = candidates[nextStep];
  }

  // ── Compartir imagen estilo CardIndex ──
  get sellerHandle(): string {
    return this.store?.display_name || (this.store?.username ? '@' + this.store.username : 'Tu tienda');
  }
  get shareStoreItems(): ShareImageItem[] {
    return (this.entries || []).slice(0, 20).map(e => ({
      name: e.card_detail?.name || '',
      image: e.card_detail?.image_url || '',
      quantity: e.selling_quantity || 1,
      foil: !!e.is_foil,
      price: e.price ?? null,
    }));
  }
  get shareWishlistItems(): ShareImageItem[] {
    return (this.wishlistEntries || []).slice(0, 20).map(w => ({
      name: w.card_detail?.name || '',
      image: w.card_detail?.image_url || '',
      quantity: w.desired_quantity || 1,
      foil: false,
      price: null,
    }));
  }
  get shareContactLine(): string {
    return `¿Tienes alguna? Escríbeme · ${this.sellerHandle}`;
  }
  get shareSellingContactLine(): string {
    return `Escríbeme para comprar · ${this.sellerHandle}`;
  }

  get instagramHandle(): string {
    return (this.store?.instagram || '').replace(/^@/, '');
  }
}