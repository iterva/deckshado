import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { DeckService } from './deck.service';
import { environment } from '../../environments/environment';

describe('DeckService', () => {
  let svc: DeckService;
  let httpMock: HttpTestingController;
  const apiUrl = `${environment.apiUrl}/decks`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    svc = TestBed.inject(DeckService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('getPublicDecks builds query string with provided filters', () => {
    svc.getPublicDecks('warrior', 2, 'imp', 'samurai', 'popular').subscribe();
    const req = httpMock.expectOne(r =>
      r.url === `${apiUrl}/public/` &&
      r.params.get('search') === 'warrior' &&
      r.params.get('page') === '2' &&
      r.params.get('format') === 'imp' &&
      r.params.get('race') === 'samurai' &&
      r.params.get('ordering') === 'popular',
    );
    expect(req.request.method).toBe('GET');
    req.flush({ count: 0, results: [] });
  });

  it('getPublicDecks omits empty params', () => {
    svc.getPublicDecks().subscribe();
    const req = httpMock.expectOne(`${apiUrl}/public/`);
    expect(req.request.params.keys().length).toBe(0);
    req.flush({ count: 0, results: [] });
  });

  it('createDeck POSTs to /my/', () => {
    svc.createDeck({ name: 'New', is_public: false }).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/my/`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ name: 'New', is_public: false });
    req.flush({ id: 1, name: 'New' });
  });

  it('updateDeck PATCHes /my/:id/', () => {
    svc.updateDeck(7, { name: 'Renamed' }).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/my/7/`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ name: 'Renamed' });
    req.flush({ id: 7, name: 'Renamed' });
  });

  it('deleteDeck DELETEs /my/:id/', () => {
    svc.deleteDeck(3).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/my/3/`);
    expect(req.request.method).toBe('DELETE');
    req.flush(null);
  });

  it('addCardToDeck POSTs card_id and quantity', () => {
    svc.addCardToDeck(1, 42, 3).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/my/1/entries/`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ card_id: 42, quantity: 3 });
    req.flush({ id: 1, quantity: 3 });
  });

  it('removeCardFromDeck DELETE with body card_id', () => {
    svc.removeCardFromDeck(1, 42).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/my/1/entries/`);
    expect(req.request.method).toBe('DELETE');
    expect(req.request.body).toEqual({ card_id: 42 });
    req.flush(null);
  });

  it('toggleLike POSTs to /public/:id/like/', () => {
    let result: any;
    svc.toggleLike(5).subscribe(r => (result = r));
    const req = httpMock.expectOne(`${apiUrl}/public/5/like/`);
    expect(req.request.method).toBe('POST');
    req.flush({ liked: true, like_count: 1 });
    expect(result.liked).toBe(true);
    expect(result.like_count).toBe(1);
  });

  it('addComment POSTs text on /public/:id/comments/', () => {
    svc.addComment(9, 'hola').subscribe();
    const req = httpMock.expectOne(`${apiUrl}/public/9/comments/`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ text: 'hola' });
    req.flush({ id: 1, text: 'hola' });
  });

  it('importDeck POSTs payload to /import/', () => {
    const payload = { name: 'X', entries: [{ myl_id: 'a', quantity: 1 }] };
    svc.importDeck(payload).subscribe();
    const req = httpMock.expectOne(`${apiUrl}/import/`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(payload);
    req.flush({ id: 1, name: 'X', imported_entries: 1, missing_myl_ids: [] });
  });
});
