import { ThumbnailPipe } from './thumbnail.pipe';

describe('ThumbnailPipe', () => {
  const pipe = new ThumbnailPipe();

  it('returns empty string for null/undefined/empty', () => {
    expect(pipe.transform(null)).toBe('');
    expect(pipe.transform(undefined)).toBe('');
    expect(pipe.transform('')).toBe('');
  });

  it('applies cloudinary transforms for thumbnails', () => {
    const url = 'https://res.cloudinary.com/demo/image/upload/sample.png';
    const out = pipe.transform(url, 150);
    expect(out).toContain('https://res.cloudinary.com/demo/image/upload/');
    expect(out).toContain('f_auto,dpr_auto,c_limit,w_150,q_auto:good/');
    expect(out).toContain('sample.png');
  });

  it('uses eco quality for tiny cloudinary thumbs', () => {
    const url = 'https://res.cloudinary.com/demo/image/upload/sample.png';
    expect(pipe.transform(url, 80)).toContain('w_80,q_auto:eco');
  });

  it('keeps non-cloudinary URLs unchanged', () => {
    const url = 'https://example.com/x.png';
    expect(pipe.transform(url, 80)).toBe(url);
  });

  it('does not stack transforms when cloudinary URL is already transformed', () => {
    const url = 'https://res.cloudinary.com/demo/image/upload/f_auto,w_250,q_auto/sample.png';
    expect(pipe.transform(url, 150)).toBe(url);
  });
});
