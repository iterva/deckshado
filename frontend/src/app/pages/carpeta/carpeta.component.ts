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

type Tab = 'carpeta' | 'codex' | 'wishlist';

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
  editingEntry: CollectionEntry | null = null;
  editQty = 1;
  editPrice: number | null = null;
  editSelling = 0;

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
    if (tab === 'carpeta' && !this.collectionEntries.length) this.loadCollection();
    if (tab === 'codex' && !this.codexCards.length) this.loadCodex();
    if (tab === 'wishlist' && !this.wishlistEntries.length) this.loadWishlist();
  }

  // ── Binder Profile ──
  loadBinderProfile() {
    this.carpetaService.getBinderProfile().subscribe(p => {
      this.binderProfile = p;
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
  collectionNext() { if (this.collectionPage * 20 < this.collectionTotal) { this.collectionPage++; this.loadCollection(); } }
  get collectionTotalPages() { return Math.ceil(this.collectionTotal / 20); }

  startEdit(entry: CollectionEntry) {
    this.editingEntry = entry;
    this.editQty = entry.quantity;
    this.editPrice = entry.price;
    this.editSelling = entry.selling_quantity;
  }

  cancelEdit() { this.editingEntry = null; }

  saveEdit() {
    if (!this.editingEntry) return;
    this.carpetaService.upsertCollection({
      card: this.editingEntry.card_detail.id,
      quantity: this.editQty,
      price: this.editPrice,
      selling_quantity: this.editSelling,
    }).subscribe(updated => {
      const idx = this.collectionEntries.findIndex(e => e.id === this.editingEntry!.id);
      if (idx >= 0) this.collectionEntries[idx] = updated;
      this.collectionIds[updated.card_detail.id] = updated.quantity;
      this.editingEntry = null;
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
  codexNext() { if (this.codexPage * 20 < this.codexTotal) { this.codexPage++; this.loadCodex(); } }
  get codexTotalPages() { return Math.ceil(this.codexTotal / 20); }

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
  wishlistNext() { if (this.wishlistPage * 20 < this.wishlistTotal) { this.wishlistPage++; this.loadWishlist(); } }
  get wishlistTotalPages() { return Math.ceil(this.wishlistTotal / 20); }

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
}
