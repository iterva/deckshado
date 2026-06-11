import { ThumbnailPipe } from './thumbnail.pipe';

describe('ThumbnailPipe', () => {
  const pipe = new ThumbnailPipe();

  it('returns empty string for null/undefined/empty', () => {
    expect(pipe.transform(null)).toBe('');
    expect(pipe.transform(undefined)).toBe('');
    expect(pipe.transform('')).toBe('');
  });

  it('keeps direct URL for non-cloudinary hosts', () => {
    const url = 'https://example.com/assets/card.png';
    const out = pipe.transform(url, 150);
    expect(out).toBe(url);
  });

  it('optimizes cloudinary URLs with native transformations', () => {
    const url = 'https://res.cloudinary.com/demo/image/upload/sample.png';
    const out = pipe.transform(url, 150);
    expect(out).toContain('https://res.cloudinary.com/demo/image/upload/');
    expect(out).toContain('f_auto');
    expect(out).toContain('q_auto:good');
    expect(out).toContain('w_150');
    expect(out).toContain('/sample.png');
  });

  it('keeps already transformed cloudinary URLs unchanged', () => {
    const url = 'https://res.cloudinary.com/demo/image/upload/f_auto,q_auto,w_150/sample.png';
    expect(pipe.transform(url, 350)).toBe(url);
  });

  it('normalizes relative media URL to backend origin', () => {
    const out = pipe.transform('/media/extra_cards/card.png', 150);
    expect(out).toBe('http://localhost:8000/media/extra_cards/card.png');
  });

  it('rewrites production media origin to local backend in dev mode', () => {
    const out = pipe.transform('https://iterva.pythonanywhere.com/media/extra_cards/card.png', 150);
    expect(out).toBe('http://localhost:8000/media/extra_cards/card.png');
  });
});
