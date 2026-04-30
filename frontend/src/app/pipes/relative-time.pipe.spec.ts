import { RelativeTimePipe } from './relative-time.pipe';

describe('RelativeTimePipe', () => {
  const pipe = new RelativeTimePipe();

  it('returns empty string for null/undefined/invalid', () => {
    expect(pipe.transform(null)).toBe('');
    expect(pipe.transform(undefined)).toBe('');
    expect(pipe.transform('not a date')).toBe('');
  });

  it('handles future dates as "recién"', () => {
    const future = new Date(Date.now() + 60_000);
    expect(pipe.transform(future)).toBe('recién');
  });

  it('formats seconds, minutes and hours', () => {
    expect(pipe.transform(new Date(Date.now() - 10_000))).toBe('hace unos segundos');
    expect(pipe.transform(new Date(Date.now() - 45_000))).toBe('hace 45 s');
    expect(pipe.transform(new Date(Date.now() - 5 * 60_000))).toBe('hace 5 min');
    expect(pipe.transform(new Date(Date.now() - 3 * 3600_000))).toBe('hace 3 h');
  });

  it('formats yesterday and days', () => {
    expect(pipe.transform(new Date(Date.now() - 24 * 3600_000))).toBe('ayer');
    expect(pipe.transform(new Date(Date.now() - 3 * 24 * 3600_000))).toBe('hace 3 días');
  });

  it('formats weeks, months and years', () => {
    expect(pipe.transform(new Date(Date.now() - 14 * 24 * 3600_000))).toBe('hace 2 sem');
    expect(pipe.transform(new Date(Date.now() - 60 * 24 * 3600_000))).toContain('mes');
    expect(pipe.transform(new Date(Date.now() - 800 * 24 * 3600_000))).toContain('año');
  });
});
