import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundBanlistEntry } from '../../../models/riftbound';

@Component({
  selector: 'app-riftbound-banlist',
  standalone: true,
  imports: [CommonModule],
  template: `
    <header class="rb-page-head">
      <h1>Banlist Riftbound — Standard</h1>
      <p class="muted">Cartas prohibidas y limitadas en formato Standard.</p>
    </header>

    @if (loading()) { <p>Cargando…</p> }

    <table class="rb-banlist">
      <thead>
        <tr>
          <th>Carta</th>
          <th>Número</th>
          <th>Estado</th>
          <th>Copias máx.</th>
        </tr>
      </thead>
      <tbody>
        @for (e of entries(); track e.id) {
          <tr [class]="'status-' + e.status">
            <td>{{ e.card_name }}</td>
            <td><code>{{ e.card_number }}</code></td>
            <td>{{ statusLabel(e.status) }}</td>
            <td>{{ e.max_copies }}</td>
          </tr>
        }
        @if (!loading() && entries().length === 0) {
          <tr><td colspan="4" class="muted center">Banlist vacía actualmente.</td></tr>
        }
      </tbody>
    </table>
  `,
  styles: [`
    .muted { opacity: .65; }
    .center { text-align: center; }
    .rb-banlist { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    .rb-banlist th, .rb-banlist td { padding: .5rem .75rem; border-bottom: 1px solid var(--border-color, #333); text-align: left; }
    .status-banned { color: #ff6b6b; }
    .status-limited_1 { color: #f0a830; }
    .status-limited_2 { color: #f0d030; }
  `],
})
export class RiftboundBanlistComponent implements OnInit {
  private rb = inject(RiftboundService);
  entries = signal<RiftboundBanlistEntry[]>([]);
  loading = signal(true);

  ngOnInit() {
    this.rb.listBanlist('standard').subscribe({
      next: (r) => { this.entries.set(r.results); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  statusLabel(s: string) {
    return s === 'banned' ? 'Prohibida' : s === 'limited_1' ? 'Limitada a 1' : 'Limitada a 2';
  }
}
