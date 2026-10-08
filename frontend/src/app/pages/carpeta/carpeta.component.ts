import {
  Component, OnInit, AfterViewInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef,
  ElementRef, ViewChild, HostListener, inject, signal, computed,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DecimalPipe, DatePipe } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { CarpetaService } from '../../services/carpeta.service';
import { CardService } from '../../services/card.service';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';
import { ShareImageComponent, ShareImageItem } from '../../components/share-image/share-image.component';
import { TourOverlayComponent } from '../../components/tour-overlay/tour-overlay.component';
import { TourService, TourStep } from '../../services/tour.service';
import { CarpetaGuideModalComponent } from './components/guide-modal/guide-modal.component';
import QRCode from 'qrcode';
import {
  Card, CollectionEntry, WishlistEntry, BinderProfile,
  Edition, CardType, Race, Rarity,
  StoreOrder, StoreOrderStatus,
  MylWorkspace, MylStoreCollaboratorPermission, MylStorePermissionFlags,
} from '../../models';

import { IconComponent } from '../../components/icon/icon.component';
import { ConfirmDialogService } from '../../services/confirm-dialog.service';

type Tab = 'carpeta' | 'codex' | 'wishlist' | 'mercado' | 'pedidos' | 'stats' | 'permisos';

type CollaboratorRole = 'lector' | 'gestor_mercado' | 'administrador' | 'personalizado';

const ROLE_PRESETS: Record<Exclude<CollaboratorRole, 'personalizado'>, Array<keyof MylStorePermissionFlags>> = {
  lector: ['view_collection', 'view_orders', 'view_history'],
  gestor_mercado: ['view_collection', 'view_orders', 'view_history', 'edit_market', 'remove_from_market', 'accept_orders', 'reject_orders'],
  administrador: ['view_collection', 'edit_collection', 'delete_collection', 'edit_market', 'remove_from_market', 'view_orders', 'view_history', 'accept_orders', 'reject_orders', 'manage_permissions'],
};

function permsMatchRole(perms: Partial<MylStorePermissionFlags>, allKeys: Array<keyof MylStorePermissionFlags>, role: Exclude<CollaboratorRole, 'personalizado'>): boolean {
  const active = new Set(ROLE_PRESETS[role]);
  return allKeys.every(key => !!perms[key] === active.has(key));
}

function detectCollaboratorRole(perms: Partial<MylStorePermissionFlags>, allKeys: Array<keyof MylStorePermissionFlags>): CollaboratorRole {
  if (permsMatchRole(perms, allKeys, 'administrador')) return 'administrador';
  if (permsMatchRole(perms, allKeys, 'gestor_mercado')) return 'gestor_mercado';
  if (permsMatchRole(perms, allKeys, 'lector')) return 'lector';
  return 'personalizado';
}

const TOUR_STEPS: Record<string, TourStep[]> = {
  carpeta: [
    { target: '[data-tour="carpeta-search"]', title: 'Buscar en tu carpeta', description: 'Escribe el nombre de una carta para filtrar rápidamente lo que ya posees.' },
    { target: '[data-tour="carpeta-filter-selling"]', title: 'Solo en venta', description: 'Filtra la grilla para ver únicamente las cartas que tienes listadas en el mercado.' },
    { target: '[data-tour="carpeta-bulk-import"]', title: 'Importar lista', description: 'Pega una lista de cartas (una por línea) para agregarlas todas de una vez a tu carpeta.' },
    { target: '[data-tour="carpeta-grid"]', title: 'Tu colección', description: 'Cada carta muestra cuántas copias tienes y si está en venta. Tócala para editar cantidad, precio, idioma, foil y notas.' },
  ],
  codex: [
    { target: '[data-tour="codex-search"]', title: 'Buscar cartas', description: 'Escribe el nombre de cualquier carta de Mitos y Leyendas para encontrarla en el catálogo completo.' },
    { target: '[data-tour="codex-filters"]', title: 'Filtrar por formato, edición, tipo, raza o frecuencia', description: 'Combina estos filtros para acotar la búsqueda a exactamente lo que buscas.' },
    { target: '[data-tour="codex-grid"]', title: 'Agregar o desear', description: 'Al pasar el mouse sobre una carta aparecen acciones para añadirla a tu carpeta o guardarla en tu wishlist.' },
  ],
  wishlist: [
    { target: '[data-tour="wishlist-search"]', title: 'Buscar en tu wishlist', description: 'Filtra rápidamente las cartas que marcaste como deseadas.' },
    { target: '[data-tour="wishlist-share"]', title: 'Genera tu imagen de "busco"', description: 'El botón de imagen genera una foto lista para compartir con las cartas de tu wishlist.' },
    { target: '[data-tour="wishlist-grid"]', title: 'Tus cartas deseadas', description: 'Ajusta cuántas copias quieres de cada una.' },
  ],
  mercado: [
    { target: '[data-tour="mercado-config"]', title: 'Configurar tienda', description: 'Define nombre público, ciudad, WhatsApp, métodos de pago y más para que los compradores confíen en tu tienda.' },
    { target: '[data-tour="mercado-toolbar"]', title: 'Herramientas de tienda', description: 'Copia el link para compartir, genera un QR o exporta un PDF con tu catálogo en venta.' },
    { target: '[data-tour="mercado-grid"]', title: 'Cartas en venta', description: 'Toca cualquier carta para actualizar su precio, cantidad en venta o subir una foto real del ejemplar.' },
  ],
  pedidos: [
    { target: '[data-tour="pedidos-pills"]', title: 'Filtra por estado', description: 'Cambia entre Pendientes, Todos, Completados y Cancelados para revisar el estado de tus ventas.' },
    { target: '[data-tour="pedidos-table"]', title: 'Gestiona cada pedido', description: 'Toca una fila para ver el detalle completo, o usa los íconos ✓/✕ para aceptar o cancelar un pedido pendiente directamente.' },
  ],
  stats: [
    { target: '[data-tour="stats-overview"]', title: 'Resumen de tu colección', description: 'Cartas totales, únicas y el valor estimado según los precios que asignaste.' },
  ],
};

interface DirtyPatch {
  quantity?: number;
  price?: number | null;
  selling_quantity?: number;
  condition?: string;
  language?: string;
  is_foil?: boolean;
  notes?: string;
}

@Component({
  selector: 'app-carpeta',
  imports: [
    FormsModule, ThumbnailPipe, DecimalPipe, DatePipe, RouterLink, ShareImageComponent, IconComponent,
    TourOverlayComponent, CarpetaGuideModalComponent,
  ],
  templateUrl: './carpeta.component.html',
  styleUrl: './carpeta.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CarpetaComponent implements OnInit, AfterViewInit, OnDestroy {
  public readonly auth = inject(AuthService);
  private readonly carpetaService = inject(CarpetaService);
  private readonly cardService = inject(CardService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly dialog = inject(ConfirmDialogService);
  private queryParamSub?: Subscription;

  @HostListener('document:click')
  onDocClick() {
    this.codexOpenFilter.set(null);
    this.openNavGroup.set(null);
  }

  @HostListener('window:scroll')
  onWindowScroll() { this.tryInfiniteScrollFallback(); }

  @HostListener('window:resize')
  onWindowResize() { this.tryInfiniteScrollFallback(); }

  activeTab = signal<Tab>('carpeta');
  binderProfile = signal<BinderProfile | null>(null);

  // ── Colaboración / "Carpetas Compartidas" ──
  workspaceMode = signal(false);
  workspacesLoading = signal(false);
  workspaces = signal<MylWorkspace[]>([]);
  selectedWorkspaceId = signal<number | null>(null);
  selectedWorkspace = computed(() => this.workspaces().find(w => w.store_profile_id === this.selectedWorkspaceId()) || null);
  selectedWorkspacePermissions = computed(() => this.selectedWorkspace()?.permissions || null);

  private wsId(): number | undefined {
    return this.workspaceMode() ? (this.selectedWorkspaceId() ?? undefined) : undefined;
  }

  hasPermission(key: keyof MylStorePermissionFlags): boolean {
    if (!this.workspaceMode()) return true;
    return !!this.selectedWorkspacePermissions()?.[key];
  }

  canUseWorkspaceContent(): boolean {
    return !this.workspaceMode() || !!this.selectedWorkspaceId();
  }

  canManagePermissions(): boolean {
    return this.hasPermission('manage_permissions');
  }

  showAdminNavGroup(): boolean {
    return !this.workspaceMode()
      || this.hasPermission('view_orders')
      || this.hasPermission('view_history')
      || this.canManagePermissions();
  }

  goToCollaborate() {
    this.router.navigate(['/carpeta/colaborar']);
  }

  goToMyFolder() {
    this.router.navigate(['/carpeta']);
  }

  loadWorkspaces() {
    this.workspacesLoading.set(true);
    this.carpetaService.listWorkspaces().subscribe({
      next: (res) => {
        this.workspaces.set(res.results || []);
        this.workspacesLoading.set(false);
        const current = this.selectedWorkspaceId();
        if (current == null || !res.results.some(w => w.store_profile_id === current)) {
          const firstOther = res.results.find(w => !w.is_owner);
          if (firstOther) this.onWorkspaceChange(String(firstOther.store_profile_id));
        }
        this.cdr.markForCheck();
      },
      error: () => { this.workspacesLoading.set(false); this.cdr.markForCheck(); },
    });
  }

  workspaceLabel(ws: MylWorkspace): string {
    return ws.is_owner ? `${ws.owner_username} (yo)` : ws.owner_username;
  }

  onWorkspaceChange(value: string) {
    const id = parseInt(value, 10);
    if (!id) return;
    this.selectedWorkspaceId.set(id);
    this.activeTab.set('carpeta');
    this.loadCollection();
    this.loadMercado();
  }

  // ── Permisos: gestión de colaboradores ──
  workspacePermissionsLoading = signal(false);
  permissionsSaving = signal(false);
  collaboratorPermissions = signal<MylStoreCollaboratorPermission[]>([]);
  newCollaboratorUser = '';
  newCollaboratorRole = signal<CollaboratorRole>('personalizado');
  readonly permissionKeys: Array<keyof MylStorePermissionFlags> = [
    'view_collection', 'edit_collection', 'delete_collection',
    'edit_market', 'remove_from_market',
    'view_orders', 'view_history', 'accept_orders', 'reject_orders',
    'manage_permissions',
  ];
  newCollaboratorPerms = signal<MylStorePermissionFlags>({
    view_collection: true,
    edit_collection: true,
    delete_collection: false,
    edit_market: true,
    remove_from_market: false,
    view_orders: true,
    view_history: true,
    accept_orders: false,
    reject_orders: false,
    manage_permissions: false,
  });

  onNewCollaboratorRoleChange(role: CollaboratorRole) {
    this.newCollaboratorRole.set(role);
    if (role === 'personalizado') return;
    const active = new Set<keyof MylStorePermissionFlags>(ROLE_PRESETS[role]);
    const next = {} as MylStorePermissionFlags;
    for (const key of this.permissionKeys) next[key] = active.has(key);
    this.newCollaboratorPerms.set(next);
  }

  toggleNewCollaboratorPerm(key: keyof MylStorePermissionFlags, value: boolean) {
    this.newCollaboratorPerms.update(p => ({ ...p, [key]: value }));
    this.newCollaboratorRole.set('personalizado');
  }

  collaboratorRoleFor(row: MylStoreCollaboratorPermission): CollaboratorRole {
    const effective: Partial<MylStorePermissionFlags> = {};
    for (const key of this.permissionKeys) effective[key] = this.collaboratorPermValue(row, key);
    return detectCollaboratorRole(effective, this.permissionKeys);
  }

  collaboratorPermValue(row: MylStoreCollaboratorPermission, key: keyof MylStorePermissionFlags): boolean {
    return !!row.permissions[key];
  }

  onCollaboratorRoleChange(row: MylStoreCollaboratorPermission, role: CollaboratorRole) {
    if (role === 'personalizado') return;
    const active = new Set<keyof MylStorePermissionFlags>(ROLE_PRESETS[role]);
    for (const key of this.permissionKeys) {
      this.toggleCollaboratorPerm(row.id, key, active.has(key));
    }
  }

  private collaboratorDirty = new Map<number, Partial<MylStorePermissionFlags>>();

  toggleCollaboratorPerm(permissionId: number, key: keyof MylStorePermissionFlags, value: boolean) {
    const pending = this.collaboratorDirty.get(permissionId) || {};
    pending[key] = value;
    this.collaboratorDirty.set(permissionId, pending);
    this.collaboratorPermissions.update(list =>
      list.map(row => row.id === permissionId
        ? { ...row, permissions: { ...row.permissions, [key]: value } }
        : row));
  }

  loadWorkspacePermissions() {
    const targetId = this.canManagePermissions() ? this.managedProfileId() : null;
    if (!targetId) return;
    this.workspacePermissionsLoading.set(true);
    this.carpetaService.listWorkspacePermissions(targetId).subscribe({
      next: (res) => {
        this.collaboratorPermissions.set(res.results || []);
        this.workspacePermissionsLoading.set(false);
        this.cdr.markForCheck();
      },
      error: () => { this.workspacePermissionsLoading.set(false); this.cdr.markForCheck(); },
    });
  }

  private ownProfileId(): number | null {
    const mine = this.workspaces().find(w => w.is_owner);
    return mine?.store_profile_id ?? this.binderProfile()?.id ?? null;
  }

  private managedProfileId(): number | null {
    return this.workspaceMode() ? this.selectedWorkspaceId() : this.ownProfileId();
  }

  addCollaborator() {
    const profileId = this.managedProfileId();
    const identifier = this.newCollaboratorUser.trim();
    if (!profileId || !identifier) return;
    this.permissionsSaving.set(true);
    this.carpetaService.upsertWorkspacePermission(profileId, identifier, this.newCollaboratorPerms()).subscribe({
      next: () => {
        this.newCollaboratorUser = '';
        this.permissionsSaving.set(false);
        this.loadWorkspacePermissions();
      },
      error: (err) => {
        this.permissionsSaving.set(false);
        alert(err?.error?.detail || 'No se pudo agregar al colaborador.');
        this.cdr.markForCheck();
      },
    });
  }

  saveCollaboratorPerms(row: MylStoreCollaboratorPermission) {
    const profileId = this.managedProfileId();
    const pending = this.collaboratorDirty.get(row.id);
    if (!profileId || !pending) return;
    this.permissionsSaving.set(true);
    this.carpetaService.updateWorkspacePermission(profileId, row.id, pending).subscribe({
      next: () => {
        this.collaboratorDirty.delete(row.id);
        this.permissionsSaving.set(false);
        this.loadWorkspacePermissions();
      },
      error: (err) => {
        this.permissionsSaving.set(false);
        alert(err?.error?.detail || 'No se pudo actualizar el permiso.');
        this.cdr.markForCheck();
      },
    });
  }

  isCollaboratorDirty(row: MylStoreCollaboratorPermission): boolean {
    return this.collaboratorDirty.has(row.id);
  }

  permissionLabel(key: keyof MylStorePermissionFlags): string {
    const labels: Record<keyof MylStorePermissionFlags, string> = {
      view_collection: 'Ver carpeta',
      edit_collection: 'Editar carpeta',
      delete_collection: 'Eliminar de carpeta',
      edit_market: 'Editar venta/precio',
      remove_from_market: 'Quitar de venta',
      view_orders: 'Ver pedidos',
      view_history: 'Ver historial',
      accept_orders: 'Aceptar pedidos',
      reject_orders: 'Rechazar pedidos',
      manage_permissions: 'Gestionar permisos',
    };
    return labels[key];
  }

  removeCollaborator(row: MylStoreCollaboratorPermission) {
    const profileId = this.managedProfileId();
    if (!profileId) return;
    if (!confirm(`¿Quitar el acceso de ${row.username}?`)) return;
    this.carpetaService.deleteWorkspacePermission(profileId, row.id).subscribe({
      next: () => this.loadWorkspacePermissions(),
      error: (err) => alert(err?.error?.detail || 'No se pudo quitar el acceso.'),
    });
  }

  // ── Carpeta (Collection) ──
  collectionEntries = signal<CollectionEntry[]>([]);
  collectionTotal = signal(0);
  collectionPage = signal(1);
  collectionHasMore = signal(false);
  collectionSearch = '';
  @ViewChild('collectionSentinel') collectionSentinelRef?: ElementRef<HTMLElement>;
  private collectionObserver?: IntersectionObserver;

  // ── Stats ──
  stats = signal<any>(null);
  statsLoading = signal(false);
  statsError = signal<string | null>(null);
  collectionLoading = signal(false);
  showSellingOnly = signal(false);
  dirtyEntries = new Map<number, DirtyPatch>();
  previewCard = signal<Card | null>(null);

  // ── Codex ──
  codexCards = signal<Card[]>([]);
  codexTotal = signal(0);
  codexPage = signal(1);
  codexSearch = '';
  codexLoading = signal(false);
  codexHasMore = signal(false);
  editions = signal<Edition[]>([]);
  types = signal<CardType[]>([]);
  races = signal<Race[]>([]);
  rarities = signal<Rarity[]>([]);
  selectedFormat = '';
  selectedEditions: string[] = [];
  selectedTypes: string[] = [];
  selectedRaces: string[] = [];
  selectedRarities: string[] = [];
  selectedCard = signal<Card | null>(null);
  addQty = 1;
  quickEditEntry = signal<CollectionEntry | null>(null);
  quickEditMercadoEntry = signal<CollectionEntry | null>(null);

  openQuickEdit(entry: CollectionEntry) { this.quickEditEntry.set(entry); }
  closeQuickEdit() { this.quickEditEntry.set(null); }
  openMercadoQuickEdit(entry: CollectionEntry) { this.quickEditMercadoEntry.set(entry); }
  closeMercadoQuickEdit() { this.quickEditMercadoEntry.set(null); }

  // ── Navegación agrupada (dropdowns) ──
  openNavGroup = signal<'coleccion' | 'admin' | null>(null);

  toggleNavGroup(group: 'coleccion' | 'admin', ev: Event) {
    ev.stopPropagation();
    this.openNavGroup.update(curr => (curr === group ? null : group));
  }

  closeNavGroup() {
    this.openNavGroup.set(null);
  }

  isTabInGroup(group: 'coleccion' | 'admin'): boolean {
    const t = this.activeTab();
    if (group === 'coleccion') return t === 'carpeta' || t === 'codex' || t === 'wishlist';
    return t === 'pedidos' || t === 'stats';
  }

  // ── Guía interactiva ──
  showGuide = signal(false);
  completedTours = signal<Set<string>>(new Set());
  private readonly tourService = inject(TourService);

  private loadTours() {
    this.carpetaService.getTours().subscribe({
      next: (res) => this.completedTours.set(new Set(res.completed)),
      error: () => {},
    });
  }

  onStartCardTour(tourId: string) {
    const steps = TOUR_STEPS[tourId];
    if (!steps) return;
    const targetTab = tourId as Tab;
    this.switchTab(targetTab);
    setTimeout(() => {
      this.tourService.start(tourId, steps, () => this.markTourComplete(tourId));
    }, 150);
  }

  private markTourComplete(tourId: string) {
    this.carpetaService.completeTour(tourId).subscribe({
      next: (res) => this.completedTours.set(new Set(res.completed)),
      error: () => this.completedTours.update(s => new Set([...s, tourId])),
    });
  }
  filtersOpen = signal(true);
  codexOpenFilter = signal<'edition' | 'type' | 'race' | 'rarity' | null>(null);
  @ViewChild('codexSentinel') codexSentinelRef?: ElementRef<HTMLElement>;
  private codexObserver?: IntersectionObserver;

  filteredEditions = computed(() => {
    const fmt = this.selectedFormatSignal();
    const eds = this.editions();
    if (!fmt) return eds;
    return eds.filter(e => e.format_code === fmt);
  });
  filteredRaces = computed(() => this.races().filter(r => r.slug !== 'noraza'));
  // selectedFormat is ngModel-bound (plain field); mirrored into a signal so `filteredEditions` stays reactive.
  private selectedFormatSignal = signal('');

  codexTotalPages = computed(() => Math.ceil(this.codexTotal() / 40));
  collectionTotalPages = computed(() => Math.ceil(this.collectionTotal() / 40));
  wishlistTotalPages = computed(() => Math.ceil(this.wishlistTotal() / 40));
  mercadoTotalPages = computed(() => Math.ceil(this.mercadoTotal() / 40));

  // ── Wishlist ──
  wishlistEntries = signal<WishlistEntry[]>([]);
  wishlistTotal = signal(0);
  wishlistPage = signal(1);
  wishlistHasMore = signal(false);
  wishlistSearch = '';
  wishlistLoading = signal(false);
  @ViewChild('wishlistSentinel') wishlistSentinelRef?: ElementRef<HTMLElement>;
  private wishlistObserver?: IntersectionObserver;

  // ── IDs for quick status checks ──
  private collectionIds: { [cardId: number]: number } = {};
  private wishlistIds = new Set<number>();

  // ── Mercado (store) ──
  mercadoEntries = signal<CollectionEntry[]>([]);
  mercadoTotal = signal(0);
  mercadoPage = signal(1);
  mercadoHasMore = signal(false);
  mercadoSearch = '';
  mercadoLoading = signal(false);
  mercadoDirty = new Map<number, { price?: number | null; selling_quantity?: number }>();
  @ViewChild('mercadoSentinel') mercadoSentinelRef?: ElementRef<HTMLElement>;
  private mercadoObserver?: IntersectionObserver;
  private contentScrollEl: HTMLElement | null = null;
  shareToken = '';
  shareLinkCopied = signal(false);
  qrDownloading = signal(false);
  batchSaving = signal(false);
  exportingPdf = signal(false);
  mercadoAllEntries = signal<CollectionEntry[]>([]);
  mercadoSelected = new Map<number, CollectionEntry>();
  /** Wishlist: ids elegidos para la imagen "busco" (vacío = todas). */
  wishlistSelected = signal<ReadonlySet<number>>(new Set());

  // ── Gestión de pedidos (unificada: Pedidos + Historial) ──
  pendingOrders = signal<StoreOrder[]>([]);
  historyOrders = signal<StoreOrder[]>([]);
  ordersLoading = signal(false);
  historyLoading = signal(false);
  ordersPill = signal<'pendientes' | 'todos' | 'completados' | 'cancelados'>('pendientes');
  orderDetail = signal<StoreOrder | null>(null);
  cancelOrderTarget = signal<StoreOrder | null>(null);
  cancelOrderReason = '';
  cancelOrderSubmitting = signal(false);

  ordersForPill = computed<StoreOrder[]>(() => {
    const pill = this.ordersPill();
    if (pill === 'pendientes') return this.pendingOrders();
    if (pill === 'completados') return this.historyOrders().filter(o => o.status === 'accepted');
    if (pill === 'cancelados') return this.historyOrders().filter(o => o.status === 'cancelled');
    return [...this.pendingOrders(), ...this.historyOrders().filter(o => o.status !== 'pending')];
  });

  assignedByEntry: Record<number, number> = {};

  // Foto real de la carta (por entry.id + slot)
  uploadingPhotoFor = signal<number | null>(null);
  uploadingPhotoSlot = signal<1 | 2 | null>(null);
  viewPhotoUrl = signal<string | null>(null);

  // ── Tienda config ──
  storeConfigOpen = signal(false);
  storeProfileSaving = signal(false);
  storeProfileSaved = signal(false);
  storeRegenerating = signal(false);

  // ── Bulk import ──
  importOpen = signal(false);
  importText = '';
  importMode: 'add' | 'set' = 'add';
  importing = signal(false);
  importResult = signal<any>(null);

  getSellingCount(): number {
    return this.collectionEntries().filter(e => (e.selling_quantity || 0) > 0).length;
  }

  ngOnInit() {
    if (!this.auth.isAuthenticated()) {
      this.router.navigate(['/login']);
      return;
    }

    this.workspaceMode.set(!!this.route.snapshot.data?.['workspaceMode']);

    if (this.workspaceMode()) {
      this.loadWorkspaces();
    } else {
      this.loadBinderProfile();
      this.loadIds();
      this.loadCollection();
      this.loadTours();
    }
    this.loadFilters();

    const validTabs: Tab[] = ['carpeta', 'codex', 'wishlist', 'mercado', 'pedidos', 'stats', 'permisos'];
    this.queryParamSub = this.route.queryParamMap.subscribe(params => {
      const requestedTab = params.get('tab');
      if (requestedTab && (validTabs as string[]).includes(requestedTab) && requestedTab !== this.activeTab()) {
        this.switchTab(requestedTab as Tab);
      }
    });
  }

  ngAfterViewInit() {
    this.setupCollectionObserver();
    this.setupCodexObserver();
    this.setupWishlistObserver();
    this.setupMercadoObserver();
    this.attachContentScrollListener();
    this.tryInfiniteScrollFallback();
  }

  ngOnDestroy() {
    this.collectionObserver?.disconnect();
    this.codexObserver?.disconnect();
    this.wishlistObserver?.disconnect();
    this.mercadoObserver?.disconnect();
    this.detachContentScrollListener();
    this.queryParamSub?.unsubscribe();
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

  switchTab(tab: Tab) {
    this.activeTab.set(tab);
    if (tab === 'carpeta') this.loadCollection();
    if (tab === 'codex' && !this.codexCards().length) this.loadCodex();
    if (tab === 'wishlist') this.loadWishlist();
    if (tab === 'mercado') this.loadMercado();
    if (tab === 'pedidos') { this.loadPendingOrders(); this.loadHistoryOrders(); }
    if (tab === 'stats' && !this.stats()) this.loadStats();
    if (tab === 'permisos') this.loadWorkspacePermissions();
    queueMicrotask(() => {
      this.setupCollectionObserver();
      this.setupCodexObserver();
      this.setupWishlistObserver();
      this.setupMercadoObserver();
      this.tryInfiniteScrollFallback();
    });
  }

  loadStats() {
    this.statsLoading.set(true);
    this.statsError.set(null);
    this.carpetaService.getCollectionStats().subscribe({
      next: (s) => { this.stats.set(s); this.statsLoading.set(false); this.cdr.markForCheck(); },
      error: (err) => {
        this.statsLoading.set(false);
        const status = err?.status ?? '?';
        const detail = err?.error?.detail || err?.message || 'sin detalle';
        this.statsError.set(`HTTP ${status}: ${detail}`);
        this.cdr.markForCheck();
      },
    });
  }

  // ── Binder Profile ──
  loadBinderProfile() {
    this.carpetaService.getBinderProfile().subscribe(p => {
      this.binderProfile.set(p);
      this.shareToken = p.share_token;
      this.cdr.markForCheck();
    });
  }

  onAvatarFileChange(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.carpetaService.uploadBinderAvatar(file).subscribe(p => {
      this.binderProfile.set(p);
      this.cdr.markForCheck();
    });
  }

  // ── IDs ──
  loadIds() {
    this.carpetaService.getMyIds().subscribe(ids => {
      this.collectionIds = ids.collection;
      this.wishlistIds = new Set(ids.wishlist);
      this.cdr.markForCheck();
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
    this.collectionPage.set(1);
    this.collectionEntries.set([]);
    this.collectionHasMore.set(false);
    this.fetchCollectionPage();
  }

  onCollectionSearch() { this.collectionPage.set(1); this.loadCollection(); }
  toggleSellingFilter() { this.showSellingOnly.update(v => !v); this.collectionPage.set(1); this.loadCollection(); }
  loadMoreCollection() {
    if (this.activeTab() !== 'carpeta' || this.collectionLoading() || !this.collectionHasMore()) return;
    this.collectionPage.update(p => p + 1);
    this.fetchCollectionPage(true);
  }
  private fetchCollectionPage(append = false) {
    this.collectionLoading.set(true);
    this.carpetaService.getCollection(
      this.collectionPage(),
      this.collectionSearch || undefined,
      this.showSellingOnly(),
      this.wsId(),
    ).subscribe({
      next: res => {
        this.collectionEntries.set(append ? [...this.collectionEntries(), ...res.results] : res.results);
        this.collectionTotal.set(res.count);
        this.collectionHasMore.set(!!res.next);
        this.collectionLoading.set(false);
        this.cdr.markForCheck();
        queueMicrotask(() => {
          this.setupCollectionObserver();
          this.tryInfiniteScrollFallback();
        });
      },
      error: () => { this.collectionLoading.set(false); this.cdr.markForCheck(); },
    });
  }
  collectionPrev() { if (this.collectionPage() > 1) { this.collectionPage.update(p => p - 1); this.loadCollection(); } }
  collectionNext() { if (this.collectionPage() * 40 < this.collectionTotal()) { this.collectionPage.update(p => p + 1); this.loadCollection(); } }

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
    this.cdr.markForCheck();
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
    }, { store_profile_id: this.wsId() }).subscribe({ next: updated => {
      const entries = this.collectionEntries();
      const idx = entries.findIndex(e => e.id === entry.id);
      if (idx >= 0) {
        const next = [...entries];
        next[idx] = updated;
        this.collectionEntries.set(next);
      }
      this.collectionIds[updated.card_detail.id] = updated.quantity;
      this.dirtyEntries.delete(entry.id);
      this.cdr.markForCheck();
    }, error: err => this.showSaveError(err, 'No se pudieron guardar los cambios.') });
  }

  removeFromCollection(entry: CollectionEntry) {
    this.carpetaService.removeFromCollection(entry.card_detail.id, this.wsId()).subscribe(() => {
      this.collectionEntries.set(this.collectionEntries().filter(e => e.id !== entry.id));
      delete this.collectionIds[entry.card_detail.id];
      this.collectionTotal.update(t => t - 1);
      this.cdr.markForCheck();
    });
  }

  // ── Codex ──
  loadFilters() {
    this.cardService.getEditions().subscribe(d => { this.editions.set(d); this.cdr.markForCheck(); });
    this.cardService.getTypes().subscribe(d => { this.types.set(d); this.cdr.markForCheck(); });
    this.cardService.getRaces().subscribe(d => { this.races.set(d); this.cdr.markForCheck(); });
    this.cardService.getRarities().subscribe(d => { this.rarities.set(d); this.cdr.markForCheck(); });
  }

  loadCodex(append = false) {
    this.codexLoading.set(true);
    this.cardService.getCards({
      search: this.codexSearch || undefined,
      format: this.selectedFormat || undefined,
      edition: this.selectedEditions.length ? this.selectedEditions.join(',') : undefined,
      type: this.selectedTypes.length ? this.selectedTypes.join(',') : undefined,
      deck_race: this.selectedRaces.length === 1 ? this.selectedRaces[0] : undefined,
      race: this.selectedRaces.length > 1 ? this.selectedRaces.join(',') : undefined,
      rarity: this.selectedRarities.length ? this.selectedRarities.join(',') : undefined,
      page: this.codexPage(),
    }).subscribe({
      next: res => {
        this.codexCards.set(append ? [...this.codexCards(), ...res.results] : res.results);
        this.codexTotal.set(res.count);
        this.codexHasMore.set(!!res.next);
        this.codexLoading.set(false);
        this.cdr.markForCheck();
        queueMicrotask(() => {
          this.setupCodexObserver();
          this.tryInfiniteScrollFallback();
        });
      },
      error: () => { this.codexLoading.set(false); this.cdr.markForCheck(); },
    });
  }

  onCodexSearch() { this.codexPage.set(1); this.loadCodex(); }
  onCodexFilter() { this.codexPage.set(1); this.loadCodex(); }

  onFormatChange() {
    // Clear edition selection when format changes (editions are now different)
    this.selectedEditions = [];
    this.selectedFormatSignal.set(this.selectedFormat);
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
    this.selectedFormatSignal.set('');
    this.selectedEditions = [];
    this.selectedTypes = [];
    this.selectedRaces = [];
    this.selectedRarities = [];
    this.onCodexFilter();
  }

  toggleCodexPopover(filter: 'edition' | 'type' | 'race' | 'rarity', event: Event) {
    event.stopPropagation();
    this.codexOpenFilter.update(curr => (curr === filter ? null : filter));
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
      if (filter === 'edition') return this.filteredEditions().find(e => e.slug === arr[0])?.title || arr[0];
      if (filter === 'type') return this.types().find(t => t.slug === arr[0])?.name || arr[0];
      if (filter === 'race') return this.filteredRaces().find(r => r.slug === arr[0])?.name || arr[0];
      return this.rarities().find(r => r.slug === arr[0])?.name || arr[0];
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
  codexPrev() { if (this.codexPage() > 1) { this.codexPage.update(p => p - 1); this.loadCodex(); } }
  codexNext() { if (this.codexPage() * 40 < this.codexTotal()) { this.codexPage.update(p => p + 1); this.loadCodex(); } }

  loadMoreCodex() {
    if (this.activeTab() !== 'codex' || this.codexLoading() || !this.codexHasMore()) return;
    this.codexPage.update(p => p + 1);
    this.loadCodex(true);
  }

  private setupCodexObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.codexObserver?.disconnect();
    if (this.activeTab() !== 'codex') return;
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

  private setupCollectionObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.collectionObserver?.disconnect();
    if (this.activeTab() !== 'carpeta') return;
    const sentinel = this.collectionSentinelRef?.nativeElement;
    if (!sentinel) return;
    this.collectionObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          this.loadMoreCollection();
          break;
        }
      }
    }, { rootMargin: '280px 0px' });
    this.collectionObserver.observe(sentinel);
  }

  selectCodexCard(card: Card) {
    this.selectedCard.update(curr => (curr?.id === card.id ? null : card));
    this.addQty = 1;
  }

  /** Muestra el mensaje del backend (400 de validación) en vez de fallar en silencio. */
  private showSaveError(err: any, fallback: string) {
    const body = err?.error;
    let message = fallback;
    if (typeof body?.detail === 'string') {
      message = body.detail;
    } else if (body && typeof body === 'object') {
      const first = Object.values(body)[0];
      if (typeof first === 'string') message = first;
      else if (Array.isArray(first) && typeof first[0] === 'string') message = first[0];
    }
    this.dialog.open({
      title: 'No se pudo guardar',
      message,
      actions: [{ value: 'ok', label: 'Entendido', style: 'primary' }],
    });
  }

  addToCollection(card: Card) {
    const qty = Math.floor(Number(this.addQty));
    if (!Number.isFinite(qty) || qty < 1) {
      this.showSaveError(null, 'La cantidad debe ser al menos 1.');
      return;
    }
    this.carpetaService.upsertCollection({ card: card.id, quantity: qty }, { store_profile_id: this.wsId() }).subscribe({
      next: entry => {
        this.collectionIds[card.id] = entry.quantity;
        this.selectedCard.set(null);
        this.cdr.markForCheck();
      },
      error: err => this.showSaveError(err, 'No se pudo añadir la carta.'),
    });
  }

  quickAddToCollection(card: Card, event: MouseEvent) {
    event.stopPropagation();
    const newQty = (this.collectionIds[card.id] || 0) + 1;
    this.carpetaService.upsertCollection({ card: card.id, quantity: newQty }, { store_profile_id: this.wsId() }).subscribe({
      next: entry => {
        this.collectionIds[card.id] = entry.quantity;
        this.cdr.markForCheck();
      },
      error: err => this.showSaveError(err, 'No se pudo añadir la carta.'),
    });
  }

  /** Desde Colección: agrega (si hace falta) y marca la carta para venta, luego abre el quick-edit para fijar precio. */
  sellFromCodex(card: Card, ev?: MouseEvent) {
    ev?.stopPropagation();
    const qty = this.collectionIds[card.id] || 1;
    this.carpetaService.upsertCollection({ card: card.id, quantity: qty, selling_quantity: qty }, { store_profile_id: this.wsId() }).subscribe({
      next: (updated) => {
        this.collectionIds[updated.card_detail.id] = updated.quantity;
        this.switchTab('carpeta');
        this.openQuickEdit(updated);
        this.cdr.markForCheck();
      },
      error: (err) => alert(err?.error?.detail || 'No se pudo preparar la carta para venta.'),
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
      this.cdr.markForCheck();
    });
  }

  // ── Wishlist ──
  loadWishlist() {
    this.wishlistPage.set(1);
    this.wishlistEntries.set([]);
    this.wishlistHasMore.set(false);
    this.fetchWishlistPage();
  }

  onWishlistSearch() { this.wishlistPage.set(1); this.loadWishlist(); }
  loadMoreWishlist() {
    if (this.activeTab() !== 'wishlist' || this.wishlistLoading() || !this.wishlistHasMore()) return;
    this.wishlistPage.update(p => p + 1);
    this.fetchWishlistPage(true);
  }
  private fetchWishlistPage(append = false) {
    this.wishlistLoading.set(true);
    this.carpetaService.getWishlist(this.wishlistPage(), this.wishlistSearch || undefined).subscribe({
      next: res => {
        this.wishlistEntries.set(append ? [...this.wishlistEntries(), ...res.results] : res.results);
        this.wishlistTotal.set(res.count);
        this.wishlistHasMore.set(!!res.next);
        this.wishlistLoading.set(false);
        this.cdr.markForCheck();
        queueMicrotask(() => {
          this.setupWishlistObserver();
          this.tryInfiniteScrollFallback();
        });
      },
      error: () => { this.wishlistLoading.set(false); this.cdr.markForCheck(); },
    });
  }
  wishlistPrev() { if (this.wishlistPage() > 1) { this.wishlistPage.update(p => p - 1); this.loadWishlist(); } }
  wishlistNext() { if (this.wishlistPage() * 40 < this.wishlistTotal()) { this.wishlistPage.update(p => p + 1); this.loadWishlist(); } }

  private setupWishlistObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.wishlistObserver?.disconnect();
    if (this.activeTab() !== 'wishlist') return;
    const sentinel = this.wishlistSentinelRef?.nativeElement;
    if (!sentinel) return;
    this.wishlistObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          this.loadMoreWishlist();
          break;
        }
      }
    }, { rootMargin: '280px 0px' });
    this.wishlistObserver.observe(sentinel);
  }

  private setupMercadoObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.mercadoObserver?.disconnect();
    if (this.activeTab() !== 'mercado') return;
    const sentinel = this.mercadoSentinelRef?.nativeElement;
    if (!sentinel) return;
    this.mercadoObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          this.loadMoreMercado();
          break;
        }
      }
    }, { rootMargin: '280px 0px' });
    this.mercadoObserver.observe(sentinel);
  }

  private tryInfiniteScrollFallback() {
    if (!this.isNearPageBottom()) return;
    const tab = this.activeTab();
    if (tab === 'carpeta') this.loadMoreCollection();
    if (tab === 'codex') this.loadMoreCodex();
    if (tab === 'wishlist') this.loadMoreWishlist();
    if (tab === 'mercado') this.loadMoreMercado();
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

  updateWishlistQty(entry: WishlistEntry, qty: number) {
    if (qty < 1) return;
    this.carpetaService.updateWishlist(entry.card_detail.id, qty).subscribe(updated => {
      const entries = this.wishlistEntries();
      const idx = entries.findIndex(e => e.id === entry.id);
      if (idx >= 0) {
        const next = [...entries];
        next[idx] = updated;
        this.wishlistEntries.set(next);
      }
      this.cdr.markForCheck();
    });
  }

  removeFromWishlist(entry: WishlistEntry) {
    this.carpetaService.toggleWishlist(entry.card_detail.id).subscribe(() => {
      this.wishlistEntries.set(this.wishlistEntries().filter(e => e.id !== entry.id));
      this.wishlistIds.delete(entry.card_detail.id);
      if (this.wishlistSelected().has(entry.id)) this.toggleWishlistSelect(entry.id);
      this.wishlistTotal.update(t => t - 1);
      this.cdr.markForCheck();
    });
  }

  // ── Batch Save (Carpeta tab) ──
  saveAllChanges() {
    if (this.dirtyEntries.size === 0) return;
    this.batchSaving.set(true);
    const items: any[] = [];
    const entries = this.collectionEntries();
    this.dirtyEntries.forEach((pending, entryId) => {
      const entry = entries.find(e => e.id === entryId);
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
    this.carpetaService.batchUpsertCollection(items, { store_profile_id: this.wsId() }).subscribe({
      next: () => {
        this.dirtyEntries.clear();
        this.batchSaving.set(false);
        this.loadCollection();
      },
      error: () => { this.batchSaving.set(false); this.cdr.markForCheck(); },
    });
  }

  // ── Mercado ──
  loadMercado() {
    this.mercadoPage.set(1);
    this.mercadoEntries.set([]);
    this.mercadoHasMore.set(false);
    this.mercadoSelected.clear();
    this.fetchMercadoPage();
  }

  loadMoreMercado() {
    if (this.activeTab() !== 'mercado' || this.mercadoLoading() || !this.mercadoHasMore()) return;
    this.mercadoPage.update(p => p + 1);
    this.fetchMercadoPage(true);
  }

  private fetchMercadoPage(append = false) {
    this.mercadoLoading.set(true);
    this.carpetaService.getCollection(
      this.mercadoPage(),
      this.mercadoSearch || undefined,
      true, // selling only
      this.wsId(),
    ).subscribe({
      next: res => {
        this.mercadoEntries.set(append ? [...this.mercadoEntries(), ...res.results] : res.results);
        this.mercadoTotal.set(res.count);
        this.mercadoHasMore.set(!!res.next);
        this.mercadoLoading.set(false);
        if (!append) this.loadAssignedSummary();
        this.cdr.markForCheck();
        queueMicrotask(() => {
          this.setupMercadoObserver();
          this.tryInfiniteScrollFallback();
        });
      },
      error: () => { this.mercadoLoading.set(false); this.cdr.markForCheck(); },
    });
  }

  loadAssignedSummary() {
    this.carpetaService.getMyOrderAssignedSummary(this.wsId()).subscribe({
      next: (res) => {
        this.assignedByEntry = res.assigned_by_entry || {};
        this.cdr.markForCheck();
      },
      error: () => {
        this.assignedByEntry = {};
        this.cdr.markForCheck();
      },
    });
  }

  assignedForEntry(entryId: number): number {
    return this.assignedByEntry[entryId] || 0;
  }

  onMercadoSearch() { this.mercadoPage.set(1); this.loadMercado(); }
  mercadoPrev() { if (this.mercadoPage() > 1) { this.mercadoPage.update(p => p - 1); this.loadMercado(); } }
  mercadoNext() { if (this.mercadoPage() * 40 < this.mercadoTotal()) { this.mercadoPage.update(p => p + 1); this.loadMercado(); } }

  showFloatingSaveButton = computed(() => {
    return (this.activeTab() === 'carpeta' && this.dirtyEntries.size > 0)
      || (this.activeTab() === 'mercado' && this.mercadoDirty.size > 0);
  });

  get floatingSaveLabel(): string {
    if (this.batchSaving()) return '⏳ Guardando...';
    if (this.activeTab() === 'carpeta') return `💾 Guardar carpeta (${this.dirtyEntries.size})`;
    if (this.activeTab() === 'mercado') return `💾 Guardar tienda (${this.mercadoDirty.size})`;
    return '💾 Guardar cambios';
  }

  onFloatingSaveClick() {
    if (this.batchSaving()) return;
    if (this.activeTab() === 'carpeta') { this.saveAllChanges(); return; }
    if (this.activeTab() === 'mercado') { this.saveMercadoChanges(); }
  }

  onMercadoFieldChange(entry: CollectionEntry, field: string, value: number) {
    let pending = this.mercadoDirty.get(entry.id) || {};
    (pending as any)[field] = value;
    // Cap selling_quantity to quantity
    const sell = pending.selling_quantity ?? entry.selling_quantity;
    if (sell > entry.quantity) {
      pending.selling_quantity = entry.quantity;
    }
    this.mercadoDirty.set(entry.id, pending);
    this.cdr.markForCheck();
  }

  saveMercadoChanges() {
    if (this.mercadoDirty.size === 0) return;
    this.batchSaving.set(true);
    const items: { card: number; price?: number | null; selling_quantity?: number }[] = [];
    const entries = this.mercadoEntries();
    this.mercadoDirty.forEach((pending, entryId) => {
      const entry = entries.find(e => e.id === entryId);
      if (!entry) return;
      items.push({
        card: entry.card_detail.id,
        price: pending.price !== undefined ? pending.price : entry.price,
        selling_quantity: pending.selling_quantity ?? entry.selling_quantity,
      });
    });
    this.carpetaService.batchUpsertCollection(items, { store_profile_id: this.wsId() }).subscribe({
      next: () => {
        this.mercadoDirty.clear();
        this.batchSaving.set(false);
        this.loadMercado();
        this.loadPendingOrders();
      },
      error: () => { this.batchSaving.set(false); this.cdr.markForCheck(); },
    });
  }

  loadPendingOrders() {
    this.ordersLoading.set(true);
    this.carpetaService.listMyStoreOrders({ status: 'pending', page: 1, store_profile_id: this.wsId() }).subscribe({
      next: (res) => {
        this.pendingOrders.set(res.results || []);
        this.ordersLoading.set(false);
        this.loadAssignedSummary();
        this.cdr.markForCheck();
      },
      error: () => {
        this.ordersLoading.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  loadHistoryOrders() {
    this.historyLoading.set(true);
    this.carpetaService.listMyStoreOrders({ status: 'history', page: 1, store_profile_id: this.wsId() }).subscribe({
      next: (res) => {
        this.historyOrders.set((res.results || []).filter(o => o.status !== 'pending'));
        this.historyLoading.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.historyLoading.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  orderStatusLabel(status: StoreOrderStatus): string {
    if (status === 'pending') return 'Pendiente';
    if (status === 'accepted') return 'Aceptado';
    return 'Cancelado';
  }

  acceptOrder(order: StoreOrder) {
    this.carpetaService.acceptStoreOrder(order.id).subscribe({
      next: () => {
        this.pendingOrders.update(arr => arr.filter(o => o.id !== order.id));
        this.orderDetail.set(null);
        this.loadHistoryOrders();
        this.loadMercado();
        this.cdr.markForCheck();
      },
      error: (err) => {
        alert(err?.error?.detail || 'No se pudo aceptar el pedido.');
      },
    });
  }

  cancelOrder(order: StoreOrder) {
    this.cancelOrderReason = '';
    this.cancelOrderTarget.set(order);
  }

  closeCancelOrderModal() {
    if (this.cancelOrderSubmitting()) return;
    this.cancelOrderTarget.set(null);
    this.cancelOrderReason = '';
  }

  confirmCancelOrder() {
    const order = this.cancelOrderTarget();
    const reason = this.cancelOrderReason.trim();
    if (!order || !reason) return;
    this.cancelOrderSubmitting.set(true);
    this.carpetaService.cancelStoreOrder(order.id, reason).subscribe({
      next: () => {
        this.pendingOrders.update(arr => arr.filter(o => o.id !== order.id));
        this.orderDetail.set(null);
        this.cancelOrderSubmitting.set(false);
        this.cancelOrderTarget.set(null);
        this.cancelOrderReason = '';
        this.loadHistoryOrders();
        this.loadMercado();
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.cancelOrderSubmitting.set(false);
        alert(err?.error?.detail || 'No se pudo cancelar el pedido.');
        this.cdr.markForCheck();
      },
    });
  }

  copyShareLink() {
    if (!this.shareToken) return;
    const url = `${window.location.origin}/tienda/${this.shareToken}`;
    navigator.clipboard.writeText(url).then(() => {
      this.shareLinkCopied.set(true);
      this.cdr.markForCheck();
      setTimeout(() => { this.shareLinkCopied.set(false); this.cdr.markForCheck(); }, 2000);
    });
  }

  async downloadStoreQr() {
    if (!this.shareToken) return;
    const url = `${window.location.origin}/tienda/${this.shareToken}`;
    this.qrDownloading.set(true);
    this.cdr.markForCheck();
    try {
      const qrDataUrl = await QRCode.toDataURL(url, {
        width: 1024,
        margin: 2,
        errorCorrectionLevel: 'H',
        color: { dark: '#0f172a', light: '#ffffff' },
      });
      const dataUrl = await this.composeQrWithCenteredLogo(qrDataUrl, this.getStoreQrLogoUrl());
      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = `myl-tienda-qr-${this.auth.user()?.username || 'shadowforge'}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      console.error('QR generation error:', e);
      alert('No se pudo generar el QR. Intenta de nuevo.');
    } finally {
      this.qrDownloading.set(false);
      this.cdr.markForCheck();
    }
  }

  private getStoreQrLogoUrl(): string | null {
    const binderAvatar = (this.binderProfile()?.binder_avatar_url || '').trim();
    if (binderAvatar) return binderAvatar;
    const userAvatar = (this.auth.user()?.avatar_url || '').trim();
    return userAvatar || null;
  }

  private async composeQrWithCenteredLogo(qrDataUrl: string, logoUrl: string | null): Promise<string> {
    if (!logoUrl) return qrDataUrl;
    try {
      const [qrImg, logoImg] = await Promise.all([
        this.loadImageForQr(qrDataUrl),
        this.loadImageForQr(logoUrl),
      ]);

      const size = qrImg.naturalWidth || qrImg.width || 1024;
      const canvas = document.createElement('canvas');
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext('2d');
      if (!ctx) return qrDataUrl;

      ctx.drawImage(qrImg, 0, 0, size, size);

      const badgeSize = Math.round(size * 0.24);
      const badgeRadius = Math.round(badgeSize / 2);
      const centerX = Math.round(size / 2);
      const centerY = Math.round(size / 2);
      const imagePadding = Math.max(6, Math.round(badgeSize * 0.08));

      ctx.save();
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(centerX, centerY, badgeRadius, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      ctx.save();
      ctx.beginPath();
      ctx.arc(centerX, centerY, badgeRadius - imagePadding, 0, Math.PI * 2);
      ctx.clip();
      ctx.drawImage(
        logoImg,
        centerX - badgeRadius + imagePadding,
        centerY - badgeRadius + imagePadding,
        badgeSize - imagePadding * 2,
        badgeSize - imagePadding * 2,
      );
      ctx.restore();

      return canvas.toDataURL('image/png');
    } catch {
      return qrDataUrl;
    }
  }

  private loadImageForQr(src: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.referrerPolicy = 'no-referrer';
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error('No se pudo cargar imagen para QR'));
      img.src = src;
    });
  }

  removeMercadoEntry(entry: CollectionEntry) {
    // Set selling_quantity to 0 (removes from mercado but keeps in collection)
    this.carpetaService.upsertCollection({
      card: entry.card_detail.id,
      selling_quantity: 0,
    }, { store_profile_id: this.wsId() }).subscribe(() => {
      this.mercadoEntries.set(this.mercadoEntries().filter(e => e.id !== entry.id));
      this.mercadoTotal.update(t => t - 1);
      this.cdr.markForCheck();
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
    this.uploadingPhotoFor.set(entry.id);
    this.uploadingPhotoSlot.set(slot);
    this.cdr.markForCheck();
    this.carpetaService.uploadEntryPhoto(entry.card_detail.id, file, slot, this.wsId()).subscribe({
      next: (updated) => {
        entry.photo_url = updated.photo_url;
        entry.photo_url_2 = updated.photo_url_2;
        this.uploadingPhotoFor.set(null);
        this.uploadingPhotoSlot.set(null);
        input.value = '';
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error subiendo foto:', err);
        alert('No se pudo subir la foto. Intenta de nuevo.');
        this.uploadingPhotoFor.set(null);
        this.uploadingPhotoSlot.set(null);
        input.value = '';
        this.cdr.markForCheck();
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
    this.carpetaService.upsertCollection(patch, { store_profile_id: this.wsId() }).subscribe(() => {
      if (slot === 2) entry.photo_url_2 = ''; else entry.photo_url = '';
      this.cdr.markForCheck();
    });
  }

  openPhotoModal(url: string | null | undefined, ev?: Event) {
    if (ev) ev.stopPropagation();
    if (!url) return;
    this.viewPhotoUrl.set(url);
  }

  closePhotoModal() {
    this.viewPhotoUrl.set(null);
  }

  // ── Share image (Wishlist + Mercado) ──
  get shareWishlistItems(): ShareImageItem[] {
    const selected = this.wishlistSelected();
    const source = selected.size > 0
      ? this.wishlistEntries().filter(w => selected.has(w.id))
      : this.wishlistEntries();
    return source.map(w => ({
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
      : this.mercadoEntries();
    return source.map(e => ({
      name: e.card_detail?.name || '',
      image: e.card_detail?.image_url || '',
      quantity: e.selling_quantity || 1,
      foil: !!e.is_foil,
      price: null,
    }));
  }

  toggleWishlistSelect(entryId: number) {
    this.wishlistSelected.update(prev => {
      const next = new Set(prev);
      if (next.has(entryId)) next.delete(entryId);
      else next.add(entryId);
      return next;
    });
  }

  toggleSelectAllWishlist() {
    const entries = this.wishlistEntries();
    this.wishlistSelected.set(
      this.wishlistSelected().size === entries.length ? new Set() : new Set(entries.map(e => e.id)),
    );
  }

  toggleMercadoSelect(entryId: number) {
    if (this.mercadoSelected.has(entryId)) {
      this.mercadoSelected.delete(entryId);
    } else {
      const entry = this.mercadoEntries().find(e => e.id === entryId);
      if (entry) this.mercadoSelected.set(entryId, entry);
    }
    this.cdr.markForCheck();
  }

  toggleSelectAllMercado() {
    if (this.mercadoSelected.size === this.mercadoEntries().length) {
      this.mercadoSelected.clear();
    } else {
      this.mercadoEntries().forEach(e => this.mercadoSelected.set(e.id, e));
    }
    this.cdr.markForCheck();
  }

  get shareSellerName(): string {
    return this.binderProfile()?.display_name || ('@' + (this.auth.user()?.username || ''));
  }

  async exportMercadoPdf() {
    this.exportingPdf.set(true);
    this.cdr.markForCheck();

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
      this.mercadoAllEntries.set(allPages);
      this.cdr.markForCheck();

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

    this.exportingPdf.set(false);
    this.cdr.markForCheck();
  }

  // ── Tienda config ──
  saveStoreProfile() {
    const profile = this.binderProfile();
    if (!profile) return;
    this.storeProfileSaving.set(true);
    const payload = {
      is_store_public: profile.is_store_public,
      display_name: profile.display_name,
      bio: profile.bio,
      city: profile.city,
      country: profile.country,
      whatsapp: profile.whatsapp,
      instagram: profile.instagram,
      discord: profile.discord,
      email_public: profile.email_public,
      payment_methods: profile.payment_methods,
      shipping_info: profile.shipping_info,
      accepts_trades: profile.accepts_trades,
    };
    this.carpetaService.updateBinderProfile(payload).subscribe({
      next: p => {
        this.binderProfile.set(p);
        this.storeProfileSaving.set(false);
        this.storeProfileSaved.set(true);
        this.cdr.markForCheck();
        setTimeout(() => { this.storeProfileSaved.set(false); this.cdr.markForCheck(); }, 2000);
      },
      error: () => { this.storeProfileSaving.set(false); this.cdr.markForCheck(); },
    });
  }

  regenerateShareToken() {
    if (!confirm('¿Generar un nuevo enlace privado? El anterior dejará de funcionar.')) return;
    this.storeRegenerating.set(true);
    this.carpetaService.regenerateShareToken().subscribe({
      next: r => {
        this.shareToken = r.share_token;
        const profile = this.binderProfile();
        if (profile) this.binderProfile.set({ ...profile, share_token: r.share_token });
        this.storeRegenerating.set(false);
        this.cdr.markForCheck();
      },
      error: () => { this.storeRegenerating.set(false); this.cdr.markForCheck(); },
    });
  }

  publicStoreUrl(): string {
    const slug = this.binderProfile()?.store_slug;
    if (!slug) return '';
    return `${window.location.origin}/t/${slug}`;
  }

  privateStoreUrl(): string {
    if (!this.shareToken) return '';
    return `${window.location.origin}/tienda/${this.shareToken}`;
  }

  copyPublicUrl() {
    navigator.clipboard.writeText(this.publicStoreUrl()).then(() => {
      this.shareLinkCopied.set(true);
      this.cdr.markForCheck();
      setTimeout(() => { this.shareLinkCopied.set(false); this.cdr.markForCheck(); }, 2000);
    });
  }

  // ── Bulk import ──
  runBulkImport() {
    if (!this.importText.trim()) return;
    this.importing.set(true);
    this.importResult.set(null);
    this.carpetaService.bulkImport(this.importText, this.importMode).subscribe({
      next: res => {
        this.importing.set(false);
        this.importResult.set(res);
        if (res.added || res.updated) {
          this.loadIds();
          this.loadCollection();
        }
        this.cdr.markForCheck();
      },
      error: () => { this.importing.set(false); this.cdr.markForCheck(); },
    });
  }

  clearImport() {
    this.importText = '';
    this.importResult.set(null);
  }

  // ── Stats: donut por rareza ──
  private readonly DONUT_PALETTE = ['#f59e0b', '#4fc3f7', '#9b6ad8', '#7cb342', '#e94560', '#c89b3c', '#8896a8', '#2a8a8a'];
  private readonly DONUT_RADIUS = 45;

  donutSegments(rows: { card__rarity__name: string | null; count: number }[]): Array<{ key: string; count: number; color: string; dashArray: string; dashOffset: string }> {
    const total = rows.reduce((sum, r) => sum + (r.count || 0), 0);
    if (total === 0) return [];
    const circumference = 2 * Math.PI * this.DONUT_RADIUS;
    let cumulative = 0;
    return rows.map((r, i) => {
      const length = ((r.count || 0) / total) * circumference;
      const dashArray = `${length} ${circumference - length}`;
      const dashOffset = `${-cumulative}`;
      cumulative += length;
      return {
        key: r.card__rarity__name || 'Sin rareza',
        count: r.count,
        color: this.DONUT_PALETTE[i % this.DONUT_PALETTE.length],
        dashArray,
        dashOffset,
      };
    });
  }
}
