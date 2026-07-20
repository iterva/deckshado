import { Component, OnDestroy, OnInit, signal, computed, ElementRef, HostListener, ViewChild } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../services/auth.service';
import { AdminUser } from '../../models';
import {
  RiftboundService,
  RiftcodexAuditStatus,
  RiftcodexSyncStatus,
  RiftcodexOpsRunItem,
} from '../../services/riftbound.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, DatePipe],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.scss',
})
export class AdminComponent implements OnInit, OnDestroy {
  private readonly apiUrl = `${environment.apiUrl}/auth/admin`;
  readonly cardsToolsAdminUrl = this.buildAdminToolsUrl('/admin/cards-tools/');
  readonly riftboundToolsAdminUrl = this.buildAdminToolsUrl('/admin/riftbound-tools/');

  users = signal<AdminUser[]>([]);
  loading = signal(false);
  searchQuery = '';
  message = signal('');
  error = signal('');
  opsLoading = signal(false);
  runningSync = signal(false);
  runningAudit = signal(false);
  syncStatus = signal<RiftcodexSyncStatus | null>(null);
  auditStatus = signal<RiftcodexAuditStatus | null>(null);
  opsRuns = signal<RiftcodexOpsRunItem[]>([]);
  rerunRunningId = signal<number | null>(null);
  outputModalOpen = signal(false);
  outputModalTitle = signal('');
  outputModalBody = signal('');
  runKindFilter: '' | 'sync' | 'audit' = '';
  runStatusFilter: '' | 'running' | 'success' | 'error' = '';
  runSearchQuery = '';
  runsPage = 1;
  runsPageSize = 8;
  runsTotal = 0;
  runsTotalPages = 1;
  autoRefreshPaused = signal(false);
  copyLinkCopied = signal(false);
  copyShortLinkCopied = signal(false);
  copyHint = signal('');
  rerunModalOpen = signal(false);
  rerunModalLoading = signal(false);
  rerunTarget = signal<RiftcodexOpsRunItem | null>(null);
  rerunSyncForm = {
    full: false,
    dry_run: false,
    skip_fixes: false,
    size: 100,
    since: '',
  };
  rerunAuditForm = {
    limit: 50,
  };
  private opsRefreshTimer: ReturnType<typeof setInterval> | null = null;
  private runSearchTimer: ReturnType<typeof setTimeout> | null = null;
  private copyHintTimer: ReturnType<typeof setTimeout> | null = null;
  @ViewChild('shareMenu') shareMenuRef?: ElementRef<HTMLDetailsElement>;

  // Edit modal state
  editing = signal<AdminUser | null>(null);
  editForm = {
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    league_code: '',
    is_active: true,
    is_staff: false,
  };
  saving = signal(false);

  // Password reset modal state
  resettingFor = signal<AdminUser | null>(null);
  newPassword = '';
  resetSaving = signal(false);

  filtered = computed(() => {
    const q = this.searchQuery.trim().toLowerCase();
    if (!q) return this.users();
    return this.users().filter(u =>
      u.username.toLowerCase().includes(q) ||
      (u.email || '').toLowerCase().includes(q)
    );
  });

  constructor(
    private http: HttpClient,
    public auth: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private riftbound: RiftboundService,
  ) {}

  private buildAdminToolsUrl(adminPath: string): string {
    const rawApiUrl = (environment.apiUrl || '').trim();
    if (!rawApiUrl) {
      return adminPath;
    }

    try {
      const parsed = new URL(rawApiUrl);
      const basePath = parsed.pathname.replace(/\/+$/, '').replace(/\/api$/, '');
      parsed.pathname = `${basePath}${adminPath}`.replace(/\/{2,}/g, '/');
      parsed.search = '';
      parsed.hash = '';
      return parsed.toString();
    } catch {
      const trimmed = rawApiUrl.replace(/\/+$/, '');
      return `${trimmed.replace(/\/api$/, '')}${adminPath}`;
    }
  }

  ngOnInit() {
    const me = this.auth.user();
    if (!me?.is_admin) {
      this.router.navigate(['/']);
      return;
    }
    this.loadRunFiltersFromQueryParams();
    this.loadOpsStatus();
    this.loadUsers();
  }

  ngOnDestroy() {
    this.stopOpsAutoRefresh();
    if (this.runSearchTimer) {
      clearTimeout(this.runSearchTimer);
      this.runSearchTimer = null;
    }
    if (this.copyHintTimer) {
      clearTimeout(this.copyHintTimer);
      this.copyHintTimer = null;
    }
    this.closeShareMenu();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    const menu = this.shareMenuRef?.nativeElement;
    if (!menu?.open) return;
    const target = event.target as Node | null;
    if (!target || !menu.contains(target)) {
      menu.open = false;
    }
  }

  @HostListener('document:keydown.escape')
  onDocumentEscape() {
    this.closeShareMenu(true);
  }

  @HostListener('document:keydown', ['$event'])
  onDocumentKeydown(event: KeyboardEvent) {
    if (!this.isShareShortcut(event)) return;
    if (this.isTypingTarget(event.target)) return;
    event.preventDefault();

    if (event.key.toLowerCase() === 'k') {
      this.copyCurrentViewLink();
      return;
    }

    if (event.key.toLowerCase() === 'l') {
      this.copyCompactViewLink();
    }
  }

  closeShareMenu(restoreFocus = false) {
    const menu = this.shareMenuRef?.nativeElement;
    if (menu?.open) {
      menu.open = false;
      if (restoreFocus) this.focusShareSummary();
    }
  }

  onShareSummaryKeydown(event: KeyboardEvent) {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
    event.preventDefault();
    const focusLast = event.key === 'ArrowUp';
    this.openShareMenu(focusLast);
  }

  onShareItemKeydown(event: KeyboardEvent, index: number) {
    const items = this.getShareMenuItems();
    if (!items.length) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      this.closeShareMenu(true);
      return;
    }

    if (event.key === 'Home') {
      event.preventDefault();
      this.focusShareItem(0);
      return;
    }

    if (event.key === 'End') {
      event.preventDefault();
      this.focusShareItem(items.length - 1);
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.focusShareItem((index + 1) % items.length);
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.focusShareItem((index - 1 + items.length) % items.length);
      return;
    }

    if (event.key === 'Tab') {
      this.closeShareMenu();
    }
  }

  private isShareShortcut(event: KeyboardEvent): boolean {
    const key = event.key.toLowerCase();
    return (event.ctrlKey || event.metaKey) && event.shiftKey && (key === 'k' || key === 'l');
  }

  private openShareMenu(focusLast = false) {
    const menu = this.shareMenuRef?.nativeElement;
    if (!menu) return;
    menu.open = true;
    const targetIndex = focusLast ? this.getShareMenuItems().length - 1 : 0;
    setTimeout(() => this.focusShareItem(Math.max(targetIndex, 0)), 0);
  }

  private focusShareSummary() {
    const summary = this.shareMenuRef?.nativeElement.querySelector('summary') as HTMLElement | null;
    summary?.focus();
  }

  private getShareMenuItems(): HTMLButtonElement[] {
    const menu = this.shareMenuRef?.nativeElement;
    if (!menu) return [];
    return Array.from(menu.querySelectorAll('.share-menu-item')) as HTMLButtonElement[];
  }

  private focusShareItem(index: number) {
    const items = this.getShareMenuItems();
    const item = items[index];
    item?.focus();
  }

  private isTypingTarget(target: EventTarget | null): boolean {
    if (!(target instanceof HTMLElement)) return false;
    const tag = target.tagName;
    if (target.isContentEditable) return true;
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
  }

  private loadRunFiltersFromQueryParams() {
    const qp = this.route.snapshot.queryParamMap;

    const kind = (qp.get('rk') || '').toLowerCase();
    if (kind === 'sync' || kind === 'audit') this.runKindFilter = kind;

    const status = (qp.get('rs') || '').toLowerCase();
    if (status === 'running' || status === 'success' || status === 'error') this.runStatusFilter = status;

    this.runSearchQuery = (qp.get('rq') || '').slice(0, 120);

    const page = Number(qp.get('rp') || '1');
    if (Number.isFinite(page) && page >= 1) this.runsPage = Math.floor(page);

    const pageSize = Number(qp.get('rps') || String(this.runsPageSize));
    if ([8, 12, 20].includes(pageSize)) this.runsPageSize = pageSize;

    const pausedRaw = (qp.get('rap') || '').toLowerCase();
    this.autoRefreshPaused.set(pausedRaw === '1' || pausedRaw === 'true' || pausedRaw === 'yes');
  }

  private syncRunFiltersToQueryParams() {
    const qp = this.getRunQueryParamsForRouter();
    this.router.navigate([], {
      relativeTo: this.route,
      replaceUrl: true,
      queryParamsHandling: 'merge',
      queryParams: qp,
    });
  }

  private getRunQueryParamsForRouter() {
    return {
      rk: this.runKindFilter || null,
      rs: this.runStatusFilter || null,
      rq: this.runSearchQuery.trim() || null,
      rp: this.runsPage > 1 ? this.runsPage : null,
      rps: this.runsPageSize !== 8 ? this.runsPageSize : null,
      rap: this.autoRefreshPaused() ? '1' : null,
    };
  }

  activeRunParamCount(): number {
    const qp = this.getRunQueryParamsForRouter();
    return Object.values(qp).filter((v) => v !== null && v !== '').length;
  }

  private buildCurrentViewUrl(compact: boolean): string {
    const qp = this.getRunQueryParamsForRouter();
    const url = new URL(window.location.href);
    if (compact) url.search = '';
    const params = url.searchParams;

    const applyParam = (key: string, value: string | number | null) => {
      if (value === null || value === '') params.delete(key);
      else params.set(key, String(value));
    };

    applyParam('rk', qp.rk as string | null);
    applyParam('rs', qp.rs as string | null);
    applyParam('rq', qp.rq as string | null);
    applyParam('rp', qp.rp as number | null);
    applyParam('rps', qp.rps as number | null);
    applyParam('rap', qp.rap as string | null);

    return url.toString();
  }

  private showCopyHint(text: string) {
    this.copyHint.set(text);
    if (this.copyHintTimer) clearTimeout(this.copyHintTimer);
    this.copyHintTimer = setTimeout(() => this.copyHint.set(''), 1800);
  }

  copyCurrentViewLink() {
    const finalUrl = this.buildCurrentViewUrl(false);

    navigator.clipboard.writeText(finalUrl)
      .then(() => {
        this.copyLinkCopied.set(true);
        this.copyShortLinkCopied.set(false);
        this.showCopyHint('Enlace completo copiado');
        this.message.set('Enlace del panel copiado.');
        setTimeout(() => this.copyLinkCopied.set(false), 1800);
        setTimeout(() => this.message.set(''), 2500);
      })
      .catch(() => {
        this.copyLinkCopied.set(false);
        this.copyShortLinkCopied.set(false);
        this.error.set('No se pudo copiar el enlace del panel.');
        setTimeout(() => this.error.set(''), 3000);
      });
  }

  copyCompactViewLink() {
    const paramsCount = this.activeRunParamCount();
    const finalUrl = this.buildCurrentViewUrl(true);
    navigator.clipboard.writeText(finalUrl)
      .then(() => {
        this.copyShortLinkCopied.set(true);
        this.copyLinkCopied.set(false);
        this.showCopyHint(`Enlace corto copiado (${paramsCount} params)`);
        this.message.set(`Enlace corto del panel copiado (${paramsCount} params).`);
        setTimeout(() => this.copyShortLinkCopied.set(false), 1800);
        setTimeout(() => this.message.set(''), 2500);
      })
      .catch(() => {
        this.copyShortLinkCopied.set(false);
        this.error.set('No se pudo copiar el enlace corto del panel.');
        setTimeout(() => this.error.set(''), 3000);
      });
  }

  resetOpsViewDefaults() {
    this.runSearchQuery = '';
    this.runKindFilter = '';
    this.runStatusFilter = '';
    this.runsPageSize = 8;
    this.runsPage = 1;
    this.autoRefreshPaused.set(false);
    this.syncRunFiltersToQueryParams();
    this.updateOpsAutoRefresh();
    this.loadOpsStatus();
  }

  loadOpsStatus() {
    this.opsLoading.set(true);
    this.riftbound.getOpsOverview({
      kind: this.runKindFilter,
      status: this.runStatusFilter,
      q: this.runSearchQuery.trim() || undefined,
      page: this.runsPage,
      page_size: this.runsPageSize,
    }).subscribe({
      next: (overview) => {
        this.syncStatus.set(overview.sync as RiftcodexSyncStatus);
        this.auditStatus.set(overview.audit as RiftcodexAuditStatus);
        this.opsRuns.set(overview.runs || []);
        this.runsTotal = overview.runs_pagination?.total ?? (overview.runs?.length || 0);
        this.runsTotalPages = overview.runs_pagination?.total_pages ?? 1;
        this.runsPage = overview.runs_pagination?.page ?? this.runsPage;
        this.opsLoading.set(false);
        this.updateOpsAutoRefresh();
      },
      error: () => {
        // Fallback para compatibilidad durante despliegues parciales.
        this.riftbound.getSyncStatus().subscribe({
          next: (status) => {
            this.syncStatus.set(status);
            this.opsLoading.set(false);
          },
          error: () => {
            this.syncStatus.set(null);
            this.opsLoading.set(false);
          },
        });

        this.riftbound.getAuditStatus().subscribe({
          next: (status) => this.auditStatus.set(status),
          error: () => this.auditStatus.set(null),
        });
        this.opsRuns.set([]);
        this.runsTotal = 0;
        this.runsTotalPages = 1;
        this.updateOpsAutoRefresh();
      },
    });
  }

  private updateOpsAutoRefresh() {
    const hasRunningRun = this.opsRuns().some((run) => run.status === 'running');
    const hasRunningAction = this.runningSync() || this.runningAudit() || !!this.rerunRunningId();
    const shouldRefresh = !this.autoRefreshPaused() && (hasRunningRun || hasRunningAction);
    if (shouldRefresh) {
      if (!this.opsRefreshTimer) {
        this.opsRefreshTimer = setInterval(() => {
          if (!this.opsLoading()) this.loadOpsStatus();
        }, 7000);
      }
      return;
    }
    this.stopOpsAutoRefresh();
  }

  private stopOpsAutoRefresh() {
    if (this.opsRefreshTimer) {
      clearInterval(this.opsRefreshTimer);
      this.opsRefreshTimer = null;
    }
  }

  applyRunFilters() {
    if (this.runSearchTimer) {
      clearTimeout(this.runSearchTimer);
      this.runSearchTimer = null;
    }
    this.runsPage = 1;
    this.syncRunFiltersToQueryParams();
    this.loadOpsStatus();
  }

  onRunSearchInput() {
    if (this.runSearchTimer) clearTimeout(this.runSearchTimer);
    this.runSearchTimer = setTimeout(() => this.applyRunFilters(), 350);
  }

  clearRunSearch() {
    this.runSearchQuery = '';
    this.applyRunFilters();
  }

  clearRunKindFilter() {
    if (!this.runKindFilter) return;
    this.runKindFilter = '';
    this.applyRunFilters();
  }

  clearRunStatusFilter() {
    if (!this.runStatusFilter) return;
    this.runStatusFilter = '';
    this.applyRunFilters();
  }

  resetRunsPageSize() {
    if (this.runsPageSize === 8) return;
    this.runsPageSize = 8;
    this.onRunsPageSizeChange();
  }

  resetAllRunFilters() {
    this.runSearchQuery = '';
    this.runKindFilter = '';
    this.runStatusFilter = '';
    this.runsPageSize = 8;
    this.applyRunFilters();
  }

  hasAnyRunFilter(): boolean {
    return !!this.runSearchQuery.trim() || !!this.runKindFilter || !!this.runStatusFilter || this.runsPageSize !== 8;
  }

  toggleAutoRefreshPause() {
    this.autoRefreshPaused.update((v) => !v);
    this.syncRunFiltersToQueryParams();
    this.updateOpsAutoRefresh();
  }

  isLiveRefreshing(): boolean {
    return !this.autoRefreshPaused() && !!this.opsRefreshTimer;
  }

  changeRunsPage(delta: number) {
    const target = this.runsPage + delta;
    if (target < 1 || target > this.runsTotalPages) return;
    this.runsPage = target;
    this.syncRunFiltersToQueryParams();
    this.loadOpsStatus();
  }

  onRunsPageSizeChange() {
    this.runsPage = 1;
    this.syncRunFiltersToQueryParams();
    this.loadOpsStatus();
  }

  openOutputModal(title: string, body: string) {
    this.outputModalTitle.set(title);
    this.outputModalBody.set(body || 'Sin salida disponible.');
    this.outputModalOpen.set(true);
  }

  closeOutputModal() {
    this.outputModalOpen.set(false);
  }

  viewRunOutput(run: RiftcodexOpsRunItem) {
    this.openOutputModal(`Run #${run.id} · ${run.command} · ${run.status}`, 'Cargando output...');
    this.riftbound.getOpsRun(run.id).subscribe({
      next: (fullRun) => {
        const detail = fullRun.error
          ? `${fullRun.error}\n\n${fullRun.output || ''}`
          : (fullRun.output || fullRun.output_excerpt || 'Sin salida registrada.');
        this.openOutputModal(`Run #${fullRun.id} · ${fullRun.command} · ${fullRun.status}`, detail);
      },
      error: () => {
        const detail = run.error
          ? `${run.error}\n\n${run.output_excerpt || run.output || ''}`
          : (run.output_excerpt || run.output || 'Sin salida registrada.');
        this.openOutputModal(`Run #${run.id} · ${run.command} · ${run.status}`, detail);
      },
    });
  }

  openRerunModal(run: RiftcodexOpsRunItem) {
    if (run.status === 'running') return;
    this.rerunTarget.set(run);
    this.rerunModalOpen.set(true);
    this.rerunModalLoading.set(true);
    this.riftbound.getOpsRun(run.id).subscribe({
      next: (fullRun) => {
        this.rerunTarget.set(fullRun);
        const args = (fullRun.args || {}) as Record<string, any>;
        if (fullRun.kind === 'sync') {
          this.rerunSyncForm = {
            full: !!args['full'],
            dry_run: !!args['dry_run'],
            skip_fixes: !!args['skip_fixes'],
            size: Number(args['size'] || 100),
            since: String(args['since'] || ''),
          };
        } else {
          this.rerunAuditForm = {
            limit: Number(args['limit'] || 50),
          };
        }
        this.rerunModalLoading.set(false);
      },
      error: () => {
        if (run.kind === 'sync') {
          this.rerunSyncForm = {
            full: false,
            dry_run: false,
            skip_fixes: false,
            size: 100,
            since: '',
          };
        } else {
          this.rerunAuditForm = { limit: 50 };
        }
        this.rerunModalLoading.set(false);
      },
    });
  }

  closeRerunModal() {
    this.rerunModalOpen.set(false);
    this.rerunModalLoading.set(false);
    this.rerunTarget.set(null);
  }

  submitRerunModal() {
    const run = this.rerunTarget();
    if (!run || run.status === 'running') return;

    const payload: Record<string, any> = run.kind === 'sync'
      ? {
          full: !!this.rerunSyncForm.full,
          dry_run: !!this.rerunSyncForm.dry_run,
          skip_fixes: !!this.rerunSyncForm.skip_fixes,
          size: Math.max(1, Math.min(100, Number(this.rerunSyncForm.size || 100))),
          since: (this.rerunSyncForm.since || '').trim(),
        }
      : {
          limit: Math.max(1, Math.min(500, Number(this.rerunAuditForm.limit || 50))),
        };

    if (!payload['since']) delete payload['since'];

    this.rerunRunningId.set(run.id);
    this.updateOpsAutoRefresh();
    this.riftbound.rerunOpsRun(run.id, payload).subscribe({
      next: (res) => {
        this.rerunRunningId.set(null);
        this.message.set(`Re-run ejecutado. Nuevo run #${res.run_id ?? 'N/A'}.`);
        this.openOutputModal(`Re-run de #${run.id}`, res.output || 'Sin salida.');
        this.closeRerunModal();
        this.loadOpsStatus();
        setTimeout(() => this.message.set(''), 4000);
      },
      error: (err) => {
        this.rerunRunningId.set(null);
        const output = err?.error?.output || err?.error?.error || 'Sin salida.';
        this.openOutputModal(`Error re-run #${run.id}`, output);
        this.error.set(err?.error?.detail || err?.error?.error || 'No se pudo re-ejecutar esta operación.');
        this.updateOpsAutoRefresh();
        setTimeout(() => this.error.set(''), 5000);
      },
    });
  }

  copyOutput() {
    const text = this.outputModalBody();
    if (!text) return;
    navigator.clipboard.writeText(text)
      .then(() => {
        this.message.set('Output copiado al portapapeles.');
        setTimeout(() => this.message.set(''), 3000);
      })
      .catch(() => {
        this.error.set('No se pudo copiar el output.');
        setTimeout(() => this.error.set(''), 3000);
      });
  }

  runSync() {
    if (!confirm('Ejecutar sincronización incremental ahora?')) return;
    this.runningSync.set(true);
    this.updateOpsAutoRefresh();
    this.riftbound.runSyncOperation({ size: 100 }).subscribe({
      next: (res) => {
        this.runningSync.set(false);
        this.message.set(`Sync ejecutada. ${res.command}`);
        this.openOutputModal(`Sync #${res.run_id ?? 'N/A'}`, res.output || 'Sin salida.');
        this.loadOpsStatus();
        setTimeout(() => this.message.set(''), 4000);
      },
      error: (err) => {
        this.runningSync.set(false);
        const output = err?.error?.output || err?.error?.error || 'Sin salida.';
        this.openOutputModal('Error Sync', output);
        this.error.set(err?.error?.error || err?.error?.detail || 'No se pudo ejecutar sync.');
        this.updateOpsAutoRefresh();
        setTimeout(() => this.error.set(''), 5000);
      },
    });
  }

  runAudit() {
    if (!confirm('Ejecutar auditoría ahora?')) return;
    this.runningAudit.set(true);
    this.updateOpsAutoRefresh();
    this.riftbound.runAuditOperation({ limit: 50 }).subscribe({
      next: (res) => {
        this.runningAudit.set(false);
        this.message.set(`Auditoría ejecutada. ${res.command}`);
        this.openOutputModal(`Audit #${res.run_id ?? 'N/A'}`, res.output || 'Sin salida.');
        this.loadOpsStatus();
        setTimeout(() => this.message.set(''), 4000);
      },
      error: (err) => {
        this.runningAudit.set(false);
        const output = err?.error?.output || err?.error?.error || 'Sin salida.';
        this.openOutputModal('Error Auditoría', output);
        this.error.set(err?.error?.error || err?.error?.detail || 'No se pudo ejecutar auditoría.');
        this.updateOpsAutoRefresh();
        setTimeout(() => this.error.set(''), 5000);
      },
    });
  }

  downloadAuditCsv() {
    this.riftbound.downloadAuditCsv().subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
        a.href = url;
        a.download = `riftcodex_audit_${stamp}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      },
      error: () => {
        this.error.set('No se pudo descargar el CSV de auditoría.');
        setTimeout(() => this.error.set(''), 5000);
      },
    });
  }

  loadUsers() {
    this.loading.set(true);
    this.error.set('');
    this.http.get<AdminUser[]>(`${this.apiUrl}/users/`).subscribe({
      next: (data) => {
        this.users.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err?.error?.detail || 'No se pudieron cargar los usuarios.');
        this.loading.set(false);
      },
    });
  }

  toggleActive(u: AdminUser) {
    const action = u.is_active ? 'banear' : 'reactivar';
    if (!confirm(`¿Seguro que deseas ${action} a "${u.username}"?`)) return;
    this.http.patch<AdminUser>(`${this.apiUrl}/users/${u.id}/`, {
      is_active: !u.is_active,
    }).subscribe({
      next: (updated) => {
        this.users.update(list => list.map(x => x.id === updated.id ? updated : x));
        this.message.set(`Usuario "${updated.username}" ${updated.is_active ? 'reactivado' : 'baneado'}.`);
        setTimeout(() => this.message.set(''), 3000);
      },
      error: (err) => {
        this.error.set(err?.error?.detail || 'Error al actualizar el usuario.');
        setTimeout(() => this.error.set(''), 4000);
      },
    });
  }

  toggleStaff(u: AdminUser) {
    if (!confirm(`¿Cambiar permisos de staff para "${u.username}"?`)) return;
    this.http.patch<AdminUser>(`${this.apiUrl}/users/${u.id}/`, {
      is_staff: !u.is_staff,
    }).subscribe({
      next: (updated) => {
        this.users.update(list => list.map(x => x.id === updated.id ? updated : x));
      },
      error: (err) => {
        this.error.set(err?.error?.detail || 'Error al actualizar permisos.');
        setTimeout(() => this.error.set(''), 4000);
      },
    });
  }

  openEdit(u: AdminUser) {
    this.editing.set(u);
    this.editForm = {
      username: u.username,
      email: u.email || '',
      first_name: u.first_name || '',
      last_name: u.last_name || '',
      league_code: u.league_code || '',
      is_active: u.is_active,
      is_staff: u.is_staff,
    };
  }

  closeEdit() {
    this.editing.set(null);
  }

  saveEdit() {
    const target = this.editing();
    if (!target) return;
    this.saving.set(true);
    this.http.patch<AdminUser>(`${this.apiUrl}/users/${target.id}/`, this.editForm).subscribe({
      next: (updated) => {
        this.users.update(list => list.map(x => x.id === updated.id ? updated : x));
        this.saving.set(false);
        this.editing.set(null);
        this.message.set('Usuario actualizado correctamente.');
        setTimeout(() => this.message.set(''), 3000);
      },
      error: (err) => {
        this.saving.set(false);
        this.error.set(err?.error?.detail || JSON.stringify(err?.error) || 'Error al guardar.');
        setTimeout(() => this.error.set(''), 5000);
      },
    });
  }

  openReset(u: AdminUser) {
    this.resettingFor.set(u);
    this.newPassword = '';
  }

  closeReset() {
    this.resettingFor.set(null);
    this.newPassword = '';
  }

  saveReset() {
    const target = this.resettingFor();
    if (!target) return;
    if (this.newPassword.length < 8) {
      this.error.set('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    this.resetSaving.set(true);
    this.http.post<{ detail: string }>(
      `${this.apiUrl}/users/${target.id}/reset-password/`,
      { new_password: this.newPassword },
    ).subscribe({
      next: () => {
        this.resetSaving.set(false);
        this.resettingFor.set(null);
        this.newPassword = '';
        this.message.set(`Contraseña de "${target.username}" actualizada.`);
        setTimeout(() => this.message.set(''), 3000);
      },
      error: (err) => {
        this.resetSaving.set(false);
        this.error.set(err?.error?.detail || 'Error al cambiar contraseña.');
        setTimeout(() => this.error.set(''), 4000);
      },
    });
  }
}
