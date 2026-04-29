import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CarpetaService } from '../../services/carpeta.service';
import { PublicBinderProfile } from '../../models';

@Component({
  selector: 'app-stores-index',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './stores-index.component.html',
  styleUrl: './stores-index.component.scss',
})
export class StoresIndexComponent implements OnInit {
  stores: PublicBinderProfile[] = [];
  total = 0;
  loading = false;
  page = 1;
  search = '';
  country = '';
  ordering = '-last_active';

  countries = [
    { code: '', name: 'Todos los países' },
    { code: 'CL', name: 'Chile' },
    { code: 'AR', name: 'Argentina' },
    { code: 'PE', name: 'Perú' },
    { code: 'MX', name: 'México' },
    { code: 'CO', name: 'Colombia' },
    { code: 'UY', name: 'Uruguay' },
    { code: 'EC', name: 'Ecuador' },
    { code: 'BO', name: 'Bolivia' },
    { code: 'VE', name: 'Venezuela' },
    { code: 'PY', name: 'Paraguay' },
    { code: 'ES', name: 'España' },
    { code: 'US', name: 'EE.UU.' },
    { code: 'OT', name: 'Otro' },
  ];

  constructor(private carpetaService: CarpetaService, private cdr: ChangeDetectorRef) {}

  ngOnInit() { this.load(); }

  load() {
    this.loading = true;
    this.carpetaService.getPublicStores({
      page: this.page,
      search: this.search || undefined,
      country: this.country || undefined,
      ordering: this.ordering,
    }).subscribe({
      next: res => {
        this.stores = res.results;
        this.total = res.count;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
  }

  apply() { this.page = 1; this.load(); }
  prev() { if (this.page > 1) { this.page--; this.load(); } }
  next() { if (this.page * 40 < this.total) { this.page++; this.load(); } }
  get totalPages() { return Math.ceil(this.total / 40); }
}
