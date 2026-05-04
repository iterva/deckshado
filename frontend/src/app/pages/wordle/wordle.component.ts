import {
  Component,
  HostListener,
  OnDestroy,
  OnInit,
  signal,
  computed,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import {
  WordleLeaderboard,
  WordleService,
  WordleState,
  WordleWinner,
} from '../../services/wordle.service';

const KEYBOARD_ROWS: string[][] = [
  ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
  ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'Ñ'],
  ['ENTER', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', 'BACK'],
];

@Component({
  selector: 'app-wordle',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './wordle.component.html',
  styleUrl: './wordle.component.scss',
})
export class WordleComponent implements OnInit, OnDestroy {
  state = signal<WordleState | null>(null);
  current = signal<string>('');
  loading = signal(false);
  error = signal<string | null>(null);
  toast = signal<string | null>(null);
  rows = KEYBOARD_ROWS;

  leaderboard = signal<WordleLeaderboard | null>(null);
  winner = signal<WordleWinner | null>(null);

  // Visual rows: includes finalized guesses, current attempt and empty rows
  display = computed(() => {
    const s = this.state();
    if (!s) return [];
    const rows: { letter: string; status: 'correct' | 'present' | 'absent' | 'pending' | 'empty' }[][] = [];
    for (const g of s.guesses) {
      rows.push(
        g.letters.map((l, i) => ({
          letter: l.toUpperCase(),
          status: g.statuses[i],
        }))
      );
    }
    if (!s.finished) {
      const cur = this.current().toUpperCase();
      const row: any[] = [];
      for (let i = 0; i < s.length; i++) {
        if (i < cur.length) row.push({ letter: cur[i], status: 'pending' });
        else row.push({ letter: '', status: 'empty' });
      }
      rows.push(row);
      while (rows.length < s.max_attempts) {
        const empty: any[] = [];
        for (let i = 0; i < s.length; i++) empty.push({ letter: '', status: 'empty' });
        rows.push(empty);
      }
    } else {
      while (rows.length < s.max_attempts) {
        const empty: any[] = [];
        for (let i = 0; i < s.length; i++) empty.push({ letter: '', status: 'empty' });
        rows.push(empty);
      }
    }
    return rows;
  });

  // Tracks letter status for keyboard coloring
  keyStatus = computed<Record<string, 'correct' | 'present' | 'absent'>>(() => {
    const s = this.state();
    const map: Record<string, 'correct' | 'present' | 'absent'> = {};
    if (!s) return map;
    const order = { absent: 0, present: 1, correct: 2 } as const;
    for (const g of s.guesses) {
      g.letters.forEach((l, i) => {
        const k = l.toUpperCase();
        const cur = map[k];
        const next = g.statuses[i];
        if (!cur || order[next] > order[cur]) map[k] = next;
      });
    }
    return map;
  });

  constructor(
    public auth: AuthService,
    private wordle: WordleService,
    private router: Router
  ) {}

  ngOnInit() {
    this.load();
    this.loadLeaderboard();
    this.loadWinner();
  }

  ngOnDestroy() {}

  private load() {
    this.loading.set(true);
    this.wordle.today().subscribe({
      next: (s) => {
        this.state.set(s);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar la palabra del día.');
        this.loading.set(false);
      },
    });
  }

  private loadLeaderboard() {
    this.wordle.leaderboard().subscribe({
      next: (l) => this.leaderboard.set(l),
      error: () => {},
    });
  }

  private loadWinner() {
    this.wordle.previousWinner().subscribe({
      next: (w) => this.winner.set(w),
      error: () => {},
    });
  }

  @HostListener('window:keydown', ['$event'])
  onKey(event: KeyboardEvent) {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const k = event.key;
    if (k === 'Enter') {
      event.preventDefault();
      this.submit();
      return;
    }
    if (k === 'Backspace') {
      event.preventDefault();
      this.backspace();
      return;
    }
    if (/^[a-zA-ZñÑáéíóúÁÉÍÓÚ]$/.test(k)) {
      this.press(k.toUpperCase());
    }
  }

  press(key: string) {
    if (key === 'ENTER') return this.submit();
    if (key === 'BACK') return this.backspace();
    const s = this.state();
    if (!s || s.finished) return;
    if (this.current().length >= s.length) return;
    this.current.set(this.current() + key);
  }

  backspace() {
    this.current.set(this.current().slice(0, -1));
  }

  submit() {
    const s = this.state();
    if (!s || s.finished) return;
    if (!this.auth.isAuthenticated()) {
      this.toast.set('Debes iniciar sesión para jugar.');
      setTimeout(() => this.toast.set(null), 2500);
      return;
    }
    const guess = this.current();
    if (guess.length !== s.length) {
      this.toast.set(`La palabra debe tener ${s.length} letras.`);
      setTimeout(() => this.toast.set(null), 2000);
      return;
    }
    this.loading.set(true);
    this.wordle.guess(guess).subscribe({
      next: (next) => {
        this.state.set(next);
        this.current.set('');
        this.loading.set(false);
        if (next.finished) {
          this.toast.set(next.won ? `¡Correcto! +${next.score} pts` : `Era: ${next.answer}`);
          setTimeout(() => this.toast.set(null), 4000);
          this.loadLeaderboard();
        }
      },
      error: (err) => {
        this.loading.set(false);
        const msg = err?.error?.detail ?? 'Error al enviar.';
        this.toast.set(msg);
        setTimeout(() => this.toast.set(null), 2500);
      },
    });
  }

  revealHint() {
    if (!this.auth.isAuthenticated()) {
      this.router.navigate(['/login']);
      return;
    }
    this.wordle.hint().subscribe({
      next: (h) => {
        const s = this.state();
        if (s) {
          this.state.set({ ...s, hint: h.hint, hint_revealed: true });
        }
      },
    });
  }

  monthName(m: number | undefined): string {
    if (!m) return '';
    const names = [
      'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
      'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
    ];
    return names[m - 1] ?? '';
  }
}
