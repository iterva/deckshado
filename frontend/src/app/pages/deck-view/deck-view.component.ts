import { Component, OnInit, ChangeDetectorRef, ElementRef, ViewChild, HostListener } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Title, Meta } from '@angular/platform-browser';
import { DatePipe } from '@angular/common';
import { DeckService } from '../../services/deck.service';
import { CardService } from '../../services/card.service';
import { AuthService } from '../../services/auth.service';
import { Deck, Card, BanlistEntry } from '../../models';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';
import { RelativeTimePipe } from '../../pipes/relative-time.pipe';

type ViewMode = 'grid' | 'list' | 'stats';
type SocialTab = 'none' | 'comments' | 'snapshots' | 'changelog' | 'suggestions';
type StackOrientation = 'down' | 'up' | 'left' | 'right' | 'center';
type ExportSortBy = 'original' | 'type' | 'name' | 'cost' | 'quantity';
type ExportSortDir = 'asc' | 'desc';
type ExportBackgroundMode = 'default' | 'color';

interface ExportDeckEntry {
  trackId: string;
  quantity: number;
  card_detail: Card;
}

@Component({
  selector: 'app-deck-view',
  standalone: true,
  imports: [RouterLink, FormsModule, ThumbnailPipe, DatePipe, RelativeTimePipe],
  templateUrl: './deck-view.component.html',
  styleUrl: './deck-view.component.scss',
})
export class DeckViewComponent implements OnInit {
  deck: Deck | null = null;
  loading = true;
  viewMode: ViewMode = 'grid';

  // Tabs sociales (colíndan al final, una sola activa o ninguna)
  socialTab: SocialTab = 'none';
  // Menú kebab
  showMoreMenu = false;
  // Menú de orientación del apilado de cartas
  showStackOrientationMenu = false;
  // Modal de opciones de exportación
  showExportOptionsModal = false;
  stackOrientation: StackOrientation = 'down';
  private readonly stackOrientationStorageKey = 'deck-view:stack-orientation';
  private readonly exportOptionsStorageKey = 'deck-view:export-options';

  exportSortBy: ExportSortBy = 'original';
  exportSortDir: ExportSortDir = 'asc';
  exportSeparateCards = false;
  exportShowNumbers = true;
  exportShowQr = true;
  exportBackgroundMode: ExportBackgroundMode = 'default';
  exportBackgroundColor = '#181926';
  exportTextColor = '#c8d6e5';
  exportQrDataUrl: string | null = null;
  exportLogoDataUrl: string | null = null;
  exportLogoName = '';
  exportLogoError = '';
  exportLogoDragOver = false;
  private exportLogoDragDepth = 0;
  exportTypeOrder: string[] = ['Oro', 'Aliado', 'Talismán', 'Arma', 'Tótem'];
  showExportPreviewModal = false;
  exportPreviewDataUrl: string | null = null;
  // Sidedeck colapsable
  sideOpen = true;
  // Hand simulator como modal global
  showHandModal = false;
  // Modo presentación / fullscreen
  presentationMode = false;
  // Suggestions
  suggestions: any[] = [];
  loadingSuggestions = false;
  groupedEntries: { type: string; total: number; entries: any[] }[] = [];
  groupedSideEntries: { type: string; total: number; entries: any[] }[] = [];
  previewCard: Card | null = null;
  previewAbility: string | null = null;
  exportOrientation: 'vertical' | 'horizontal' = 'horizontal';
  exporting = false;
  shareToast = false;
  @ViewChild('deckContent') deckContent!: ElementRef;
  private abilityCache = new Map<number, string>();
  private readonly deckImagePlaceholder = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="350" height="500" viewBox="0 0 350 500"><rect width="350" height="500" fill="%231a1f3d"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%2396a1c8" font-family="Arial" font-size="20">Sin imagen</text></svg>';

  // Hand simulator
  handCards: Card[] = [];
  handSize = 0;
  handActive = false;

  // Banlist
  banlistByName = new Map<string, BanlistEntry>();
  banlistByCardId = new Map<number, BanlistEntry>();

  // Changelog
  changelog: { id: number; summary: string; created_at: string }[] = [];
  showChangelog = false;

  // Likes
  liked = false;
  likeCount = 0;

  // Comments
  comments: any[] = [];
  showComments = false;
  newComment = '';

  // Snapshots
  snapshots: any[] = [];
  showSnapshots = false;
  snapshotLabel = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private deckService: DeckService,
    private cardService: CardService,
    public auth: AuthService,
    private cdr: ChangeDetectorRef,
    private titleService: Title,
    private metaService: Meta,
  ) {}

  get isOwner(): boolean {
    const user = this.auth.user();
    return !!user && !!this.deck && user.username === this.deck.owner_username;
  }

  get canCopy(): boolean {
    return this.auth.isAuthenticated();
  }

  editDeck() {
    if (this.deck) {
      this.router.navigate(['/builder', this.deck.id]);
    }
  }

  togglingVisibility = false;
  toggleVisibility() {
    if (!this.deck || this.togglingVisibility) return;
    this.togglingVisibility = true;
    const newVal = !this.deck.is_public;
    this.deckService.updateDeck(this.deck.id, { is_public: newVal }).subscribe({
      next: (updated: any) => {
        if (this.deck) this.deck.is_public = updated.is_public ?? newVal;
        this.togglingVisibility = false;
        this.cdr.markForCheck();
      },
      error: (err: any) => {
        console.error('Error cambiando visibilidad:', err);
        this.togglingVisibility = false;
      },
    });
  }

  deleteDeck() {
    if (!this.deck) return;
    if (!confirm('¿Estás seguro de que quieres eliminar este mazo?')) return;
    this.deckService.deleteDeck(this.deck.id).subscribe({
      next: () => this.router.navigate(['/decks']),
      error: (err: any) => console.error('Error eliminando mazo:', err),
    });
  }

  copyDeck() {
    if (!this.deck) return;
    if (!this.auth.isAuthenticated()) {
      // Invitar a registrarse / iniciar sesión y volver al mazo
      this.router.navigate(['/login'], {
        queryParams: { returnUrl: this.router.url, action: 'clone' },
      });
      return;
    }
    const fmt = this.deck.format || 'imp';
    const qp: any = {};
    if (this.deck.race) qp.race = this.deck.race;
    if (this.deck.sub_format && this.deck.sub_format !== 'racial') qp.sub_fmt = this.deck.sub_format;
    this.router.navigate(['/builder/new', fmt], {
      queryParams: qp,
      state: { copyFrom: this.deck },
    });
  }

  /** Fijar/quitar la carta como portada del mazo (solo owner). */
  toggleCover(card: Card, event: Event) {
    event.preventDefault();
    event.stopPropagation();
    if (!this.deck || !this.isOwner) return;
    const isCurrent = this.deck.cover_card === card.id;
    const obs = isCurrent
      ? this.deckService.clearCoverCard(this.deck.id)
      : this.deckService.setCoverCard(this.deck.id, card.id);
    obs.subscribe({
      next: (res) => {
        if (this.deck) {
          this.deck.cover_card = res.cover_card;
          (this.deck as any).cover_card_detail = res.cover_card ? card : null;
          this.cdr.detectChanges();
        }
      },
    });
  }

  shareDeck() {
    const url = window.location.href;
    const title = this.deck ? `${this.deck.name} · ShadowForge` : 'ShadowForge';
    const text = this.deck ? `Mira este mazo: ${this.deck.name}` : '';
    // Usa Web Share API en mobile/PWA cuando esté disponible.
    const nav = navigator as any;
    if (nav.share) {
      nav.share({ title, text, url }).catch(() => {/* usuario canceló */});
      return;
    }
    navigator.clipboard.writeText(url).then(() => {
      this.shareToast = true;
      this.cdr.detectChanges();
      setTimeout(() => {
        this.shareToast = false;
        this.cdr.detectChanges();
      }, 2000);
    });
  }

  /** Exporta el mazo como JSON descargable (formato propio, importable). */
  exportJson() {
    if (!this.deck) return;
    const payload = {
      version: 1,
      app: 'shadowforge',
      name: this.deck.name,
      description: this.deck.description ?? '',
      format: this.deck.format,
      sub_format: (this.deck as any).sub_format ?? '',
      race: this.deck.race ?? '',
      starting_gold: (this.deck as any).starting_gold_detail?.myl_id ?? null,
      cover_card: (this.deck as any).cover_card_detail?.myl_id ?? null,
      entries: (this.deck.entries ?? []).map(e => ({
        myl_id: e.card_detail.myl_id,
        name: e.card_detail.name,
        quantity: e.quantity,
      })),
      sideboard: (this.deck.sideboard_entries ?? []).map(e => ({
        myl_id: e.card_detail.myl_id,
        name: e.card_detail.name,
        quantity: e.quantity,
      })),
      exported_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const safeName = this.deck.name.replace(/[^\w\-]+/g, '_').slice(0, 60) || 'deck';
    a.download = `${safeName}.deck.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  exportText() {
    if (!this.deck) return;
    let text = `// ${this.deck.name}\n// ${this.formatLabel}`;
    if (this.raceLabel) text += ` · ${this.raceLabel}`;
    text += `\n\n`;
    for (const g of this.groupedEntries) {
      text += `// ${g.type} (${g.total})\n`;
      for (const e of g.entries) {
        text += `${e.quantity}x ${e.card_detail.name}\n`;
      }
      text += `\n`;
    }
    if (this.deck.sideboard_entries && this.deck.sideboard_entries.length > 0) {
      text += `// Sidedeck\n`;
      for (const e of this.deck.sideboard_entries) {
        text += `${e.quantity}x ${e.card_detail.name}\n`;
      }
    }
    navigator.clipboard.writeText(text.trim()).then(() => {
      this.shareToast = true;
      this.cdr.detectChanges();
      setTimeout(() => {
        this.shareToast = false;
        this.cdr.detectChanges();
      }, 2000);
    });
  }

  private readonly typeOrder: Record<string, number> = {
    'Oro': 0, 'Aliado': 1, 'Talismán': 2, 'Arma': 3, 'Tótem': 4,
  };

  // ── Likes ──
  toggleLike() {
    if (!this.deck || !this.auth.isAuthenticated()) return;
    this.deckService.toggleLike(this.deck.id).subscribe({
      next: (res) => {
        this.liked = res.liked;
        this.likeCount = res.like_count;
        this.cdr.detectChanges();
      },
    });
  }

  // ── Comments ──
  loadComments() {
    if (!this.deck) return;
    this.deckService.getComments(this.deck.id).subscribe({
      next: (c) => { this.comments = c; this.cdr.detectChanges(); },
    });
  }

  submitComment() {
    if (!this.deck || !this.newComment.trim()) return;
    this.deckService.addComment(this.deck.id, this.newComment.trim()).subscribe({
      next: (c) => {
        this.comments = [c, ...this.comments];
        this.newComment = '';
        this.cdr.detectChanges();
      },
    });
  }

  deleteComment(commentId: number) {
    this.deckService.deleteComment(commentId).subscribe({
      next: () => {
        this.comments = this.comments.filter(c => c.id !== commentId);
        this.cdr.detectChanges();
      },
    });
  }

  // ── Snapshots ──
  loadSnapshots() {
    if (!this.deck) return;
    this.deckService.getSnapshots(this.deck.id).subscribe({
      next: (s) => { this.snapshots = s; this.cdr.detectChanges(); },
    });
  }

  createSnapshot() {
    if (!this.deck) return;
    this.deckService.createSnapshot(this.deck.id, this.snapshotLabel || undefined).subscribe({
      next: (s) => {
        this.snapshots = [s, ...this.snapshots];
        this.snapshotLabel = '';
        this.cdr.detectChanges();
      },
    });
  }

  restoreSnapshot(snapshotId: number) {
    if (!confirm('¿Restaurar el mazo a esta versión? Se perderán los cambios actuales.')) return;
    this.deckService.restoreSnapshot(snapshotId).subscribe({
      next: () => window.location.reload(),
    });
  }

  ngOnInit() {
    // Restaurar viewMode persistido
    try {
      const saved = localStorage.getItem('deck-view:mode') as ViewMode | null;
      if (saved === 'grid' || saved === 'list' || saved === 'stats') this.viewMode = saved;

      const savedOrientation = localStorage.getItem(this.stackOrientationStorageKey) as StackOrientation | null;
      if (savedOrientation === 'down' || savedOrientation === 'up' || savedOrientation === 'left' || savedOrientation === 'right' || savedOrientation === 'center') {
        this.stackOrientation = savedOrientation;
      }

      const rawExportOptions = localStorage.getItem(this.exportOptionsStorageKey);
      if (rawExportOptions) {
        const parsed = JSON.parse(rawExportOptions) as Partial<{
          stackOrientation: StackOrientation;
          sortBy: ExportSortBy;
          sortDir: ExportSortDir;
          separate: boolean;
          showNumbers: boolean;
          showQr: boolean;
          backgroundMode: ExportBackgroundMode;
          backgroundColor: string;
          textColor: string;
          typeOrder: string[];
        }>;
        if (parsed.sortBy === 'original' || parsed.sortBy === 'type' || parsed.sortBy === 'name' || parsed.sortBy === 'cost' || parsed.sortBy === 'quantity') {
          this.exportSortBy = parsed.sortBy;
        }
        if (parsed.sortDir === 'asc' || parsed.sortDir === 'desc') {
          this.exportSortDir = parsed.sortDir;
        }
        if (this.isValidStackOrientation(parsed.stackOrientation)) {
          this.stackOrientation = parsed.stackOrientation;
        }
        if (typeof parsed.separate === 'boolean') this.exportSeparateCards = parsed.separate;
        if (typeof parsed.showNumbers === 'boolean') this.exportShowNumbers = parsed.showNumbers;
        if (typeof parsed.showQr === 'boolean') this.exportShowQr = parsed.showQr;
        if (parsed.backgroundMode === 'default' || parsed.backgroundMode === 'color') {
          this.exportBackgroundMode = parsed.backgroundMode;
        }
        if (typeof parsed.backgroundColor === 'string') {
          const normalizedBg = this.normalizeHexColor(parsed.backgroundColor);
          if (normalizedBg) this.exportBackgroundColor = normalizedBg;
        }
        if (typeof parsed.textColor === 'string') {
          const normalizedText = this.normalizeHexColor(parsed.textColor);
          if (normalizedText) this.exportTextColor = normalizedText;
        }
        if (Array.isArray(parsed.typeOrder)) {
          this.exportTypeOrder = this.dedupeTypeOrder(parsed.typeOrder);
        }
      }
    } catch {}

    const id = Number(this.route.snapshot.paramMap.get('id'));
    const loadDeck = (deck: Deck) => {
      this.deck = deck;
      this.likeCount = (deck as any).like_count || 0;
      this.liked = (deck as any).user_liked || false;
      this.sortEntries();
      this.buildGroups();
      this.syncExportTypeOrderFromDeck();
      this.loading = false;
      this.preloadImages();
      this.loadBanlist();
      this.loadComments();
      // SEO
      this.titleService.setTitle(`${deck.name} — ShadowForge`);
      this.metaService.updateTag({ name: 'description', content: `Mazo ${deck.name} por ${deck.owner_username} — ${this.formatLabel} · ${deck.card_count} cartas` });
      this.ensureExportQr();
      // Load changelog + snapshots if owner
      if (this.isOwner) {
        this.deckService.getChangelog(deck.id).subscribe({
          next: (log) => { this.changelog = log; this.cdr.detectChanges(); },
          error: () => {},
        });
        this.loadSnapshots();
      }
      // Deep-link ?card=ID -> abrir preview
      const cardParam = this.route.snapshot.queryParamMap.get('card');
      if (cardParam) {
        const cid = Number(cardParam);
        const target = (deck.entries || []).concat(deck.sideboard_entries || [])
          .find(e => e.card_detail.id === cid);
        if (target) {
          // Llamada manual (sin event) para no afectar handlers
          this.previewCard = target.card_detail;
          if (this.abilityCache.has(cid)) {
            this.previewAbility = this.abilityCache.get(cid) || null;
          } else {
            this.cardService.getCard(cid).subscribe(detail => {
              this.abilityCache.set(cid, detail.ability || '');
              if (this.previewCard?.id === cid) {
                this.previewAbility = detail.ability || null;
                this.cdr.detectChanges();
              }
            });
          }
        }
      }
    };
    // Try owner endpoint first if authenticated, then team, then public
    if (this.auth.isAuthenticated()) {
      this.deckService.getDeck(id).subscribe({
        next: loadDeck,
        error: () => {
          this.deckService.getTeamDeck(id).subscribe({
            next: loadDeck,
            error: () => {
              this.deckService.getPublicDeck(id).subscribe({
                next: loadDeck,
                error: () => this.loading = false,
              });
            },
          });
        },
      });
    } else {
      this.deckService.getPublicDeck(id).subscribe({
        next: loadDeck,
        error: () => this.loading = false,
      });
    }
  }

  private sortEntries() {
    if (!this.deck?.entries) return;
    this.deck.entries.sort((a, b) => {
      const typeA = this.typeOrder[a.card_detail.type_name ?? ''] ?? 99;
      const typeB = this.typeOrder[b.card_detail.type_name ?? ''] ?? 99;
      if (typeA !== typeB) return typeA - typeB;
      return b.quantity - a.quantity;
    });
    if (this.deck.sideboard_entries) {
      this.deck.sideboard_entries.sort((a, b) => {
        const typeA = this.typeOrder[a.card_detail.type_name ?? ''] ?? 99;
        const typeB = this.typeOrder[b.card_detail.type_name ?? ''] ?? 99;
        if (typeA !== typeB) return typeA - typeB;
        return b.quantity - a.quantity;
      });
    }
  }

  private buildGroups() {
    if (!this.deck?.entries) return;
    const map = new Map<string, { type: string; total: number; entries: any[] }>();
    for (const entry of this.deck.entries) {
      const type = entry.card_detail.type_name ?? 'Otro';
      if (!map.has(type)) {
        map.set(type, { type, total: 0, entries: [] });
      }
      const group = map.get(type)!;
      group.entries.push(entry);
      group.total += entry.quantity;
    }
    // Sort groups by typeOrder
    this.groupedEntries = [...map.values()].sort(
      (a, b) => (this.typeOrder[a.type] ?? 99) - (this.typeOrder[b.type] ?? 99)
    );

    // Build sideboard groups
    if (this.deck.sideboard_entries) {
      const sideMap = new Map<string, { type: string; total: number; entries: any[] }>();
      for (const entry of this.deck.sideboard_entries) {
        const type = entry.card_detail.type_name ?? 'Otro';
        if (!sideMap.has(type)) {
          sideMap.set(type, { type, total: 0, entries: [] });
        }
        const group = sideMap.get(type)!;
        group.entries.push(entry);
        group.total += entry.quantity;
      }
      this.groupedSideEntries = [...sideMap.values()].sort(
        (a, b) => (this.typeOrder[a.type] ?? 99) - (this.typeOrder[b.type] ?? 99)
      );
    }
  }

  getRange(n: number): number[] {
    return Array.from({ length: n }, (_, i) => i);
  }

  /**
   * Curva de coste del mazo principal (excluye Oros y cartas sin coste).
   * Buckets 0..6 + 7+; siempre devuelve los 8 buckets para mantener forma.
   */
  get costCurve(): { label: string; count: number; pct: number }[] {
    const buckets = [0, 0, 0, 0, 0, 0, 0, 0];
    if (this.deck?.entries) {
      for (const entry of this.deck.entries) {
        const card = entry.card_detail;
        if (card.type_name === 'Oro') continue;
        const raw = card.cost;
        if (raw === null || raw === undefined || raw === '') continue;
        const n = Number(raw);
        if (!Number.isFinite(n)) continue;
        const idx = n >= 7 ? 7 : Math.max(0, Math.min(7, Math.floor(n)));
        buckets[idx] += entry.quantity;
      }
    }
    const max = Math.max(1, ...buckets);
    return buckets.map((count, i) => ({
      label: i === 7 ? '7+' : String(i),
      count,
      pct: Math.round((count / max) * 100),
    }));
  }

  get hasAnyCost(): boolean {
    return this.costCurve.some(b => b.count > 0);
  }

  /** Bucket label correspondiente al promedio (para resaltarlo en la curva). */
  get avgCostBucket(): string {
    const a = this.avgCost;
    if (!Number.isFinite(a) || a <= 0) return '';
    const idx = a >= 7 ? 7 : Math.max(0, Math.min(7, Math.round(a)));
    return idx === 7 ? '7+' : String(idx);
  }

  /** Promedio de coste de cartas no-Oro con coste definido. */
  get avgCost(): number {
    let sum = 0;
    let n = 0;
    if (this.deck?.entries) {
      for (const entry of this.deck.entries) {
        const card = entry.card_detail;
        if (card.type_name === 'Oro') continue;
        const raw = card.cost;
        if (raw === null || raw === undefined || raw === '') continue;
        const v = Number(raw);
        if (!Number.isFinite(v)) continue;
        sum += v * entry.quantity;
        n += entry.quantity;
      }
    }
    return n === 0 ? 0 : Math.round((sum / n) * 10) / 10;
  }

  /**
   * Draw probability: for each unique card, probability of drawing at least
   * one copy in an 8-card opening hand (hypergeometric).
   * P(≥1) = 1 − C(N−K, n) / C(N, n)
   */
  get drawProbabilities(): { name: string; qty: number; pct: number }[] {
    if (!this.deck?.entries) return [];
    const N = this.cardPool.length; // total pool size
    const n = Math.min(8, N); // draw size
    if (N === 0 || n === 0) return [];
    return this.deck.entries.map(entry => {
      const K = entry.quantity;
      // P(draw 0) = C(N-K, n) / C(N, n)
      let p0 = 1;
      for (let i = 0; i < n; i++) {
        p0 *= (N - K - i) / (N - i);
      }
      return {
        name: entry.card_detail.name,
        qty: K,
        pct: Math.round((1 - Math.max(0, p0)) * 100),
      };
    }).sort((a, b) => b.pct - a.pct);
  }

  /** Type distribution: percentage of each card type in the main deck. */
  get typeDistribution(): { type: string; count: number; pct: number; color: string }[] {
    if (!this.deck?.entries) return [];
    const total = this.deck.entries.reduce((s, e) => s + e.quantity, 0);
    if (total === 0) return [];
    const colors: Record<string, string> = {
      'Oro': '#ffbd39', 'Aliado': '#4ade80', 'Talismán': '#60a5fa',
      'Arma': '#e94560', 'Tótem': '#c084fc',
    };
    return this.groupedEntries.map(g => ({
      type: g.type,
      count: g.total,
      pct: Math.round((g.total / total) * 100),
      color: colors[g.type] || '#888',
    }));
  }

  /** Ratio aliados vs armas. */
  get allyWeaponRatio(): { allies: number; weapons: number; ratio: string } {
    const allies = this.groupedEntries.find(g => g.type === 'Aliado')?.total || 0;
    const weapons = this.groupedEntries.find(g => g.type === 'Arma')?.total || 0;
    const ratio = weapons > 0 ? `${(allies / weapons).toFixed(1)}:1` : `${allies}:0`;
    return { allies, weapons, ratio };
  }

  showPreview(card: Card, event: MouseEvent) {
    event.stopPropagation();
    this.previewCard = card;
    // Permalink ?card=
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { card: card.id },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
    if (this.abilityCache.has(card.id)) {
      this.previewAbility = this.abilityCache.get(card.id) || null;
      this.cdr.detectChanges();
    } else {
      this.previewAbility = null;
      this.cdr.detectChanges();
      this.cardService.getCard(card.id).subscribe(detail => {
        const ability = detail.ability || null;
        this.abilityCache.set(card.id, ability || '');
        if (this.previewCard?.id === card.id) {
          this.previewAbility = ability;
          this.cdr.detectChanges();
        }
      });
    }
  }

  hidePreview() {
    this.previewCard = null;
    this.previewAbility = null;
    // Limpia ?card= del URL
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { card: null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  /** Cambiar vista y persistir en localStorage. */
  setViewMode(mode: ViewMode) {
    this.viewMode = mode;
    try { localStorage.setItem('deck-view:mode', mode); } catch {}
  }

  toggleStackOrientationMenu(e?: Event) {
    if (e) e.stopPropagation();
    this.showMoreMenu = false;
    this.showExportOptionsModal = false;
    this.showStackOrientationMenu = !this.showStackOrientationMenu;
  }

  setStackOrientation(orientation: StackOrientation) {
    this.stackOrientation = orientation;
    this.showStackOrientationMenu = false;
    try { localStorage.setItem(this.stackOrientationStorageKey, orientation); } catch {}
    this.persistExportOptions();
  }

  openExportOptionsModal(e?: Event) {
    if (e) e.stopPropagation();
    this.showMoreMenu = false;
    this.showStackOrientationMenu = false;
    this.showExportPreviewModal = false;
    this.showExportOptionsModal = true;
  }

  closeExportOptionsModal() {
    this.showExportOptionsModal = false;
  }

  backToExportOptions() {
    this.showExportPreviewModal = false;
    this.showExportOptionsModal = true;
  }

  closeExportPreview() {
    this.showExportPreviewModal = false;
  }

  setExportSortBy(sortBy: ExportSortBy) {
    this.exportSortBy = sortBy;
    this.persistExportOptions();
  }

  moveExportTypeOrder(typeName: string, direction: 'up' | 'down') {
    const idx = this.exportTypeOrder.findIndex((x) => x === typeName);
    if (idx === -1) return;
    const target = direction === 'up' ? idx - 1 : idx + 1;
    if (target < 0 || target >= this.exportTypeOrder.length) return;
    const copy = [...this.exportTypeOrder];
    [copy[idx], copy[target]] = [copy[target], copy[idx]];
    this.exportTypeOrder = copy;
    this.persistExportOptions();
  }

  toggleExportSortDir() {
    this.exportSortDir = this.exportSortDir === 'asc' ? 'desc' : 'asc';
    this.persistExportOptions();
  }

  setExportSeparateCards(value: boolean) {
    this.exportSeparateCards = value;
    this.persistExportOptions();
  }

  setExportShowNumbers(value: boolean) {
    this.exportShowNumbers = value;
    this.persistExportOptions();
  }

  setExportShowQr(value: boolean) {
    this.exportShowQr = value;
    if (value) this.ensureExportQr();
    this.persistExportOptions();
  }

  setExportBackgroundMode(mode: ExportBackgroundMode) {
    this.exportBackgroundMode = mode;
    this.persistExportOptions();
  }

  onExportBackgroundColorInput(value: string) {
    const normalized = this.normalizeHexColor(value);
    if (!normalized) return;
    this.exportBackgroundMode = 'color';
    this.exportBackgroundColor = normalized;
    this.persistExportOptions();
  }

  onExportBackgroundHexChange(value: string) {
    const normalized = this.normalizeHexColor(value);
    if (!normalized) return;
    this.exportBackgroundMode = 'color';
    this.exportBackgroundColor = normalized;
    this.persistExportOptions();
  }

  onExportTextColorInput(value: string) {
    const normalized = this.normalizeHexColor(value);
    if (!normalized) return;
    this.exportTextColor = normalized;
    this.persistExportOptions();
  }

  onExportTextHexChange(value: string) {
    const normalized = this.normalizeHexColor(value);
    if (!normalized) return;
    this.exportTextColor = normalized;
    this.persistExportOptions();
  }

  onExportLogoSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    this.loadExportLogoFromFile(file);
    input.value = '';
  }

  onExportLogoDragEnter(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.exportLogoDragDepth += 1;
    this.exportLogoDragOver = true;
  }

  onExportLogoDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy';
    this.exportLogoDragOver = true;
  }

  onExportLogoDragLeave(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.exportLogoDragDepth = Math.max(0, this.exportLogoDragDepth - 1);
    if (this.exportLogoDragDepth === 0) {
      this.exportLogoDragOver = false;
    }
  }

  onExportLogoDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.exportLogoDragDepth = 0;
    this.exportLogoDragOver = false;
    const file = event.dataTransfer?.files?.[0];
    if (!file) return;
    this.loadExportLogoFromFile(file);
  }

  private loadExportLogoFromFile(file: File) {
    this.exportLogoError = '';
    if (!file.type.startsWith('image/')) {
      this.exportLogoError = 'Selecciona una imagen valida para el logo.';
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      this.exportLogoError = 'El logo no puede superar 5 MB.';
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      this.exportLogoDataUrl = typeof reader.result === 'string' ? reader.result : null;
      this.exportLogoName = file.name;
      this.exportLogoError = '';
      this.cdr.detectChanges();
    };
    reader.onerror = () => {
      this.exportLogoDataUrl = null;
      this.exportLogoName = '';
      this.exportLogoError = 'No se pudo leer la imagen del logo.';
      this.cdr.detectChanges();
    };
    reader.readAsDataURL(file);
  }

  clearExportLogo() {
    this.exportLogoDataUrl = null;
    this.exportLogoName = '';
    this.exportLogoError = '';
    this.exportLogoDragDepth = 0;
    this.exportLogoDragOver = false;
  }

  async generateExportPreview() {
    const canvas = await this.renderExportCanvas();
    if (!canvas) return;
    this.exportPreviewDataUrl = canvas.toDataURL('image/png');
    this.showExportOptionsModal = false;
    this.showExportPreviewModal = true;
    this.cdr.detectChanges();
  }

  downloadExportPreview() {
    if (!this.exportPreviewDataUrl) return;
    const link = document.createElement('a');
    link.download = `${this.deck?.name || 'mazo'}.png`;
    link.href = this.exportPreviewDataUrl;
    link.click();
  }

  async copyExportPreviewToClipboard() {
    if (!this.exportPreviewDataUrl) return;
    if (!('clipboard' in navigator) || !(navigator.clipboard as any).write) {
      this.downloadExportPreview();
      return;
    }
    try {
      const response = await fetch(this.exportPreviewDataUrl);
      const blob = await response.blob();
      await (navigator.clipboard as any).write([
        new (window as any).ClipboardItem({ 'image/png': blob }),
      ]);
      this.shareToast = true;
      this.cdr.detectChanges();
      setTimeout(() => {
        this.shareToast = false;
        this.cdr.detectChanges();
      }, 2000);
    } catch (e) {
      console.error('Error copiando preview al portapapeles:', e);
    }
  }

  private normalizeHexColor(value: string | null | undefined): string | null {
    if (!value) return null;
    const raw = value.trim();
    if (!raw) return null;
    const prefixed = raw.startsWith('#') ? raw : `#${raw}`;
    if (/^#[0-9a-fA-F]{3}$/.test(prefixed)) {
      const r = prefixed[1];
      const g = prefixed[2];
      const b = prefixed[3];
      return `#${r}${r}${g}${g}${b}${b}`.toLowerCase();
    }
    if (/^#[0-9a-fA-F]{6}$/.test(prefixed)) {
      return prefixed.toLowerCase();
    }
    return null;
  }

  get exportBackgroundResolved(): string {
    return this.exportBackgroundMode === 'color' ? this.exportBackgroundColor : this.getRaceBackground();
  }

  private persistExportOptions() {
    try {
      localStorage.setItem(this.exportOptionsStorageKey, JSON.stringify({
        stackOrientation: this.stackOrientation,
        sortBy: this.exportSortBy,
        sortDir: this.exportSortDir,
        separate: this.exportSeparateCards,
        showNumbers: this.exportShowNumbers,
        showQr: this.exportShowQr,
        backgroundMode: this.exportBackgroundMode,
        backgroundColor: this.exportBackgroundColor,
        textColor: this.exportTextColor,
        typeOrder: this.exportTypeOrder,
      }));
    } catch {}
  }

  /** Tabs sociales (toggle). */
  setSocialTab(tab: SocialTab) {
    this.socialTab = (this.socialTab === tab) ? 'none' : tab;
    if (this.socialTab === 'suggestions' && this.suggestions.length === 0) {
      this.loadSuggestions();
    }
  }

  toggleMoreMenu(e?: Event) {
    if (e) { e.stopPropagation(); }
    this.showStackOrientationMenu = false;
    this.showExportOptionsModal = false;
    this.showMoreMenu = !this.showMoreMenu;
  }

  togglePresentation() {
    this.presentationMode = !this.presentationMode;
    document.body.classList.toggle('deck-presentation', this.presentationMode);
  }

  /** Esc cierra preview / menús / fullscreen. */
  @HostListener('document:keydown', ['$event'])
  onKeydown(ev: KeyboardEvent) {
    if (ev.key === 'Escape') {
      if (this.previewCard) { this.hidePreview(); return; }
      if (this.showExportPreviewModal) { this.closeExportPreview(); return; }
      if (this.showHandModal) { this.showHandModal = false; return; }
      if (this.showStackOrientationMenu) { this.showStackOrientationMenu = false; return; }
      if (this.showExportOptionsModal) { this.showExportOptionsModal = false; return; }
      if (this.showMoreMenu) { this.showMoreMenu = false; return; }
      if (this.presentationMode) { this.togglePresentation(); return; }
    }
    // F = fullscreen / presentación
    if ((ev.key === 'f' || ev.key === 'F') && !this.previewCard && !this.isTypingTarget(ev.target)) {
      this.togglePresentation();
    }
  }

  /** Cerrar el menú "más" si se hace click afuera. */
  @HostListener('document:click')
  onDocClick() {
    let changed = false;
    if (this.showMoreMenu) {
      this.showMoreMenu = false;
      changed = true;
    }
    if (this.showStackOrientationMenu) {
      this.showStackOrientationMenu = false;
      changed = true;
    }
    if (changed) this.cdr.detectChanges();
  }

  private isTypingTarget(t: EventTarget | null): boolean {
    if (!t) return false;
    const el = t as HTMLElement;
    const tag = (el.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || el.isContentEditable;
  }

  loadSuggestions() {
    if (!this.deck || !this.isOwner) return;
    this.loadingSuggestions = true;
    this.deckService.getSuggestions(this.deck.id).subscribe({
      next: (s) => { this.suggestions = s || []; this.loadingSuggestions = false; this.cdr.detectChanges(); },
      error: () => { this.loadingSuggestions = false; this.cdr.detectChanges(); },
    });
  }

  /** Copiar imagen exportada al portapapeles (si el navegador lo soporta). */
  async copyImageToClipboard() {
    if (!this.deckContent || this.exporting) return;
    if (!('clipboard' in navigator) || !(navigator.clipboard as any).write) {
      this.exportImage();
      return;
    }
    const canvas = await this.renderExportCanvas();
    if (!canvas) return;
    try {
      const blob: Blob | null = await new Promise(res => canvas.toBlob(b => res(b), 'image/png'));
      if (blob) {
        await (navigator.clipboard as any).write([
          new (window as any).ClipboardItem({ 'image/png': blob }),
        ]);
        this.shareToast = true;
        setTimeout(() => { this.shareToast = false; this.cdr.detectChanges(); }, 2000);
      }
    } catch (e) {
      console.error('Error copiando imagen:', e);
    }
  }

  private loadBanlist() {
    if (!this.deck) return;
    const fmt = this.deck.format || 'imp';
    // Para Imperio existen dos sub-banlists (racial y vcr). Si el mazo no es VCR,
    // forzamos 'racial' para no traer límites del meta VCR a un mazo clásico.
    let sub: string | undefined;
    if (fmt === 'imp') {
      sub = this.deck.sub_format === 'vcr' ? 'vcr' : 'racial';
    } else {
      sub = this.deck.sub_format && this.deck.sub_format !== 'racial' ? this.deck.sub_format : undefined;
    }
    this.cardService.getBanlist(fmt, sub).subscribe(entries => {
      this.banlistByName.clear();
      this.banlistByCardId.clear();
      for (const e of entries) {
        // Indexar por nombre SIEMPRE: la regla aplica a todas las ediciones con ese nombre.
        this.banlistByName.set(this.normalizeName(e.card_name), e);
        // Indexar también por card_id si la entrada lo tiene (precedencia sobre el nombre).
        if (e.card_id) this.banlistByCardId.set(e.card_id, e);
      }
      this.cdr.detectChanges();
    });
  }

  private normalizeName(name: string): string {
    if (!name) return '';
    return name.replace(/\(v\d+\)/gi, '')
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim().replace(/\s+/g, ' ');
  }

  getBanStatus(card: Card): BanlistEntry | null {
    return this.banlistByCardId.get(card.id)
      || this.banlistByName.get(this.normalizeName(card.name))
      || null;
  }

  /** Flat list of cards expanded by quantity (for horizontal export) */
  get expandedEntries(): Card[] {
    if (!this.deck?.entries) return [];
    const cards: Card[] = [];
    for (const entry of this.deck.entries) {
      for (let i = 0; i < entry.quantity; i++) {
        cards.push(entry.card_detail);
      }
    }
    return cards;
  }

  get expandedSideEntries(): Card[] {
    if (!this.deck?.sideboard_entries) return [];
    const cards: Card[] = [];
    for (const entry of this.deck.sideboard_entries) {
      for (let i = 0; i < entry.quantity; i++) {
        cards.push(entry.card_detail);
      }
    }
    return cards;
  }

  get isPublicDeck(): boolean {
    return !!this.deck?.is_public;
  }

  get publicDeckUrl(): string {
    if (!this.deck) return '';
    const origin = typeof window !== 'undefined' ? window.location.origin : '';
    return `${origin}/decks/${this.deck.id}`;
  }

  get exportMainEntries(): ExportDeckEntry[] {
    return this.buildExportEntries(this.deck?.entries || [], 'm');
  }

  get exportSideEntries(): ExportDeckEntry[] {
    return this.buildExportEntries(this.deck?.sideboard_entries || [], 's');
  }

  private buildExportEntries(entries: any[], prefix: string): ExportDeckEntry[] {
    const sorted = this.sortExportEntries(entries || []);
    if (!this.exportSeparateCards) {
      return sorted.map((e: any) => ({
        trackId: `${prefix}-${e.id}`,
        quantity: e.quantity,
        card_detail: e.card_detail,
      }));
    }

    const expanded: ExportDeckEntry[] = [];
    for (const e of sorted) {
      for (let i = 0; i < e.quantity; i++) {
        expanded.push({
          trackId: `${prefix}-${e.id}-${i}`,
          quantity: 1,
          card_detail: e.card_detail,
        });
      }
    }
    return expanded;
  }

  private sortExportEntries(entries: any[]): any[] {
    const copy = [...entries];
    if (this.exportSortBy === 'original') return copy;

    const dir = this.exportSortDir === 'asc' ? 1 : -1;
    const normalize = (v: string | null | undefined) => (v || '').toLowerCase();
    const toCost = (v: unknown) => {
      const n = Number(v);
      return Number.isFinite(n) ? n : 999;
    };

    copy.sort((a, b) => {
      switch (this.exportSortBy) {
        case 'type': {
          const av = this.getExportTypeSortWeight(a.card_detail?.type_name);
          const bv = this.getExportTypeSortWeight(b.card_detail?.type_name);
          if (av !== bv) return (av - bv) * dir;
          return normalize(a.card_detail?.name).localeCompare(normalize(b.card_detail?.name)) * dir;
        }
        case 'name':
          return normalize(a.card_detail?.name).localeCompare(normalize(b.card_detail?.name)) * dir;
        case 'cost': {
          const av = toCost(a.card_detail?.cost);
          const bv = toCost(b.card_detail?.cost);
          if (av !== bv) return (av - bv) * dir;
          return normalize(a.card_detail?.name).localeCompare(normalize(b.card_detail?.name)) * dir;
        }
        case 'quantity':
          if (a.quantity !== b.quantity) return (a.quantity - b.quantity) * dir;
          return normalize(a.card_detail?.name).localeCompare(normalize(b.card_detail?.name)) * dir;
        default:
          return 0;
      }
    });

    return copy;
  }

  private syncExportTypeOrderFromDeck() {
    if (!this.deck) return;
    const entries = [...(this.deck.entries || []), ...(this.deck.sideboard_entries || [])];
    const found = new Set<string>();
    for (const entry of entries) {
      const type = (entry?.card_detail?.type_name || 'Otro').trim() || 'Otro';
      found.add(type);
    }
    if (found.size === 0) return;

    const fallback = [...found].sort((a, b) => {
      const av = this.typeOrder[a] ?? 99;
      const bv = this.typeOrder[b] ?? 99;
      if (av !== bv) return av - bv;
      return a.localeCompare(b, 'es');
    });

    const kept = this.exportTypeOrder.filter((x) => [...found].some((f) => this.normalizeTypeForOrder(f) === this.normalizeTypeForOrder(x)));
    const missing = fallback.filter((x) => !kept.some((k) => this.normalizeTypeForOrder(k) === this.normalizeTypeForOrder(x)));
    this.exportTypeOrder = this.dedupeTypeOrder([...kept, ...missing]);
  }

  private dedupeTypeOrder(values: string[]): string[] {
    const out: string[] = [];
    for (const raw of values || []) {
      const item = (raw || '').trim();
      if (!item) continue;
      if (out.some((x) => this.normalizeTypeForOrder(x) === this.normalizeTypeForOrder(item))) continue;
      out.push(item);
    }
    return out;
  }

  private normalizeTypeForOrder(value: string): string {
    return (value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  private getExportTypeSortWeight(typeName: string | null | undefined): number {
    const normalized = this.normalizeTypeForOrder(typeName || '');
    const idx = this.exportTypeOrder.findIndex((x) => this.normalizeTypeForOrder(x) === normalized);
    if (idx !== -1) return idx;
    const fallback = this.typeOrder[typeName ?? ''] ?? 999;
    return this.exportTypeOrder.length + fallback;
  }

  private async ensureExportQr() {
    if (!this.isPublicDeck || !this.exportShowQr) {
      this.exportQrDataUrl = null;
      return;
    }
    if (this.exportQrDataUrl) return;
    try {
      this.exportQrDataUrl = await this.buildExportQrDataUrl(this.publicDeckUrl);
      if (!this.exportQrDataUrl) {
        throw new Error('No se encontro un generador QR compatible.');
      }
      this.cdr.detectChanges();
    } catch (err) {
      console.warn('No se pudo generar QR para exportación:', err);
      this.exportQrDataUrl = null;
    }
  }

  private async buildExportQrDataUrl(value: string): Promise<string | null> {
    const qrcodeModule: any = await import('qrcode');
    const toDataURL: ((text: string, options?: any) => Promise<string>) | undefined =
      typeof qrcodeModule?.toDataURL === 'function'
        ? qrcodeModule.toDataURL.bind(qrcodeModule)
        : typeof qrcodeModule?.default?.toDataURL === 'function'
          ? qrcodeModule.default.toDataURL.bind(qrcodeModule.default)
          : typeof qrcodeModule?.default === 'function'
            ? qrcodeModule.default
            : undefined;

    if (!toDataURL) return null;

    return toDataURL(value, {
      width: 180,
      margin: 1,
      // Fondo sólido para garantizar legibilidad en html2canvas.
      color: { dark: '#0a1320', light: '#ffffff' },
    });
  }

  private readonly formatNames: Record<string, string> = {
    imp: 'Imperio', esc: 'Escuelas Elementales', imp_r: 'Imperio Retro',
  };

  get formatLabel(): string {
    const base = this.formatNames[this.deck?.format || 'imp'] || 'Imperio';
    if (this.deck?.sub_format === 'vcr') return base + ' · VCR';
    return base;
  }

  get raceLabel(): string {
    if (!this.deck?.race) return '';
    const names: Record<string, string> = {
      dream: 'Dream', totem: 'Tótem', eterno: 'Eterno', faerie: 'Faerie',
      dragon: 'Dragón', sombra: 'Sombra', heroe: 'Héroe', sacerdote: 'Sacerdote',
      guerrero: 'Guerrero', bestia: 'Bestia', caballero: 'Caballero',
      ancestral: 'Ancestral', barbaro: 'Bárbaro', samurai: 'Samurái', oni: 'Oni',
      'culto-tenebris': 'Culto Tenebris', 'vigilantes-etereos': 'Vigilantes Etéreos',
      'gremio-paladin': 'Gremio Paladín', 'clan-desafiante': 'Clan Desafiante',
      oscuridad: 'Oscuridad', luz: 'Luz',
    };
    return names[this.deck.race] || this.deck.race;
  }

  get todayFormatted(): string {
    return new Date().toLocaleDateString('es-CL', { day: 'numeric', month: 'long', year: 'numeric' });
  }

  private thumbPipe = new ThumbnailPipe();

  // ── Hand Simulator ──

  /** Build a flat pool of cards expanded by quantity (main deck only) */
  private get cardPool(): Card[] {
    if (!this.deck?.entries) return [];
    const pool: Card[] = [];
    for (const entry of this.deck.entries) {
      for (let i = 0; i < entry.quantity; i++) {
        pool.push(entry.card_detail);
      }
    }
    return pool;
  }

  /** Pool without the starting gold (it starts on the field, never drawn). */
  private get shufflePool(): Card[] {
    const sgId = this.deck?.starting_gold;
    if (!sgId) return this.cardPool;
    const pool = this.cardPool;
    // Remove exactly one copy of the starting gold from the pool
    const idx = pool.findIndex(c => c.id === sgId);
    if (idx !== -1) pool.splice(idx, 1);
    return pool;
  }

  /** The starting gold Card object, if set and present in the deck. */
  get startingGoldCard(): Card | null {
    const sgId = this.deck?.starting_gold;
    if (!sgId || !this.deck?.entries) return null;
    const entry = this.deck.entries.find(e => e.card_detail.id === sgId);
    return entry ? entry.card_detail : null;
  }

  /** Fisher-Yates shuffle and take n */
  private drawRandom(pool: Card[], n: number): Card[] {
    const arr = [...pool];
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr.slice(0, Math.min(n, arr.length));
  }

  drawHand() {
    this.handSize = 8;
    this.handCards = this.drawRandom(this.shufflePool, 8);
    this.handActive = true;
  }

  mulligan() {
    if (this.handSize <= 1) return;
    this.handSize--;
    this.handCards = this.drawRandom(this.shufflePool, this.handSize);
  }

  resetHand() {
    this.handSize = 8;
    this.handCards = this.drawRandom(this.shufflePool, 8);
  }

  handleDeckImageError(event: Event | string, originalUrl: string | null | undefined) {
    const img = typeof event === 'string' ? null : (event.target as HTMLImageElement | null);
    if (!img) return;

    const current = img.currentSrc || img.src || '';
    const fallbackStage = img.dataset['fallbackStage'] || '';
    const rewritten = this.rewriteLegacyCloudinaryUrl(originalUrl);

    // If we received a legacy Cloudinary URL, try active cloud first.
    if (rewritten && rewritten !== current && fallbackStage !== 'rewritten') {
      img.dataset['fallbackStage'] = 'rewritten';
      img.onerror = null;
      img.src = rewritten;
      img.onerror = (e) => this.handleDeckImageError(e, originalUrl);
      return;
    }

    // If thumbnail URL failed, try the original source URL once.
    if (originalUrl && originalUrl !== current && fallbackStage !== 'original') {
      img.dataset['fallbackStage'] = 'original';
      img.onerror = null;
      img.src = originalUrl;
      img.onerror = (e) => this.handleDeckImageError(e, originalUrl);
      return;
    }

    // If source is an external URL without CORS, retry through Cloudinary fetch.
    const cloudinaryFetch = this.toCloudinaryFetchUrl(originalUrl);
    if (cloudinaryFetch && cloudinaryFetch !== current && fallbackStage !== 'fetch') {
      img.dataset['fallbackStage'] = 'fetch';
      img.onerror = null;
      img.src = cloudinaryFetch;
      img.onerror = (e) => this.handleDeckImageError(e, originalUrl);
      return;
    }

    img.onerror = null;
    img.src = this.deckImagePlaceholder;
  }

  private toCloudinaryFetchUrl(url: string | null | undefined): string | null {
    if (!url || typeof url !== 'string') return null;
    const clean = url.trim();
    if (!clean) return null;

    const lower = clean.toLowerCase();
    if (lower.startsWith('data:') || lower.startsWith('blob:')) return null;
    if (lower.includes('res.cloudinary.com/')) return null;

    const normalized = clean.startsWith('//') ? `https:${clean}` : clean;
    const encoded = encodeURIComponent(normalized);
    return `https://res.cloudinary.com/daobfx9yb/image/fetch/${encoded}`;
  }

  private isCdnCanvasSafeUrl(url: string): boolean {
    const lower = url.toLowerCase();
    if (lower.includes('ik.imagekit.io/')) return true;
    if (lower.includes('res.cloudinary.com/')) return true;
    if (lower.includes('.r2.dev/') || lower.includes('.r2.cloudflarestorage.com/')) return true;
    return false;
  }

  getExportImageUrl(url: string | null | undefined): string {
    const thumb = this.thumbPipe.transform(url ?? '', 350);
    if (!thumb) return this.deckImagePlaceholder;

    const rewritten = this.rewriteLegacyCloudinaryUrl(thumb) || thumb;
    const lower = rewritten.toLowerCase();
    if (lower.startsWith('data:') || lower.startsWith('blob:')) return rewritten;
    if (this.isCdnCanvasSafeUrl(rewritten)) return rewritten;

    return this.toCloudinaryFetchUrl(rewritten) || rewritten;
  }

  private rewriteLegacyCloudinaryUrl(url: string | null | undefined): string | null {
    if (!url) return null;
    const rewritten = url.replace(
      /res\.cloudinary\.com\/(drw7y27sm|dmvu6tuee)\//i,
      'res.cloudinary.com/daobfx9yb/',
    );
    return rewritten !== url ? rewritten : null;
  }

  /** Preload card images in background so they're cached for viewing & export */
  private preloadImages() {
    if (!this.deck) return;
    const urls = new Set<string>();
    const allEntries = [...(this.deck.entries || []), ...(this.deck.sideboard_entries || [])];
    for (const entry of allEntries) {
      const url = entry.card_detail.image_url;
      if (url) {
        urls.add(this.thumbPipe.transform(url, 250)); // grid view
        urls.add(this.thumbPipe.transform(url, 350)); // export
      }
    }
    for (const url of urls) {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.src = url;
    }
  }

  private getRaceBackground(): string {
    const raceColors: Record<string, string> = {
      dream: '#1a0a2e', totem: '#0a1e0a', eterno: '#1e1e2e', faerie: '#1a0e28',
      dragon: '#2e0a0a', sombra: '#0a0a1e', heroe: '#1e1a0a', sacerdote: '#1e1e0a',
      guerrero: '#2e1a0a', bestia: '#0a1e1a', caballero: '#1a1a2e',
      ancestral: '#1e0a1e', barbaro: '#2e1a1a', samurai: '#1e0a0a', oni: '#1e0a1a',
      'culto-tenebris': '#0e0a1e', 'vigilantes-etereos': '#0a1a2e',
      'gremio-paladin': '#1e1e0a', 'clan-desafiante': '#2e0e0a',
      oscuridad: '#0a0a0e', luz: '#1e1e1a',
    };
    return raceColors[this.deck?.race ?? ''] || '#0f0f23';
  }

  async exportImage() {
    const canvas = await this.renderExportCanvas();
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `${this.deck?.name || 'mazo'}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }

  private async renderExportCanvas(): Promise<HTMLCanvasElement | null> {
    if (!this.deckContent || this.exporting) return null;
    this.exporting = true;
    this.cdr.detectChanges();
    try {
      await this.ensureExportQr();
      this.syncStackOrientationFromStorage();
      this.cdr.detectChanges();
      const el = this.deckContent.nativeElement as HTMLElement;
      await this.nextRenderTick();
      await this.waitForExportImages(el);
      await this.nextRenderTick();
      const targetWidth = this.exportOrientation === 'horizontal' ? 1200 : 780;
      const html2canvas = (await import('html2canvas')).default;
      return await html2canvas(el, {
        backgroundColor: this.exportBackgroundResolved,
        useCORS: true,
        allowTaint: true,
        scale: 2,
        width: targetWidth,
        height: el.scrollHeight,
        windowWidth: targetWidth,
        windowHeight: el.scrollHeight,
      });
    } catch (e) {
      console.error('Error generando canvas de exportación:', e);
      return null;
    } finally {
      this.exporting = false;
      this.cdr.detectChanges();
    }
  }

  private nextRenderTick(): Promise<void> {
    return new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
  }

  private waitForExportImages(el: HTMLElement): Promise<void[]> {
    const imgs = Array.from(el.querySelectorAll('img')) as HTMLImageElement[];
    return Promise.all(imgs.map((img) => {
      img.loading = 'eager';
      if (img.complete && img.naturalWidth > 0) return Promise.resolve();
      return new Promise<void>((resolve) => {
        const done = () => resolve();
        img.addEventListener('load', done, { once: true });
        img.addEventListener('error', done, { once: true });
        if (img.complete) resolve();
      });
    }));
  }

  private isValidStackOrientation(value: unknown): value is StackOrientation {
    return value === 'down' || value === 'up' || value === 'left' || value === 'right' || value === 'center';
  }

  private syncStackOrientationFromStorage() {
    try {
      const saved = localStorage.getItem(this.stackOrientationStorageKey);
      if (this.isValidStackOrientation(saved)) {
        this.stackOrientation = saved;
      }
    } catch {}
  }
}
