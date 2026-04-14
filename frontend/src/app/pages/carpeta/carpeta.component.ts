import { Component, OnInit, signal, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { CarpetaService } from '../../services/carpeta.service';
import { CardService } from '../../services/card.service';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';
import {
  Card, CollectionEntry, WishlistEntry, BinderProfile,
  Edition, CardType, Race, Rarity, CarpetaIds,
} from '../../models';

type Tab = 'carpeta' | 'codex' | 'wishlist' | 'mercado';

@Component({
  selector: 'app-carpeta',
  standalone: true,
  imports: [FormsModule, ThumbnailPipe],
  templateUrl: './carpeta.component.html',
  styleUrl: './carpeta.component.scss',
})
export class CarpetaComponent implements OnInit {
  activeTab: Tab = 'carpeta';
  binderProfile: BinderProfile | null = null;

  // ── Carpeta (Collection) ──
  collectionEntries: CollectionEntry[] = [];
  collectionTotal = 0;
  collectionPage = 1;
  collectionSearch = '';
  collectionLoading = false;
  showSellingOnly = false;
  dirtyEntries = new Map<number, { quantity?: number; price?: number | null; selling_quantity?: number }>();
  previewCard: Card | null = null;

  // ── Codex ──
  codexCards: Card[] = [];
  codexTotal = 0;
  codexPage = 1;
  codexSearch = '';
  codexLoading = false;
  editions: Edition[] = [];
  types: CardType[] = [];
  races: Race[] = [];
  rarities: Rarity[] = [];
  selectedEdition = '';
  selectedType = '';
  selectedRace = '';
  selectedRarity = '';
  selectedCard: Card | null = null;
  addQty = 1;

  // ── Wishlist ──
  wishlistEntries: WishlistEntry[] = [];
  wishlistTotal = 0;
  wishlistPage = 1;
  wishlistSearch = '';
  wishlistLoading = false;

  // ── IDs for quick status checks ──
  collectionIds: { [cardId: number]: number } = {};
  wishlistIds = new Set<number>();

  // ── Mercado (store) ──
  mercadoEntries: CollectionEntry[] = [];
  mercadoTotal = 0;
  mercadoPage = 1;
  mercadoSearch = '';
  mercadoLoading = false;
  mercadoDirty = new Map<number, { price?: number | null; selling_quantity?: number }>();
  shareToken = '';
  shareLinkCopied = false;
  batchSaving = false;
  exportingPdf = false;
  mercadoAllEntries: CollectionEntry[] = [];

  constructor(
    public auth: AuthService,
    private carpetaService: CarpetaService,
    private cardService: CardService,
    private cdr: ChangeDetectorRef,
    private router: Router,
  ) {}

  ngOnInit() {
    if (!this.auth.isAuthenticated()) {
      this.router.navigate(['/login']);
      return;
    }
    this.loadBinderProfile();
    this.loadIds();
    this.loadCollection();
    this.loadFilters();
  }

  switchTab(tab: Tab) {
    this.activeTab = tab;
    if (tab === 'carpeta') this.loadCollection();
    if (tab === 'codex' && !this.codexCards.length) this.loadCodex();
    if (tab === 'wishlist') this.loadWishlist();
    if (tab === 'mercado') this.loadMercado();
  }

  // ── Binder Profile ──
  loadBinderProfile() {
    this.carpetaService.getBinderProfile().subscribe(p => {
      this.binderProfile = p;
      this.shareToken = p.share_token;
      this.cdr.detectChanges();
    });
  }

  onAvatarFileChange(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.carpetaService.uploadBinderAvatar(file).subscribe(p => {
      this.binderProfile = p;
      this.cdr.detectChanges();
    });
  }

  // ── IDs ──
  loadIds() {
    this.carpetaService.getMyIds().subscribe(ids => {
      this.collectionIds = ids.collection;
      this.wishlistIds = new Set(ids.wishlist);
      this.cdr.detectChanges();
    });
  }

  isInCollection(cardId: number): boolean {
    return cardId in this.collectionIds;
  }

  isInWishlist(cardId: number): boolean {
    return this.wishlistIds.has(cardId);
  }

  collectionQty(cardId: number): number {
    return this.collectionIds[cardId] || 0;
  }

  // ── Collection ──
  loadCollection() {
    this.collectionLoading = true;
    this.carpetaService.getCollection(
      this.collectionPage,
      this.collectionSearch || undefined,
      this.showSellingOnly,
    ).subscribe({
      next: res => {
        this.collectionEntries = res.results;
        this.collectionTotal = res.count;
        this.collectionLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.collectionLoading = false; this.cdr.detectChanges(); },
    });
  }

  onCollectionSearch() { this.collectionPage = 1; this.loadCollection(); }
  toggleSellingFilter() { this.showSellingOnly = !this.showSellingOnly; this.collectionPage = 1; this.loadCollection(); }
  collectionPrev() { if (this.collectionPage > 1) { this.collectionPage--; this.loadCollection(); } }
  collectionNext() { if (this.collectionPage * 40 < this.collectionTotal) { this.collectionPage++; this.loadCollection(); } }
  get collectionTotalPages() { return Math.ceil(this.collectionTotal / 40); }

  onFieldChange(entry: CollectionEntry, field: string, value: number) {
    let pending = this.dirtyEntries.get(entry.id) || {};
    (pending as any)[field] = value;
    // Cap selling_quantity to quantity
    const qty = pending.quantity ?? entry.quantity;
    const sell = pending.selling_quantity ?? entry.selling_quantity;
    if (sell > qty) {
      pending.selling_quantity = qty;
    }
    this.dirtyEntries.set(entry.id, pending);
  }

  saveEntry(entry: CollectionEntry) {
    const pending = this.dirtyEntries.get(entry.id);
    if (!pending) return;
    this.carpetaService.upsertCollection({
      card: entry.card_detail.id,
      quantity: pending.quantity ?? entry.quantity,
      price: pending.price !== undefined ? pending.price : entry.price,
      selling_quantity: pending.selling_quantity ?? entry.selling_quantity,
    }).subscribe(updated => {
      const idx = this.collectionEntries.findIndex(e => e.id === entry.id);
      if (idx >= 0) this.collectionEntries[idx] = updated;
      this.collectionIds[updated.card_detail.id] = updated.quantity;
      this.dirtyEntries.delete(entry.id);
      this.cdr.detectChanges();
    });
  }

  removeFromCollection(entry: CollectionEntry) {
    this.carpetaService.removeFromCollection(entry.card_detail.id).subscribe(() => {
      this.collectionEntries = this.collectionEntries.filter(e => e.id !== entry.id);
      delete this.collectionIds[entry.card_detail.id];
      this.collectionTotal--;
      this.cdr.detectChanges();
    });
  }

  // ── Codex ──
  loadFilters() {
    this.cardService.getEditions().subscribe(d => { this.editions = d; this.cdr.detectChanges(); });
    this.cardService.getTypes().subscribe(d => { this.types = d; this.cdr.detectChanges(); });
    this.cardService.getRaces().subscribe(d => { this.races = d; this.cdr.detectChanges(); });
    this.cardService.getRarities().subscribe(d => { this.rarities = d; this.cdr.detectChanges(); });
  }

  loadCodex() {
    this.codexLoading = true;
    this.cardService.getCards({
      search: this.codexSearch || undefined,
      edition: this.selectedEdition || undefined,
      type: this.selectedType || undefined,
      race: this.selectedRace || undefined,
      rarity: this.selectedRarity || undefined,
      page: this.codexPage,
    }).subscribe({
      next: res => {
        this.codexCards = res.results;
        this.codexTotal = res.count;
        this.codexLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.codexLoading = false; this.cdr.detectChanges(); },
    });
  }

  onCodexSearch() { this.codexPage = 1; this.loadCodex(); }
  onCodexFilter() { this.codexPage = 1; this.loadCodex(); }
  codexPrev() { if (this.codexPage > 1) { this.codexPage--; this.loadCodex(); } }
  codexNext() { if (this.codexPage * 40 < this.codexTotal) { this.codexPage++; this.loadCodex(); } }
  get codexTotalPages() { return Math.ceil(this.codexTotal / 40); }

  selectCodexCard(card: Card) {
    this.selectedCard = this.selectedCard?.id === card.id ? null : card;
    this.addQty = 1;
  }

  addToCollection(card: Card) {
    this.carpetaService.upsertCollection({ card: card.id, quantity: this.addQty }).subscribe(entry => {
      this.collectionIds[card.id] = entry.quantity;
      this.selectedCard = null;
      this.cdr.detectChanges();
    });
  }

  quickAddToCollection(card: Card, event: MouseEvent) {
    event.stopPropagation();
    const newQty = (this.collectionIds[card.id] || 0) + 1;
    this.carpetaService.upsertCollection({ card: card.id, quantity: newQty }).subscribe(entry => {
      this.collectionIds[card.id] = entry.quantity;
      this.cdr.detectChanges();
    });
  }

  toggleWishlist(card: Card, event: MouseEvent) {
    event.stopPropagation();
    this.carpetaService.toggleWishlist(card.id).subscribe(res => {
      if (res.wishlisted) {
        this.wishlistIds.add(card.id);
      } else {
        this.wishlistIds.delete(card.id);
      }
      this.cdr.detectChanges();
    });
  }

  // ── Wishlist ──
  loadWishlist() {
    this.wishlistLoading = true;
    this.carpetaService.getWishlist(this.wishlistPage, this.wishlistSearch || undefined).subscribe({
      next: res => {
        this.wishlistEntries = res.results;
        this.wishlistTotal = res.count;
        this.wishlistLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.wishlistLoading = false; this.cdr.detectChanges(); },
    });
  }

  onWishlistSearch() { this.wishlistPage = 1; this.loadWishlist(); }
  wishlistPrev() { if (this.wishlistPage > 1) { this.wishlistPage--; this.loadWishlist(); } }
  wishlistNext() { if (this.wishlistPage * 40 < this.wishlistTotal) { this.wishlistPage++; this.loadWishlist(); } }
  get wishlistTotalPages() { return Math.ceil(this.wishlistTotal / 40); }

  updateWishlistQty(entry: WishlistEntry, qty: number) {
    if (qty < 1) return;
    this.carpetaService.updateWishlist(entry.card_detail.id, qty).subscribe(updated => {
      const idx = this.wishlistEntries.findIndex(e => e.id === entry.id);
      if (idx >= 0) this.wishlistEntries[idx] = updated;
      this.cdr.detectChanges();
    });
  }

  removeFromWishlist(entry: WishlistEntry) {
    this.carpetaService.toggleWishlist(entry.card_detail.id).subscribe(() => {
      this.wishlistEntries = this.wishlistEntries.filter(e => e.id !== entry.id);
      this.wishlistIds.delete(entry.card_detail.id);
      this.wishlistTotal--;
      this.cdr.detectChanges();
    });
  }

  // ── Batch Save (Carpeta tab) ──
  saveAllChanges() {
    if (this.dirtyEntries.size === 0) return;
    this.batchSaving = true;
    const items: { card: number; quantity?: number; price?: number | null; selling_quantity?: number }[] = [];
    this.dirtyEntries.forEach((pending, entryId) => {
      const entry = this.collectionEntries.find(e => e.id === entryId);
      if (!entry) return;
      items.push({
        card: entry.card_detail.id,
        quantity: pending.quantity ?? entry.quantity,
        price: pending.price !== undefined ? pending.price : entry.price,
        selling_quantity: pending.selling_quantity ?? entry.selling_quantity,
      });
    });
    this.carpetaService.batchUpsertCollection(items).subscribe({
      next: () => {
        this.dirtyEntries.clear();
        this.batchSaving = false;
        this.loadCollection();
      },
      error: () => { this.batchSaving = false; this.cdr.detectChanges(); },
    });
  }

  // ── Mercado ──
  loadMercado() {
    this.mercadoLoading = true;
    this.carpetaService.getCollection(
      this.mercadoPage,
      this.mercadoSearch || undefined,
      true, // selling only
    ).subscribe({
      next: res => {
        this.mercadoEntries = res.results;
        this.mercadoTotal = res.count;
        this.mercadoLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.mercadoLoading = false; this.cdr.detectChanges(); },
    });
  }

  onMercadoSearch() { this.mercadoPage = 1; this.loadMercado(); }
  mercadoPrev() { if (this.mercadoPage > 1) { this.mercadoPage--; this.loadMercado(); } }
  mercadoNext() { if (this.mercadoPage * 40 < this.mercadoTotal) { this.mercadoPage++; this.loadMercado(); } }
  get mercadoTotalPages() { return Math.ceil(this.mercadoTotal / 40); }

  onMercadoFieldChange(entry: CollectionEntry, field: string, value: number) {
    let pending = this.mercadoDirty.get(entry.id) || {};
    (pending as any)[field] = value;
    // Cap selling_quantity to quantity
    const sell = pending.selling_quantity ?? entry.selling_quantity;
    if (sell > entry.quantity) {
      pending.selling_quantity = entry.quantity;
    }
    this.mercadoDirty.set(entry.id, pending);
  }

  saveMercadoChanges() {
    if (this.mercadoDirty.size === 0) return;
    this.batchSaving = true;
    const items: { card: number; price?: number | null; selling_quantity?: number }[] = [];
    this.mercadoDirty.forEach((pending, entryId) => {
      const entry = this.mercadoEntries.find(e => e.id === entryId);
      if (!entry) return;
      items.push({
        card: entry.card_detail.id,
        price: pending.price !== undefined ? pending.price : entry.price,
        selling_quantity: pending.selling_quantity ?? entry.selling_quantity,
      });
    });
    this.carpetaService.batchUpsertCollection(items).subscribe({
      next: () => {
        this.mercadoDirty.clear();
        this.batchSaving = false;
        this.loadMercado();
      },
      error: () => { this.batchSaving = false; this.cdr.detectChanges(); },
    });
  }

  copyShareLink() {
    if (!this.shareToken) return;
    const url = `${window.location.origin}/tienda/${this.shareToken}`;
    navigator.clipboard.writeText(url).then(() => {
      this.shareLinkCopied = true;
      this.cdr.detectChanges();
      setTimeout(() => { this.shareLinkCopied = false; this.cdr.detectChanges(); }, 2000);
    });
  }

  removeMercadoEntry(entry: CollectionEntry) {
    // Set selling_quantity to 0 (removes from mercado but keeps in collection)
    this.carpetaService.upsertCollection({
      card: entry.card_detail.id,
      selling_quantity: 0,
    }).subscribe(() => {
      this.mercadoEntries = this.mercadoEntries.filter(e => e.id !== entry.id);
      this.mercadoTotal--;
      this.cdr.detectChanges();
    });
  }

  async exportMercadoPdf() {
    this.exportingPdf = true;
    this.cdr.detectChanges();

    try {
      // Load ALL selling entries (no pagination) for the export
      const allPages: CollectionEntry[] = [];
      let page = 1;
      let hasMore = true;
      while (hasMore) {
        const res = await this.carpetaService.getCollection(page, undefined, true).toPromise();
        if (res) {
          allPages.push(...res.results);
          hasMore = page * 40 < res.count;
          page++;
        } else {
          hasMore = false;
        }
      }
      this.mercadoAllEntries = allPages;
      this.cdr.detectChanges();

      // Wait for images to load
      const el = document.getElementById('mercado-export')!;
      el.style.position = 'absolute';
      el.style.left = '0';
      el.style.top = '0';
      el.style.width = '1200px';
      el.style.display = 'block';

      const imgs = Array.from(el.querySelectorAll('img')) as HTMLImageElement[];
      await Promise.all(imgs.map(img => {
        if (img.complete && img.naturalWidth > 0) return Promise.resolve();
        return new Promise<void>((resolve) => {
          img.onload = () => resolve();
          img.onerror = () => resolve();
          img.loading = 'eager';
          img.src = img.src;
        });
      }));

      const html2canvas = (await import('html2canvas')).default;
      const canvas = await html2canvas(el, {
        backgroundColor: '#0f0f23',
        useCORS: true,
        allowTaint: true,
        scale: 2,
        windowWidth: 1200,
        windowHeight: el.scrollHeight,
      });

      el.style.position = '';
      el.style.left = '';
      el.style.top = '';
      el.style.width = '';
      el.style.display = '';

      const link = document.createElement('a');
      link.download = `tienda_${this.auth.user()?.username || 'mercado'}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (e) {
      console.error('Error exporting mercado:', e);
    }

    this.exportingPdf = false;
    this.cdr.detectChanges();
  }
}
