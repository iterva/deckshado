import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';

import { DeckBuilderComponent } from './deck-builder.component';
import { CardService } from '../../services/card.service';
import { DeckService } from '../../services/deck.service';
import { AuthService } from '../../services/auth.service';
import { Card, BanlistEntry, Edition } from '../../models';

/**
 * Cobertura de la lógica de reglas de negocio del constructor de mazos MyL
 * (normalización de nombres, límite de copias, banlist, formato/edición,
 * restricción racial, oro inicial). Antes de esta suite, `deck-builder.
 * component.ts` (2300+ líneas, casi toda la lógica de reglas del juego)
 * tenía 0% de cobertura de tests. Ver docs/PLAN_DE_TESTING.md sección 3.1.
 *
 * No se llama a `fixture.detectChanges()` a propósito: eso dispararía
 * `ngOnInit` (setTimeout + chequeo de auth + llamadas HTTP reales vía
 * CardService/DeckService). Estos tests solo ejercitan métodos públicos de
 * lógica pura sobre el estado del componente, construido a mano.
 */

function makeCard(overrides: Partial<Card> = {}): Card {
  return {
    id: 1,
    myl_id: 'x1',
    edid: '001',
    slug: 'carta',
    name: 'Carta',
    edition_slug: 'ed-1',
    edition_title: 'Edición 1',
    rarity_name: null,
    race_name: null,
    race_slug: null,
    type_name: 'Aliado',
    cost: '1',
    damage: '1',
    ability: null,
    flavour: null,
    is_unique: false,
    image_url: '',
    ...overrides,
  };
}

function makeEdition(overrides: Partial<Edition> = {}): Edition {
  return {
    id: 1,
    myl_id: 'e1',
    slug: 'ed-1',
    title: 'Edición 1',
    image: null,
    date_release: null,
    date_empire_valid: null,
    format_code: 'imp',
    format_name: 'Imperio',
    active: true,
    ...overrides,
  };
}

function makeBan(overrides: Partial<BanlistEntry> = {}): BanlistEntry {
  return {
    id: 1,
    card_name: 'Carta',
    card_id: null,
    card_image_url: null,
    format_code: 'imp',
    sub_format: 'racial',
    status: 'banned',
    max_copies: 0,
    last_synced: '',
    ...overrides,
  };
}

describe('DeckBuilderComponent — reglas de negocio', () => {
  let component: DeckBuilderComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        { provide: CardService, useValue: {} },
        { provide: DeckService, useValue: {} },
        { provide: AuthService, useValue: { isAuthenticated: () => true, user: () => null } },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({}), queryParamMap: convertToParamMap({}) } },
        },
        { provide: Router, useValue: { navigate: () => Promise.resolve(true) } },
      ],
    });
    component = TestBed.createComponent(DeckBuilderComponent).componentInstance;
  });

  // ── getMaxCopies / getEffectiveMaxCopies ──────────────────────────────

  describe('getMaxCopies', () => {
    it('permite 3 copias por defecto', () => {
      expect(component.getMaxCopies(makeCard())).toBe(3);
    });

    it('limita a 1 copia si la carta es Única', () => {
      expect(component.getMaxCopies(makeCard({ is_unique: true }))).toBe(1);
    });

    it('usa max_copies de la banlist cuando existe, aunque la carta sea Única', () => {
      const card = makeCard({ id: 42, is_unique: true });
      component.banlistByCardId.set(42, makeBan({ status: 'limited_2', max_copies: 2 }));
      expect(component.getMaxCopies(card)).toBe(2);
    });

    it('una carta prohibida (banned) tiene máximo 0', () => {
      const card = makeCard({ id: 7 });
      component.banlistByCardId.set(7, makeBan({ status: 'banned', max_copies: 0 }));
      expect(component.getMaxCopies(card)).toBe(0);
    });
  });

  describe('getEffectiveMaxCopies', () => {
    it('toma el mínimo entre versiones del mismo nombre normalizado (acentos/mayúsculas/paréntesis)', () => {
      const promo = makeCard({ id: 1, name: 'Cthulhu (v2)', is_unique: true }); // max 1
      const normal = makeCard({ id: 2, name: 'CTHULHU', is_unique: false }); // max 3 por sí sola
      component.deckCards = [{ card: promo, quantity: 1 }];

      expect(component.getEffectiveMaxCopies(normal)).toBe(1);
    });

    it('no se ve afectada por copias de sí misma (mismo id)', () => {
      const card = makeCard({ id: 5, name: 'Dragón Dorado' });
      component.deckCards = [{ card, quantity: 2 }];
      expect(component.getEffectiveMaxCopies(card)).toBe(3);
    });

    it('considera versiones tanto en main como en side', () => {
      const uniqueVersion = makeCard({ id: 1, name: 'Samurái del Norte', is_unique: true });
      const otherVersion = makeCard({ id: 2, name: 'samurai del norte' });
      component.sideCards = [{ card: uniqueVersion, quantity: 1 }];

      expect(component.getEffectiveMaxCopies(otherVersion)).toBe(1);
    });
  });

  describe('getNameCount', () => {
    it('suma copias de main + side agrupando por nombre normalizado', () => {
      const a = makeCard({ id: 1, name: 'Dragón-Rojo' });
      const b = makeCard({ id: 2, name: 'dragon rojo' });
      component.deckCards = [{ card: a, quantity: 2 }];
      component.sideCards = [{ card: b, quantity: 1 }];

      expect(component.getNameCount('Dragón Rojo')).toBe(3);
    });

    it('devuelve 0 si el nombre no está en el mazo', () => {
      expect(component.getNameCount('Nadie')).toBe(0);
    });
  });

  // ── isCardAllowedByFormat ──────────────────────────────────────────────

  describe('isCardAllowedByFormat', () => {
    it('permite cualquier carta sin edition_slug', () => {
      component.selectedFormat = 'imp';
      expect(component.isCardAllowedByFormat(makeCard({ edition_slug: '' }))).toBe(true);
    });

    it('formato esc: solo permite ediciones en la whitelist', () => {
      component.selectedFormat = 'esc';
      expect(component.isCardAllowedByFormat(makeCard({ edition_slug: 'bushido' }))).toBe(true);
      expect(component.isCardAllowedByFormat(makeCard({ edition_slug: 'ed-cualquiera' }))).toBe(false);
    });

    it('formato pb/pe: restringe al scope de ediciones del grupo seleccionado', () => {
      component.selectedFormat = 'pb';
      (component as any).pbEditionScope = ['espada-sagrada', 'espada_sagrada_aniversario'];
      expect(component.isCardAllowedByFormat(makeCard({ edition_slug: 'espada-sagrada' }))).toBe(true);
      expect(component.isCardAllowedByFormat(makeCard({ edition_slug: 'helenica' }))).toBe(false);
    });

    it('formato normal: compara format_code de la edición contra el formato del mazo', () => {
      component.selectedFormat = 'imp';
      component.allEditions = [makeEdition({ slug: 'ed-1', format_code: 'imp' }), makeEdition({ slug: 'ed-2', format_code: 'fx' })];
      expect(component.isCardAllowedByFormat(makeCard({ edition_slug: 'ed-1' }))).toBe(true);
      expect(component.isCardAllowedByFormat(makeCard({ edition_slug: 'ed-2' }))).toBe(false);
    });

    it('si la edición no se encuentra en allEditions, permite la carta (fail-open)', () => {
      component.selectedFormat = 'imp';
      component.allEditions = [];
      expect(component.isCardAllowedByFormat(makeCard({ edition_slug: 'ed-desconocida' }))).toBe(true);
    });
  });

  describe('formatViolations', () => {
    it('reporta cartas fuera de formato en main y side con su sección correcta', () => {
      component.selectedFormat = 'esc';
      const legal = makeCard({ id: 1, edition_slug: 'bushido' });
      const illegalMain = makeCard({ id: 2, edition_slug: 'otra', edition_title: 'Otra Ed' });
      const illegalSide = makeCard({ id: 3, edition_slug: 'otra2', edition_title: 'Otra Ed 2' });
      component.deckCards = [{ card: legal, quantity: 1 }, { card: illegalMain, quantity: 1 }];
      component.sideCards = [{ card: illegalSide, quantity: 1 }];

      const violations = component.formatViolations;

      expect(violations.length).toBe(2);
      expect(violations.find(v => v.card.id === 2)?.section).toBe('main');
      expect(violations.find(v => v.card.id === 3)?.section).toBe('side');
    });
  });

  // ── addCard / addToSide: límites duros ─────────────────────────────────

  describe('addCard', () => {
    it('agrega una copia nueva de una carta', () => {
      const card = makeCard({ id: 1 });
      component.addCard(card);
      expect(component.getQuantityInDeck(1)).toBe(1);
    });

    it('no permite exceder getEffectiveMaxCopies (3 por defecto)', () => {
      const card = makeCard({ id: 1 });
      component.deckCards = [{ card, quantity: 3 }];
      component.addCard(card);
      expect(component.getQuantityInDeck(1)).toBe(3);
    });

    it('no permite exceder 1 copia si la carta es Única', () => {
      const card = makeCard({ id: 1, is_unique: true });
      component.addCard(card);
      component.addCard(card);
      expect(component.getQuantityInDeck(1)).toBe(1);
    });

    it('no permite exceder 50 cartas en el mazo principal', () => {
      component.deckCards = Array.from({ length: 25 }, (_, i) => ({
        card: makeCard({ id: i + 100, name: `Carta ${i}` }),
        quantity: 2,
      }));
      expect(component.totalDeckCards).toBe(50);

      const newCard = makeCard({ id: 999, name: 'Carta Nueva' });
      component.addCard(newCard);

      expect(component.getQuantityInDeck(999)).toBe(0);
    });

    it('no agrega una carta prohibida (banlist banned)', () => {
      const card = makeCard({ id: 1 });
      component.banlistByCardId.set(1, makeBan({ status: 'banned', max_copies: 0 }));
      component.addCard(card);
      expect(component.getQuantityInDeck(1)).toBe(0);
    });

    it('no agrega una carta fuera de formato', () => {
      component.selectedFormat = 'esc';
      const card = makeCard({ id: 1, edition_slug: 'no-esc' });
      component.addCard(card);
      expect(component.getQuantityInDeck(1)).toBe(0);
    });
  });

  describe('addToSide', () => {
    it('no permite exceder 15 cartas en el sidedeck', () => {
      component.sideCards = Array.from({ length: 7 }, (_, i) => ({
        card: makeCard({ id: i + 200, name: `Side ${i}` }),
        quantity: 2,
      }));
      // 14 cartas, queda espacio para 1 más
      component.sideCards.push({ card: makeCard({ id: 300, name: 'Side extra' }), quantity: 1 });
      expect(component.totalSideCards).toBe(15);

      const newCard = makeCard({ id: 999, name: 'Nueva' });
      component.addToSide(newCard);

      expect(component.getQuantityInSide(999)).toBe(0);
    });
  });

  // ── Restricción racial ─────────────────────────────────────────────────

  describe('isCardAllowedByRace', () => {
    it('sin raza seleccionada, todo está permitido', () => {
      component.selectedRace = '';
      expect(component.isCardAllowedByRace(makeCard({ race_slug: 'dragon' }))).toBe(true);
    });

    it('las cartas que no son Aliado siempre están permitidas', () => {
      component.selectedRace = 'dragon';
      expect(component.isCardAllowedByRace(makeCard({ type_name: 'Arma', race_slug: 'otra-raza' }))).toBe(true);
    });

    it('raza Dream: cualquier aliado sin restricción', () => {
      component.selectedRace = 'dream';
      expect(component.isCardAllowedByRace(makeCard({ type_name: 'Aliado', race_slug: 'oni' }))).toBe(true);
    });

    it('raza Tótem: solo aliados sin raza', () => {
      component.selectedRace = 'totem';
      expect(component.isCardAllowedByRace(makeCard({ type_name: 'Aliado', race_slug: '' }))).toBe(true);
      expect(component.isCardAllowedByRace(makeCard({ type_name: 'Aliado', race_slug: 'dragon' }))).toBe(false);
    });

    it('raza específica: permite aliados de esa raza', () => {
      component.selectedRace = 'dragon';
      expect(component.isCardAllowedByRace(makeCard({ type_name: 'Aliado', race_slug: 'dragon' }))).toBe(true);
      expect(component.isCardAllowedByRace(makeCard({ type_name: 'Aliado', race_slug: 'oni' }))).toBe(false);
    });

    it('arquetipo multi-raza (culto-tenebris = sombra + oni)', () => {
      component.selectedRace = 'culto-tenebris';
      expect(component.isCardAllowedByRace(makeCard({ type_name: 'Aliado', race_slug: 'sombra' }))).toBe(true);
      expect(component.isCardAllowedByRace(makeCard({ type_name: 'Aliado', race_slug: 'oni' }))).toBe(true);
      expect(component.isCardAllowedByRace(makeCard({ type_name: 'Aliado', race_slug: 'dragon' }))).toBe(false);
    });

    it('raza por habilidad: Oscuridad detecta la palabra clave al inicio de la primera línea', () => {
      component.selectedRace = 'oscuridad';
      expect(component.isCardAllowedByRace(makeCard({
        type_name: 'Aliado', race_slug: '', ability: 'Oscuridad: hace algo.\nSegunda línea.',
      }))).toBe(true);
      // race_slug no vacío ⇒ no es "sin raza", así que si el texto de habilidad
      // no matchea la keyword, queda excluida (no cae en la cuota de sin-raza).
      expect(component.isCardAllowedByRace(makeCard({
        type_name: 'Aliado', race_slug: 'humano', ability: 'Luz: hace otra cosa.',
      }))).toBe(false);
    });

    it('un aliado "sin raza" (sin keyword de habilidad que matchee) cuenta en la cuota de 4, no queda excluido de plano', () => {
      component.selectedRace = 'oscuridad';
      const card = makeCard({ type_name: 'Aliado', race_slug: '', ability: 'Luz: hace otra cosa.' });
      // Permitido porque cuenta como "aliado sin raza" dentro del límite de 4 (racelessAllyLimit).
      expect(component.isCardAllowedByRace(card)).toBe(true);
    });

    it('permite hasta 4 aliados sin raza en un mazo racial, bloquea el 5to', () => {
      component.selectedRace = 'dragon';
      component.deckCards = Array.from({ length: 4 }, (_, i) => ({
        card: makeCard({ id: i + 1, type_name: 'Aliado', race_slug: '' }),
        quantity: 1,
      }));
      const fifthRaceless = makeCard({ id: 999, type_name: 'Aliado', race_slug: '' });
      expect(component.isCardAllowedByRace(fifthRaceless)).toBe(false);
    });

    it('addCard respeta el límite racial de 4 aliados sin raza', () => {
      component.selectedRace = 'dragon';
      component.deckCards = Array.from({ length: 4 }, (_, i) => ({
        card: makeCard({ id: i + 1, name: `Raceless ${i}`, type_name: 'Aliado', race_slug: '' }),
        quantity: 1,
      }));
      const fifthRaceless = makeCard({ id: 999, name: 'Raceless 5', type_name: 'Aliado', race_slug: '' });
      component.addCard(fifthRaceless);
      expect(component.getQuantityInDeck(999)).toBe(0);
    });
  });

  // ── Oro inicial ─────────────────────────────────────────────────────────

  describe('isEligibleStartingGold', () => {
    it('solo cartas tipo Oro con "oro inicial" en la habilidad son elegibles', () => {
      expect(component.isEligibleStartingGold(makeCard({ type_name: 'Oro', ability: 'Es Oro inicial.' }))).toBe(true);
      expect(component.isEligibleStartingGold(makeCard({ type_name: 'Oro', ability: 'Otro efecto.' }))).toBe(false);
      expect(component.isEligibleStartingGold(makeCard({ type_name: 'Aliado', ability: 'Oro inicial.' }))).toBe(false);
    });

    it('la detección es insensible a acentos y mayúsculas', () => {
      expect(component.isEligibleStartingGold(makeCard({ type_name: 'Oro', ability: 'ÓRO INICIÁL de prueba' }))).toBe(true);
    });
  });

  describe('setStartingGold / removeCard', () => {
    it('quitar la última copia de la carta de oro inicial limpia startingGoldId', () => {
      const gold = makeCard({ id: 1, type_name: 'Oro', ability: 'Oro inicial.' });
      component.deckCards = [{ card: gold, quantity: 1 }];
      component.setStartingGold(1);
      expect(component.startingGoldId).toBe(1);

      component.removeCard(1);
      expect(component.startingGoldId).toBeNull();
    });

    it('no asigna oro inicial a una carta no elegible', () => {
      const notGold = makeCard({ id: 1, type_name: 'Aliado' });
      component.deckCards = [{ card: notGold, quantity: 1 }];
      component.setStartingGold(1);
      expect(component.startingGoldId).toBeNull();
    });
  });
});
