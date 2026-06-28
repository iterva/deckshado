import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { convertToParamMap, Router } from '@angular/router';
import { of } from 'rxjs';

import { AdminComponent } from './admin.component';
import { AuthService } from '../../services/auth.service';
import { RiftboundService } from '../../services/riftbound.service';
import { ActivatedRoute } from '@angular/router';

describe('AdminComponent share menu', () => {
  let routerNavigateSpy: ReturnType<typeof vi.fn>;

  const setupComponent = () => {
    const fixture = TestBed.createComponent(AdminComponent);
    const component = fixture.componentInstance;
    vi.spyOn(component, 'loadUsers').mockImplementation(() => {});
    vi.spyOn(component, 'loadOpsStatus').mockImplementation(() => {});
    fixture.detectChanges();
    return { fixture, component };
  };

  beforeEach(async () => {
    routerNavigateSpy = vi.fn();
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      configurable: true,
    });

    await TestBed.configureTestingModule({
      imports: [AdminComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: AuthService,
          useValue: {
            user: () => ({ id: 1, username: 'admin', is_admin: true }),
          },
        },
        {
          provide: Router,
          useValue: {
            navigate: routerNavigateSpy,
          },
        },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              queryParamMap: convertToParamMap({}),
            },
          },
        },
        {
          provide: RiftboundService,
          useValue: {
            getOpsOverview: () => of({
              sync: { status: 'ok' },
              audit: { status: 'ok' },
              runs: [],
              runs_pagination: { total: 0, total_pages: 1, page: 1 },
            }),
            getSyncStatus: () => of({ status: 'ok' }),
            getAuditStatus: () => of({ status: 'ok' }),
            runSync: () => of({ output: '' }),
            runAudit: () => of({ output: '' }),
            downloadAuditCsv: () => of(new Blob(['id'])),
            getOpsRun: () => of({ id: 1, output: '', error: '' }),
            rerunOpsRun: () => of({ output: '' }),
          },
        },
      ],
    }).compileComponents();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('opens the share menu with ArrowDown and focuses the first item', () => {
    vi.useFakeTimers();
    const { fixture, component } = setupComponent();

    const menu = fixture.nativeElement.querySelector('details.share-menu-details') as HTMLDetailsElement;
    const items = fixture.nativeElement.querySelectorAll('.share-menu-item') as NodeListOf<HTMLButtonElement>;

    const event = new KeyboardEvent('keydown', { key: 'ArrowDown' });
    component.onShareSummaryKeydown(event);
    vi.runAllTimers();

    expect(menu.open).toBe(true);
    expect(document.activeElement).toBe(items[0]);
  });

  it('opens the share menu with ArrowUp and focuses the last item', () => {
    vi.useFakeTimers();
    const { fixture, component } = setupComponent();

    const menu = fixture.nativeElement.querySelector('details.share-menu-details') as HTMLDetailsElement;
    const items = fixture.nativeElement.querySelectorAll('.share-menu-item') as NodeListOf<HTMLButtonElement>;

    const event = new KeyboardEvent('keydown', { key: 'ArrowUp' });
    component.onShareSummaryKeydown(event);
    vi.runAllTimers();

    expect(menu.open).toBe(true);
    expect(document.activeElement).toBe(items[items.length - 1]);
  });

  it('closes the menu on outside click', () => {
    const { fixture, component } = setupComponent();

    const menu = fixture.nativeElement.querySelector('details.share-menu-details') as HTMLDetailsElement;
    menu.open = true;

    component.onDocumentClick(new MouseEvent('click'));

    expect(menu.open).toBe(false);
  });

  it('supports shortcuts for full and compact links outside inputs only', () => {
    const { component } = setupComponent();

    const fullSpy = vi.spyOn(component, 'copyCurrentViewLink').mockImplementation(() => {});
    const compactSpy = vi.spyOn(component, 'copyCompactViewLink').mockImplementation(() => {});

    const fullEvent = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, shiftKey: true });
    component.onDocumentKeydown(fullEvent);
    expect(fullSpy).toHaveBeenCalledTimes(1);

    const compactEvent = new KeyboardEvent('keydown', { key: 'l', ctrlKey: true, shiftKey: true });
    component.onDocumentKeydown(compactEvent);
    expect(compactSpy).toHaveBeenCalledTimes(1);

    const input = document.createElement('input');
    const blockedEvent = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, shiftKey: true });
    Object.defineProperty(blockedEvent, 'target', { value: input });
    component.onDocumentKeydown(blockedEvent);

    expect(fullSpy).toHaveBeenCalledTimes(1);
  });

  it('restores focus to summary when closing with Escape from a menu item', () => {
    const { fixture, component } = setupComponent();

    const menu = fixture.nativeElement.querySelector('details.share-menu-details') as HTMLDetailsElement;
    const summary = fixture.nativeElement.querySelector('summary') as HTMLElement;
    const items = fixture.nativeElement.querySelectorAll('.share-menu-item') as NodeListOf<HTMLButtonElement>;

    menu.open = true;
    items[1].focus();

    const event = new KeyboardEvent('keydown', { key: 'Escape' });
    component.onShareItemKeydown(event, 1);

    expect(menu.open).toBe(false);
    expect(document.activeElement).toBe(summary);
  });

  it('wraps menu item focus with ArrowDown and ArrowUp', () => {
    const { fixture, component } = setupComponent();

    const menu = fixture.nativeElement.querySelector('details.share-menu-details') as HTMLDetailsElement;
    const items = fixture.nativeElement.querySelectorAll('.share-menu-item') as NodeListOf<HTMLButtonElement>;

    menu.open = true;
    items[1].focus();

    const down = new KeyboardEvent('keydown', { key: 'ArrowDown' });
    component.onShareItemKeydown(down, 1);
    expect(document.activeElement).toBe(items[0]);

    const up = new KeyboardEvent('keydown', { key: 'ArrowUp' });
    component.onShareItemKeydown(up, 0);
    expect(document.activeElement).toBe(items[1]);
  });

  it('moves focus with Home and End keys inside menu items', () => {
    const { fixture, component } = setupComponent();

    const menu = fixture.nativeElement.querySelector('details.share-menu-details') as HTMLDetailsElement;
    const items = fixture.nativeElement.querySelectorAll('.share-menu-item') as NodeListOf<HTMLButtonElement>;

    menu.open = true;
    items[1].focus();

    const home = new KeyboardEvent('keydown', { key: 'Home' });
    component.onShareItemKeydown(home, 1);
    expect(document.activeElement).toBe(items[0]);

    const end = new KeyboardEvent('keydown', { key: 'End' });
    component.onShareItemKeydown(end, 0);
    expect(document.activeElement).toBe(items[1]);
  });

  it('closes menu on Tab from an item', () => {
    const { fixture, component } = setupComponent();

    const menu = fixture.nativeElement.querySelector('details.share-menu-details') as HTMLDetailsElement;
    menu.open = true;

    const tab = new KeyboardEvent('keydown', { key: 'Tab' });
    component.onShareItemKeydown(tab, 0);

    expect(menu.open).toBe(false);
  });

  it('closes menu and restores summary focus on document Escape', () => {
    const { fixture, component } = setupComponent();

    const menu = fixture.nativeElement.querySelector('details.share-menu-details') as HTMLDetailsElement;
    const summary = fixture.nativeElement.querySelector('summary') as HTMLElement;

    menu.open = true;
    component.onDocumentEscape();

    expect(menu.open).toBe(false);
    expect(document.activeElement).toBe(summary);
  });

  it('copies full link and resets copy indicators after timers', async () => {
    vi.useFakeTimers();
    const { component } = setupComponent();
    const writeText = (navigator.clipboard.writeText as ReturnType<typeof vi.fn>);

    component.copyCurrentViewLink();
    await Promise.resolve();

    expect(writeText).toHaveBeenCalledTimes(1);
    expect(component.copyLinkCopied()).toBe(true);
    expect(component.copyShortLinkCopied()).toBe(false);
    expect(component.copyHint()).toContain('Enlace completo copiado');
    expect(component.message()).toContain('Enlace del panel copiado');

    vi.runAllTimers();

    expect(component.copyLinkCopied()).toBe(false);
    expect(component.copyHint()).toBe('');
    expect(component.message()).toBe('');
  });

  it('copies compact link with active params count in feedback', async () => {
    const { component } = setupComponent();
    const writeText = (navigator.clipboard.writeText as ReturnType<typeof vi.fn>);

    component.runKindFilter = 'sync';
    component.runStatusFilter = 'success';
    component.runSearchQuery = 'dragon';
    component.runsPage = 2;

    const paramsCount = component.activeRunParamCount();
    component.copyCompactViewLink();
    await Promise.resolve();

    expect(writeText).toHaveBeenCalledTimes(1);
    expect(component.copyShortLinkCopied()).toBe(true);
    expect(component.copyLinkCopied()).toBe(false);
    expect(component.copyHint()).toContain(`(${paramsCount} params)`);
    expect(component.message()).toContain(`(${paramsCount} params)`);
  });

  it('sets error when clipboard copy fails', async () => {
    vi.useFakeTimers();
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockRejectedValue(new Error('no clipboard')) },
      configurable: true,
    });

    const { component } = setupComponent();
    component.copyCurrentViewLink();
    await Promise.resolve();
    await Promise.resolve();

    expect(component.copyLinkCopied()).toBe(false);
    expect(component.copyShortLinkCopied()).toBe(false);
    expect(component.error()).toContain('No se pudo copiar el enlace del panel');

    vi.advanceTimersByTime(3000);
    expect(component.error()).toBe('');
  });
});
