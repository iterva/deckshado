import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DecimalPipe } from '@angular/common';
import { CarpetaService, StoreFilters } from '../../services/carpeta.service';
import { CardService } from '../../services/card.service';
import { AuthService } from '../../services/auth.service';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';
import { CollectionEntry, Card, PublicBinderProfile, Edition, Race, Rarity, CardType, WishlistEntry } from '../../models';

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
  imports: [FormsModule, ThumbnailPipe, DecimalPipe, RouterLink],
  templateUrl: './tienda.component.html',
  styleUrl: './tienda.component.scss',
})
export class TiendaComponent implements OnInit {
  token = '';
  store: PublicBinderProfile | null = null;
  entries: CollectionEntry[] = [];
  total = 0;
  loading = false;
  notFound = false;
  previewCard: Card | null = null;
  viewPhotoUrl: string | null = null;
  showContactModal = false;
  showCart = false;

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

  // Cart (localStorage scoped per token/slug)
  cart: CartItem[] = [];

  constructor(
    private route: ActivatedRoute,
    private carpetaService: CarpetaService,
    private cardService: CardService,
    public auth: AuthService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.token = this.route.snapshot.paramMap.get('token') || this.route.snapshot.paramMap.get('slug') || '';
    if (!this.token) { this.notFound = true; return; }
    const dt = this.route.snapshot.data?.['defaultTab'];
    if (dt === 'wishlist') this.activeTab = 'wishlist';
    this.loadCart();
    this.loadFilters();
    this.loadStore();
    if (this.activeTab === 'wishlist') this.loadWishlist();
  }

  loadFilters() {
    this.cardService.getEditions().subscribe(d => { this.editions = d; this.cdr.detectChanges(); });
    this.cardService.getRaces().subscribe(d => { this.races = d; this.cdr.detectChanges(); });
    this.cardService.getRarities().subscribe(d => { this.rarities = d; this.cdr.detectChanges(); });
    this.cardService.getTypes().subscribe(d => { this.types = d; this.cdr.detectChanges(); });
  }

  loadStore() {
    this.loading = true;
    this.carpetaService.getPublicStore(this.token, this.filters).subscribe({
      next: res => {
        this.entries = res.results;
        this.total = res.count;
        this.store = res.store;
        this.loading = false;
        this.syncCartAvailability();
        this.cdr.detectChanges();
      },
      error: () => { this.notFound = true; this.loading = false; this.cdr.detectChanges(); },
    });
  }

  applyFilter() { this.filters.page = 1; this.loadStore(); }
  resetFilters() {
    this.filters = { page: 1, ordering: '-id' };
    this.loadStore();
  }
  prevPage() { if ((this.filters.page || 1) > 1) { this.filters.page = (this.filters.page || 1) - 1; this.loadStore(); } }
  nextPage() { if ((this.filters.page || 1) * 40 < this.total) { this.filters.page = (this.filters.page || 1) + 1; this.loadStore(); } }
  get totalPages() { return Math.ceil(this.total / 40); }

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
    if (!this.store?.whatsapp) return;
    const number = this.store.whatsapp.replace(/[^0-9]/g, '');
    const text = encodeURIComponent(this.buildOrderText());
    window.open(`https://wa.me/${number}?text=${text}`, '_blank');
  }

  copyOrder() {
    navigator.clipboard.writeText(this.buildOrderText());
  }

  // ── Tabs / Wishlist ──
  switchTab(tab: 'store' | 'wishlist') {
    if (this.activeTab === tab) return;
    this.activeTab = tab;
    if (tab === 'wishlist' && !this.wishlistLoaded) this.loadWishlist();
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

  get instagramHandle(): string {
    return (this.store?.instagram || '').replace(/^@/, '');
  }
}