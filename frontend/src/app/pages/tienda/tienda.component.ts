import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CarpetaService } from '../../services/carpeta.service';
import { ThumbnailPipe } from '../../pipes/thumbnail.pipe';
import { CollectionEntry, Card } from '../../models';

@Component({
  selector: 'app-tienda',
  standalone: true,
  imports: [FormsModule, ThumbnailPipe],
  templateUrl: './tienda.component.html',
  styleUrl: './tienda.component.scss',
})
export class TiendaComponent implements OnInit {
  token = '';
  storeOwner = '';
  storeAvatar: string | null = null;
  storeBinder: string | null = null;
  entries: CollectionEntry[] = [];
  total = 0;
  page = 1;
  search = '';
  loading = false;
  notFound = false;
  previewCard: Card | null = null;

  constructor(
    private route: ActivatedRoute,
    private carpetaService: CarpetaService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.token = this.route.snapshot.paramMap.get('token') || '';
    if (this.token) {
      this.loadStore();
    }
  }

  loadStore() {
    this.loading = true;
    this.carpetaService.getPublicStore(this.token, this.page, this.search || undefined).subscribe({
      next: res => {
        this.entries = res.results;
        this.total = res.count;
        this.storeOwner = res.store_owner;
        this.storeAvatar = res.store_avatar;
        this.storeBinder = res.store_binder_avatar;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.notFound = true;
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  onSearch() { this.page = 1; this.loadStore(); }
  prevPage() { if (this.page > 1) { this.page--; this.loadStore(); } }
  nextPage() { if (this.page * 40 < this.total) { this.page++; this.loadStore(); } }
  get totalPages() { return Math.ceil(this.total / 40); }

  exportPdf() {
    window.print();
  }

  copyLink() {
    navigator.clipboard.writeText(window.location.href);
  }
}
