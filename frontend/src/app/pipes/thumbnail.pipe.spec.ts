import { ThumbnailPipe } from './thumbnail.pipe';

describe('ThumbnailPipe', () => {
  const pipe = new ThumbnailPipe();

  it('returns empty string for null/undefined/empty', () => {
    expect(pipe.transform(null)).toBe('');
    expect(pipe.transform(undefined)).toBe('');
    expect(pipe.transform('')).toBe('');
  });

  it('proxies via wsrv.nl with webp output', () => {
    const url = 'https://res.cloudinary.com/demo/image/upload/sample.png';
    const out = pipe.transform(url, 150);
    expect(out).toContain('https://wsrv.nl/?url=');
    expect(out).toContain(encodeURIComponent(url));
    expect(out).toContain('output=webp');
    expect(out).toContain('w=150');
  });

  it('lowers quality for smaller widths', () => {
    const url = 'https://example.com/x.png';
    expect(pipe.transform(url, 80)).toContain('q=55');
    expect(pipe.transform(url, 150)).toContain('q=60');
    expect(pipe.transform(url, 350)).toContain('q=70');
  });

  it('normalizes relative media URL to backend origin before proxy', () => {
    const out = pipe.transform('/media/extra_cards/card.png', 150);
    expect(out).toContain(encodeURIComponent('http://localhost:8000/media/extra_cards/card.png'));
  });
});
