import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';

import { RiftboundBuilderComponent } from './riftbound-builder.component';
import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundCardLite, RiftboundZone } from '../../../models/riftbound';

/**
 * Cobertura de la lógica de reglas de Riftbound en el frontend
 * (`riftbound-builder.component.ts`, ~2400 líneas, 0% de cobertura previa).
 * Complementa a `backend/riftbound/tests_validation.py`, que cubre el mismo
 * conjunto de reglas pero server-side. Ver docs/PLAN_DE_TESTING.md sección 3.1.
 *
 * No se llama a `fixture.detectChanges()`: evita disparar `ngOnInit` (carga
 * de mazo/sets/banlist/legends vía HTTP real). Se manipula el signal
 * `entries` directamente y se llaman métodos públicos.
 */

function makeCard(overrides: Partial<RiftboundCardLite> = {}): RiftboundCardLite {
  return {
    id: 1,
    card_number: 'OGN-001',
    name: 'Carta',
    card_type: 'unit',
    rarity: 'common',
    colors: [],
    energy: 1,
    power: null,
    might: null,
    image: '',
    subtypes: [],
    ...overrides,
  };
}

type EntriesState = Record<RiftboundZone, { card: RiftboundCardLite; quantity: number; zone: RiftboundZone }[]>;

function emptyEntries(): EntriesState {
  return { main: [], side: [], rune: [], champion: [], bg: [] };
}

describe('RiftboundBuilderComponent — reglas de negocio', () => {
  let component: RiftboundBuilderComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        { provide: RiftboundService, useValue: {} },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({}), queryParamMap: convertToParamMap({}) } },
        },
        { provide: Router, useValue: { navigate: () => Promise.resolve(true) } },
      ],
    });
    component = TestBed.createComponent(RiftboundBuilderComponent).componentInstance;
  });

  // ── getMaxCopies ─────────────────────────────────────────────────────

  describe('getMaxCopies', () => {
    it('por defecto permite 3 copias', () => {
      expect(component.getMaxCopies(makeCard())).toBe(3);
    });

    it('battlefield y legend están limitados a 1 copia', () => {
      expect(component.getMaxCopies(makeCard({ card_type: 'battlefield' }))).toBe(1);
      expect(component.getMaxCopies(makeCard({ card_type: 'legend' }))).toBe(1);
    });

    it('rune usa el límite de la zona de runas (12)', () => {
      expect(component.getMaxCopies(makeCard({ card_type: 'rune' }))).toBe(component.rules.rune);
    });

    it('override hardcodeado: Spiderling permite hasta 50 (limitado en la práctica por el tamaño de la zona main)', () => {
      expect(component.getMaxCopies(makeCard({ name: 'Spiderling', card_type: 'unit' }))).toBe(50);
    });

    it('banlist banned: 0 copias, sin importar el tipo de carta', () => {
      const card = makeCard({ card_number: 'OGN-100' });
      component.banlist.set(new Map([['OGN-100', { status: 'banned', max_copies: 0 }]]));
      expect(component.getMaxCopies(card)).toBe(0);
    });

    it('banlist limited: usa max_copies de la entrada', () => {
      const card = makeCard({ card_number: 'OGN-200' });
      component.banlist.set(new Map([['OGN-200', { status: 'limited', max_copies: 1 }]]));
      expect(component.getMaxCopies(card)).toBe(1);
    });

    it('la banlist tiene prioridad sobre el override de Spiderling', () => {
      const card = makeCard({ name: 'Spiderling', card_number: 'OGN-300' });
      component.banlist.set(new Map([['OGN-300', { status: 'banned', max_copies: 0 }]]));
      expect(component.getMaxCopies(card)).toBe(0);
    });
  });

  // ── canAddToAuto / addToZone ─────────────────────────────────────────

  describe('canAddToAuto', () => {
    it('bloquea la zona de runas al llegar a 12', () => {
      const runeCard = makeCard({ id: 1, card_type: 'rune' });
      const state = emptyEntries();
      state.rune = [{ card: runeCard, quantity: 12, zone: 'rune' }];
      component.entries.set(state);
      expect(component.canAddToAuto(runeCard, 'rune')).toBe(false);
    });

    it('bloquea la zona de champion al llegar a 1', () => {
      const legend = makeCard({ id: 1, card_type: 'legend' });
      const state = emptyEntries();
      state.champion = [{ card: legend, quantity: 1, zone: 'champion' }];
      component.entries.set(state);
      const otherLegend = makeCard({ id: 2, card_type: 'legend' });
      expect(component.canAddToAuto(otherLegend, 'champion')).toBe(false);
    });

    it('bloquea battlefields duplicados aunque la zona no esté llena', () => {
      const bg1 = makeCard({ id: 1, card_type: 'battlefield' });
      const state = emptyEntries();
      state.bg = [{ card: bg1, quantity: 1, zone: 'bg' }];
      component.entries.set(state);
      expect(component.canAddToAuto(bg1, 'bg')).toBe(false);
    });

    it('permite un battlefield distinto mientras la zona no esté llena', () => {
      const bg1 = makeCard({ id: 1, name: 'Battlefield Uno', card_type: 'battlefield' });
      const bg2 = makeCard({ id: 2, name: 'Battlefield Dos', card_type: 'battlefield' });
      const state = emptyEntries();
      state.bg = [{ card: bg1, quantity: 1, zone: 'bg' }];
      component.entries.set(state);
      expect(component.canAddToAuto(bg2, 'bg')).toBe(true);
    });

    it('respeta el límite de copias por nombre en zonas normales', () => {
      const card = makeCard({ id: 1, name: 'Unidad X' });
      const state = emptyEntries();
      state.main = [{ card, quantity: 3, zone: 'main' }];
      component.entries.set(state);
      expect(component.canAddToAuto(card, 'main')).toBe(false);
    });
  });

  describe('addToZone', () => {
    it('respeta el tope de 40 cartas en main', () => {
      const state = emptyEntries();
      state.main = Array.from({ length: 20 }, (_, i) => ({
        card: makeCard({ id: i + 1, name: `Carta ${i}` }),
        quantity: 2,
        zone: 'main' as RiftboundZone,
      }));
      component.entries.set(state);
      expect(component.zoneCount('main')).toBe(40);

      const newCard = makeCard({ id: 999, name: 'Nueva' });
      component.addToZone(newCard, 'main');

      expect(component.zoneCount('main')).toBe(40);
      expect(component.getQuantityInZone(999, 'main')).toBe(0);
    });

    it('respeta el tope de 10 cartas en el sideboard', () => {
      const state = emptyEntries();
      state.side = Array.from({ length: 10 }, (_, i) => ({
        card: makeCard({ id: i + 1, name: `Carta ${i}` }),
        quantity: 1,
        zone: 'side' as RiftboundZone,
      }));
      component.entries.set(state);

      const newCard = makeCard({ id: 999, name: 'Nueva' });
      component.addToZone(newCard, 'side');

      expect(component.getQuantityInZone(999, 'side')).toBe(0);
    });

    it('champion y battlefield fuerzan máximo 1 copia por carta sin importar getMaxCopies', () => {
      const legend = makeCard({ id: 1, card_type: 'legend' });
      component.addToZone(legend, 'champion');
      component.addToZone(legend, 'champion'); // segunda copia, debe ser ignorada

      expect(component.getQuantityInZone(1, 'champion')).toBe(1);
    });

    it('agrega copias hasta el máximo por defecto (3) y luego lo bloquea', () => {
      const card = makeCard({ id: 1, name: 'Unidad Y' });
      component.addToZone(card, 'main');
      component.addToZone(card, 'main');
      component.addToZone(card, 'main');
      component.addToZone(card, 'main'); // 4ta, debe bloquearse

      expect(component.getQuantityInZone(1, 'main')).toBe(3);
    });

    it('una carta banned (max_copies 0) no se puede agregar', () => {
      const card = makeCard({ id: 1, card_number: 'OGN-500' });
      component.banlist.set(new Map([['OGN-500', { status: 'banned', max_copies: 0 }]]));
      component.addToZone(card, 'main');
      expect(component.getQuantityInZone(1, 'main')).toBe(0);
    });
  });

  // ── Champion Unit: coincidencia con el Legend elegido ────────────────

  describe('championName / filteredChampionUnits (wizard de Champion Unit)', () => {
    it('deriva el tag del champion del legend elegido (chosenLegend)', () => {
      const legend = makeCard({ id: 1, card_type: 'legend', name: 'Annie, Dark Child', subtypes: ['Annie', 'Legend'] });
      const state = emptyEntries();
      state.champion = [{ card: legend, quantity: 1, zone: 'champion' }];
      component.entries.set(state);

      expect(component.championName()).toBe('Annie');
    });

    it('sin legend elegido, championName es null', () => {
      expect(component.championName()).toBeNull();
    });

    it('filtra champion units que comparten el tag del legend Y el tag "Champion Unit"', () => {
      const legend = makeCard({ id: 1, card_type: 'legend', name: 'Annie, Dark Child', subtypes: ['Annie', 'Legend'] });
      const validUnit = makeCard({ id: 2, name: 'Annie, Stubborn', subtypes: ['Annie', 'Champion Unit'] });
      const wrongTagUnit = makeCard({ id: 3, name: 'Otra unidad', subtypes: ['Annie'] }); // falta 'Champion Unit'
      const unrelatedUnit = makeCard({ id: 4, name: 'Cosa random', subtypes: ['Otro', 'Champion Unit'] });

      const state = emptyEntries();
      state.champion = [{ card: legend, quantity: 1, zone: 'champion' }];
      component.entries.set(state);
      component.championUnitOptions.set([validUnit, wrongTagUnit, unrelatedUnit]);

      const filtered = component.filteredChampionUnits();
      expect(filtered.map(u => u.id)).toEqual([2]);
    });

    it('usa el nombre como respaldo cuando la unidad no tiene los subtypes esperados (dato legacy)', () => {
      const legend = makeCard({ id: 1, card_type: 'legend', name: 'Akali, The Rogue Assassin', subtypes: ['Akali', 'Legend'] });
      const legacyUnit = makeCard({ id: 2, name: 'Akali - Fist of Shadow', subtypes: [] }); // sin subtypes, pero el nombre matchea

      const state = emptyEntries();
      state.champion = [{ card: legend, quantity: 1, zone: 'champion' }];
      component.entries.set(state);
      component.championUnitOptions.set([legacyUnit]);

      expect(component.filteredChampionUnits().map(u => u.id)).toEqual([2]);
    });

    it('el buscador del picker filtra adicionalmente por nombre o card_number', () => {
      const legend = makeCard({ id: 1, card_type: 'legend', name: 'Annie, Dark Child', subtypes: ['Annie', 'Legend'] });
      const unitA = makeCard({ id: 2, card_number: 'OGN-050', name: 'Annie, Stubborn', subtypes: ['Annie', 'Champion Unit'] });
      const unitB = makeCard({ id: 3, card_number: 'OGN-051', name: 'Annie, Fireball', subtypes: ['Annie', 'Champion Unit'] });

      const state = emptyEntries();
      state.champion = [{ card: legend, quantity: 1, zone: 'champion' }];
      component.entries.set(state);
      component.championUnitOptions.set([unitA, unitB]);
      component.championUnitPickerSearch.set('fireball');

      expect(component.filteredChampionUnits().map(u => u.id)).toEqual([3]);
    });
  });
});
