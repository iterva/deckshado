import { Component, OnInit, AfterViewInit, OnDestroy, signal, ChangeDetectorRef, HostListener, ViewChild, ElementRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DecimalPipe } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { CarpetaService } from '../../services/carpeta.service';
import { CardService } from '../../services/card.service';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';
import { ShareImageComponent, ShareImageItem } from '../../components/share-image/share-image.component';
import {
  Card, CollectionEntry, WishlistEntry, BinderProfile,
  Edition, CardType, Race, Rarity, CarpetaIds,
} from '../../models';

type Tab = 'carpeta' | 'codex' | 'wishlist' | 'mercado' | 'stats';

@Component({
  selector: 'app-carpeta',
  standalone: true,
  imports: [FormsModule, ThumbnailPipe, DecimalPipe, RouterLink, ShareImageComponent],
  templateUrl: './carpeta.component.html',
  styleUrl: './carpeta.component.scss',
})
export class CarpetaComponent implements OnInit, AfterViewInit, OnDestroy {
  activeTab: Tab = 'carpeta';
  binderProfile: BinderProfile | null = null;

  @HostListener('document:click')
  onDocClick() { this.codexOpenFilter = null; }

  // ── Carpeta (Collection) ──
  collectionEntries: CollectionEntry[] = [];
  collectionTotal = 0;
  collectionPage = 1;
  collectionSearch = '';

  // ── Stats ──
  stats: any = null;
  statsLoading = false;
  statsError: string | null = null;
  collectionLoading = false;
  showSellingOnly = false;
  dirtyEntries = new Map<number, { quantity?: number; price?: number | null; selling_quantity?: number; condition?: string; language?: string; is_foil?: boolean; notes?: string }>();
  previewCard: Card | null = null;

  // ── Codex ──
  codexCards: Card[] = [];
  codexTotal = 0;
  codexPage = 1;
  codexSearch = '';
  codexLoading = false;
  codexHasMore = false;
  editions: Edition[] = [];
  types: CardType[] = [];
  races: Race[] = [];
  rarities: Rarity[] = [];
  selectedFormat = '';
  selectedEditions: string[] = [];
  selectedTypes: string[] = [];
  selectedRaces: string[] = [];
  selectedRarities: string[] = [];
  selectedCard: Card | null = null;
  addQty = 1;
  filtersOpen = true;
  codexOpenFilter: 'edition' | 'type' | 'race' | 'rarity' | null = null;
  @ViewChild('codexSentinel') codexSentinelRef?: ElementRef<HTMLElement>;
  private codexObserver?: IntersectionObserver;

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
  mercadoSelected = new Map<number, CollectionEntry>();

  // Foto real de la carta (por entry.id + slot)
  uploadingPhotoFor: number | null = null;
  uploadingPhotoSlot: 1 | 2 | null = null;
  viewPhotoUrl: string | null = null;

  // ── Tienda config ──
  storeConfigOpen = false;
  storeProfileSaving = false;
  storeProfileSaved = false;
  storeRegenerating = false;

  // ── Bulk import ──
  importOpen = false;
  importText = '';
  importMode: 'add' | 'set' = 'add';
  importing = false;
  importResult: any = null;

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

  ngAfterViewInit() {
    this.setupCodexObserver();
  }

  ngOnDestroy() {
    this.codexObserver?.disconnect();
  }

  switchTab(tab: Tab) {
    this.activeTab = tab;
    if (tab === 'carpeta') this.loadCollection();
    if (tab === 'codex' && !this.codexCards.length) this.loadCodex();
    if (tab === 'wishlist') this.loadWishlist();
    if (tab === 'mercado') this.loadMercado();
    if (tab === 'stats' && !this.stats) this.loadStats();
    queueMicrotask(() => this.setupCodexObserver());
  }

  loadStats() {
    this.statsLoading = true;
    this.statsError = null;
    this.carpetaService.getCollectionStats().subscribe({
      next: (s) => { this.stats = s; this.statsLoading = false; this.cdr.detectChanges(); },
      error: (err) => {
        this.statsLoading = false;
        const status = err?.status ?? '?';
        const detail = err?.error?.detail || err?.message || 'sin detalle';
        this.statsError = `HTTP ${status}: ${detail}`;
        this.cdr.detectChanges();
      },
    });
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

  onFieldChange(entry: CollectionEntry, field: string, value: any) {
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
      condition: (pending.condition ?? entry.condition) as any,
      language: (pending.language ?? entry.language) as any,
      is_foil: pending.is_foil ?? entry.is_foil,
      notes: pending.notes ?? entry.notes,
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

  get filteredEditions(): Edition[] {
    if (!this.selectedFormat) return this.editions;
    return this.editions.filter(e => e.format_code === this.selectedFormat);
  }

  get filteredRaces(): Race[] {
    // Hide 'noraza' / 'Sin Raza' from filter (internal use)
    return this.races.filter(r => r.slug !== 'noraza');
  }

  loadCodex(append = false) {
    this.codexLoading = true;
    this.cardService.getCards({
      search: this.codexSearch || undefined,
      format: this.selectedFormat || undefined,
      edition: this.selectedEditions.length ? this.selectedEditions.join(',') : undefined,
      type: this.selectedTypes.length ? this.selectedTypes.join(',') : undefined,
      deck_race: this.selectedRaces.length === 1 ? this.selectedRaces[0] : undefined,
      race: this.selectedRaces.length > 1 ? this.selectedRaces.join(',') : undefined,
      rarity: this.selectedRarities.length ? this.selectedRarities.join(',') : undefined,
      page: this.codexPage,
    }).subscribe({
      next: res => {
        this.codexCards = append ? [...this.codexCards, ...res.results] : res.results;
        this.codexTotal = res.count;
        this.codexHasMore = !!res.next;
        this.codexLoading = false;
        this.cdr.detectChanges();
        queueMicrotask(() => this.setupCodexObserver());
      },
      error: () => { this.codexLoading = false; this.cdr.detectChanges(); },
    });
  }

  onCodexSearch() { this.codexPage = 1; this.loadCodex(); }
  onCodexFilter() { this.codexPage = 1; this.loadCodex(); }

  onFormatChange() {
    // Clear edition selection when format changes (editions are now different)
    this.selectedEditions = [];
    this.onCodexFilter();
  }

  toggleFilter(arr: string[], value: string) {
    const idx = arr.indexOf(value);
    if (idx >= 0) arr.splice(idx, 1);
    else arr.push(value);
    this.onCodexFilter();
  }

  isSelected(arr: string[], value: string): boolean {
    return arr.includes(value);
  }

  clearFilters() {
    this.selectedFormat = '';
    this.selectedEditions = [];
    this.selectedTypes = [];
    this.selectedRaces = [];
    this.selectedRarities = [];
    this.onCodexFilter();
  }

  toggleCodexPopover(filter: 'edition' | 'type' | 'race' | 'rarity', event: Event) {
    event.stopPropagation();
    this.codexOpenFilter = this.codexOpenFilter === filter ? null : filter;
  }

  codexFilterLabel(filter: 'edition' | 'type' | 'race' | 'rarity'): string {
    const map: Record<string, { arr: string[]; label: string }> = {
      edition: { arr: this.selectedEditions, label: 'Todas las ediciones' },
      type: { arr: this.selectedTypes, label: 'Todos los tipos' },
      race: { arr: this.selectedRaces, label: 'Todas las razas' },
      rarity: { arr: this.selectedRarities, label: 'Todas las frecuencias' },
    };
    const { arr, label } = map[filter];
    if (arr.length === 0) return label;
    if (arr.length === 1) {
      if (filter === 'edition') return this.filteredEditions.find(e => e.slug === arr[0])?.title || arr[0];
      if (filter === 'type') return this.types.find(t => t.slug === arr[0])?.name || arr[0];
      if (filter === 'race') return this.filteredRaces.find(r => r.slug === arr[0])?.name || arr[0];
      return this.rarities.find(r => r.slug === arr[0])?.name || arr[0];
    }
    return `${arr.length} seleccionados`;
  }

  clearCodexFilter(filter: 'edition' | 'type' | 'race' | 'rarity') {
    if (filter === 'edition') this.selectedEditions = [];
    else if (filter === 'type') this.selectedTypes = [];
    else if (filter === 'race') this.selectedRaces = [];
    else this.selectedRarities = [];
    this.onCodexFilter();
  }
  codexPrev() { if (this.codexPage > 1) { this.codexPage--; this.loadCodex(); } }
  codexNext() { if (this.codexPage * 40 < this.codexTotal) { this.codexPage++; this.loadCodex(); } }
  get codexTotalPages() { return Math.ceil(this.codexTotal / 40); }

  loadMoreCodex() {
    if (this.activeTab !== 'codex' || this.codexLoading || !this.codexHasMore) return;
    this.codexPage++;
    this.loadCodex(true);
  }

  private setupCodexObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.codexObserver?.disconnect();
    if (this.activeTab !== 'codex') return;
    const sentinel = this.codexSentinelRef?.nativeElement;
    if (!sentinel) return;
    this.codexObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          this.loadMoreCodex();
          break;
        }
      }
    }, { rootMargin: '280px 0px' });
    this.codexObserver.observe(sentinel);
  }

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
    const items: any[] = [];
    this.dirtyEntries.forEach((pending, entryId) => {
      const entry = this.collectionEntries.find(e => e.id === entryId);
      if (!entry) return;
      items.push({
        card: entry.card_detail.id,
        quantity: pending.quantity ?? entry.quantity,
        price: pending.price !== undefined ? pending.price : entry.price,
        selling_quantity: pending.selling_quantity ?? entry.selling_quantity,
        condition: pending.condition ?? entry.condition,
        language: pending.language ?? entry.language,
        is_foil: pending.is_foil ?? entry.is_foil,
        notes: pending.notes ?? entry.notes,
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

  /** Trigger file input asociado a una entrada. */
  triggerPhotoUpload(entry: CollectionEntry, ev: Event, slot: 1 | 2 = 1) {
    ev.stopPropagation();
    const input = document.getElementById(`photo-input-${entry.id}-${slot}`) as HTMLInputElement | null;
    input?.click();
  }

  /** Subir foto real de la carta a Cloudinary y guardar URL en la entrada. */
  onPhotoSelected(entry: CollectionEntry, ev: Event, slot: 1 | 2 = 1) {
    const input = ev.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      alert('Solo se permiten imágenes.');
      input.value = '';
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      alert('La imagen es muy grande (máx 8 MB).');
      input.value = '';
      return;
    }
    this.uploadingPhotoFor = entry.id;
    this.uploadingPhotoSlot = slot;
    this.cdr.detectChanges();
    this.carpetaService.uploadEntryPhoto(entry.card_detail.id, file, slot).subscribe({
      next: (updated) => {
        entry.photo_url = updated.photo_url;
        entry.photo_url_2 = updated.photo_url_2;
        this.uploadingPhotoFor = null;
        this.uploadingPhotoSlot = null;
        input.value = '';
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error subiendo foto:', err);
        alert('No se pudo subir la foto. Intenta de nuevo.');
        this.uploadingPhotoFor = null;
        this.uploadingPhotoSlot = null;
        input.value = '';
        this.cdr.detectChanges();
      },
    });
  }

  removeMercadoPhoto(entry: CollectionEntry, ev: Event, slot: 1 | 2 = 1) {
    ev.stopPropagation();
    const currentUrl = slot === 2 ? entry.photo_url_2 : entry.photo_url;
    if (!currentUrl) return;
    if (!confirm('¿Quitar esta foto?')) return;
    const patch: any = { card: entry.card_detail.id };
    patch[slot === 2 ? 'photo_url_2' : 'photo_url'] = '';
    this.carpetaService.upsertCollection(patch).subscribe(() => {
      if (slot === 2) entry.photo_url_2 = ''; else entry.photo_url = '';
      this.cdr.detectChanges();
    });
  }

  openPhotoModal(url: string | null | undefined, ev?: Event) {
    if (ev) ev.stopPropagation();
    if (!url) return;
    this.viewPhotoUrl = url;
  }

  closePhotoModal() {
    this.viewPhotoUrl = null;
  }

  // ── Share image (Wishlist + Mercado) ──
  get shareWishlistItems(): ShareImageItem[] {
    return this.wishlistEntries.slice(0, 20).map(w => ({
      name: w.card_detail?.name || '',
      image: w.card_detail?.image_url || '',
      quantity: w.desired_quantity || 1,
      foil: false,
      price: null,
    }));
  }

  get shareMercadoItems(): ShareImageItem[] {
    const source = this.mercadoSelected.size > 0
      ? Array.from(this.mercadoSelected.values())
      : this.mercadoEntries;
    return source.map(e => ({
      name: e.card_detail?.name || '',
      image: e.card_detail?.image_url || '',
      quantity: e.selling_quantity || 1,
      foil: !!e.is_foil,
      price: null,
    }));
  }

  toggleMercadoSelect(entryId: number) {
    if (this.mercadoSelected.has(entryId)) {
      this.mercadoSelected.delete(entryId);
    } else {
      const entry = this.mercadoEntries.find(e => e.id === entryId);
      if (entry) this.mercadoSelected.set(entryId, entry);
    }
  }

  toggleSelectAllMercado() {
    if (this.mercadoSelected.size === this.mercadoEntries.length) {
      this.mercadoSelected.clear();
    } else {
      this.mercadoEntries.forEach(e => this.mercadoSelected.set(e.id, e));
    }
  }

  get shareSellerName(): string {
    return this.binderProfile?.display_name || ('@' + (this.auth.user()?.username || ''));
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

      const el = document.getElementById('mercado-export')!;
      // Render off-screen so user doesn't see it
      el.style.position = 'fixed';
      el.style.left = '-9999px';
      el.style.top = '0';
      el.style.width = '1200px';
      el.style.display = 'block';

      // Wait for images to load
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
      const { jsPDF } = await import('jspdf');

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

      // Generate multi-page PDF from the canvas
      const imgData = canvas.toDataURL('image/jpeg', 0.92);
      const pdfWidth = 210; // A4 width in mm
      const pdfHeight = 297; // A4 height in mm
      const imgWidth = pdfWidth;
      const imgHeight = (canvas.height * pdfWidth) / canvas.width;

      const pdf = new jsPDF('p', 'mm', 'a4');
      let position = 0;

      while (position < imgHeight) {
        if (position > 0) pdf.addPage();
        pdf.addImage(imgData, 'JPEG', 0, -position, imgWidth, imgHeight);
        position += pdfHeight;
      }

      pdf.save(`tienda_${this.auth.user()?.username || 'mercado'}.pdf`);
    } catch (e) {
      console.error('Error exporting mercado:', e);
    }

    this.exportingPdf = false;
    this.cdr.detectChanges();
  }

  // ── Tienda config ──
  saveStoreProfile() {
    if (!this.binderProfile) return;
    this.storeProfileSaving = true;
    const payload = {
      is_store_public: this.binderProfile.is_store_public,
      display_name: this.binderProfile.display_name,
      bio: this.binderProfile.bio,
      city: this.binderProfile.city,
      country: this.binderProfile.country,
      whatsapp: this.binderProfile.whatsapp,
      instagram: this.binderProfile.instagram,
      discord: this.binderProfile.discord,
      email_public: this.binderProfile.email_public,
      payment_methods: this.binderProfile.payment_methods,
      shipping_info: this.binderProfile.shipping_info,
      accepts_trades: this.binderProfile.accepts_trades,
    };
    this.carpetaService.updateBinderProfile(payload).subscribe({
      next: p => {
        this.binderProfile = p;
        this.storeProfileSaving = false;
        this.storeProfileSaved = true;
        this.cdr.detectChanges();
        setTimeout(() => { this.storeProfileSaved = false; this.cdr.detectChanges(); }, 2000);
      },
      error: () => { this.storeProfileSaving = false; this.cdr.detectChanges(); },
    });
  }

  regenerateShareToken() {
    if (!confirm('¿Generar un nuevo enlace privado? El anterior dejará de funcionar.')) return;
    this.storeRegenerating = true;
    this.carpetaService.regenerateShareToken().subscribe({
      next: r => {
        this.shareToken = r.share_token;
        if (this.binderProfile) this.binderProfile.share_token = r.share_token;
        this.storeRegenerating = false;
        this.cdr.detectChanges();
      },
      error: () => { this.storeRegenerating = false; this.cdr.detectChanges(); },
    });
  }

  publicStoreUrl(): string {
    if (!this.binderProfile?.store_slug) return '';
    return `${window.location.origin}/t/${this.binderProfile.store_slug}`;
  }

  privateStoreUrl(): string {
    if (!this.shareToken) return '';
    return `${window.location.origin}/tienda/${this.shareToken}`;
  }

  copyPublicUrl() {
    navigator.clipboard.writeText(this.publicStoreUrl()).then(() => {
      this.shareLinkCopied = true;
      this.cdr.detectChanges();
      setTimeout(() => { this.shareLinkCopied = false; this.cdr.detectChanges(); }, 2000);
    });
  }

  // ── Bulk import ──
  runBulkImport() {
    if (!this.importText.trim()) return;
    this.importing = true;
    this.importResult = null;
    this.carpetaService.bulkImport(this.importText, this.importMode).subscribe({
      next: res => {
        this.importing = false;
        this.importResult = res;
        if (res.added || res.updated) {
          this.loadIds();
          this.loadCollection();
        }
        this.cdr.detectChanges();
      },
      error: () => { this.importing = false; this.cdr.detectChanges(); },
    });
  }

  clearImport() {
    this.importText = '';
    this.importResult = null;
  }
}
