import { ThumbnailPipe } from './thumbnail.pipe';

describe('ThumbnailPipe', () => {
  const pipe = new ThumbnailPipe();

  it('returns empty string for null/undefined/empty', () => {
    expect(pipe.transform(null)).toBe('');
    expect(pipe.transform(undefined)).toBe('');
    expect(pipe.transform('')).toBe('');
  });

  it('keeps direct URL for regular hosts', () => {
    const url = 'https://example.com/assets/card.png';
    expect(pipe.transform(url, 150)).toBe(url);
  });

  it('normalizes protocol-relative URL', () => {
    expect(pipe.transform('//cdn.example.com/card.png', 150)).toBe('https://cdn.example.com/card.png');
  });

  it('normalizes relative media URL to backend origin', () => {
    expect(pipe.transform('/media/extra_cards/card.png', 150)).toBe('http://localhost:8000/media/extra_cards/card.png');
  });

  it('rewrites production media origin to local backend in dev mode', () => {
    const src = 'https://iterva.pythonanywhere.com/media/extra_cards/card.png';
    expect(pipe.transform(src, 150)).toBe('http://localhost:8000/media/extra_cards/card.png');
  });

  it('ignores width argument but keeps API compatibility', () => {
    const url = 'https://res.cloudinary.com/demo/image/upload/sample.png';
    expect(pipe.transform(url, 80)).toBe(url);
    expect(pipe.transform(url, 350)).toBe(url);
  });
});
