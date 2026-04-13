import { Component, ChangeDetectorRef } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { UpperCasePipe } from '@angular/common';
import { CardService } from '../../services/card.service';
import { AuthService } from '../../services/auth.service';
import { Format } from '../../models';

interface RaceOption {
  slug: string;
  name: string;
  description: string;
}

@Component({
  selector: 'app-format-select',
  standalone: true,
  imports: [RouterLink, UpperCasePipe],
  templateUrl: './format-select.component.html',
  styleUrl: './format-select.component.scss',
})
export class FormatSelectComponent {
  formats: Format[] = [];
  loading = true;
  step: 'format' | 'race' = 'format';
  selectedFormat = '';
  selectedFormatName = '';

  readonly enabledFormats = ['imp', 'imp_r', 'esc'];

  readonly races: RaceOption[] = [
    { slug: 'dream', name: 'Dream', description: 'Todas las razas, talismanes, armas y tótems' },
    { slug: 'totem', name: 'Tótem', description: 'Aliados sin raza + tótems, talismanes y armas' },
    { slug: 'eterno', name: 'Eterno', description: 'Aliados Eterno + neutrales' },
    { slug: 'faerie', name: 'Faerie', description: 'Aliados Faerie + neutrales' },
    { slug: 'dragon', name: 'Dragón', description: 'Aliados Dragón + neutrales' },
    { slug: 'sombra', name: 'Sombra', description: 'Aliados Sombra + neutrales' },
    { slug: 'heroe', name: 'Héroe', description: 'Aliados Héroe + neutrales' },
    { slug: 'sacerdote', name: 'Sacerdote', description: 'Aliados Sacerdote + neutrales' },
    { slug: 'guerrero', name: 'Guerrero', description: 'Aliados Guerrero + neutrales' },
    { slug: 'bestia', name: 'Bestia', description: 'Aliados Bestia + neutrales' },
    { slug: 'caballero', name: 'Caballero', description: 'Aliados Caballero + neutrales' },
  ];

  constructor(
    private cardService: CardService,
    private auth: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {
    // Check authentication after a short delay to allow user loading
    setTimeout(() => {
      if (!this.auth.isAuthenticated()) {
        this.router.navigate(['/login']);
        return;
      }
      this.cardService.getFormats().subscribe(d => {
        const order = ['imp', 'esc', 'imp_r'];
        this.formats = d.sort((a, b) => {
          const ai = order.indexOf(a.code);
          const bi = order.indexOf(b.code);
          const aIdx = ai >= 0 ? ai : order.length;
          const bIdx = bi >= 0 ? bi : order.length;
          return aIdx - bIdx;
        });
        this.loading = false;
        this.cdr.detectChanges();
      });
    }, 100);
  }

  isEnabled(code: string): boolean {
    return this.enabledFormats.includes(code);
  }

  selectFormat(code: string) {
    if (!this.isEnabled(code)) return;
    this.selectedFormat = code;
    this.selectedFormatName = this.formats.find(f => f.code === code)?.name || code;
    this.step = 'race';
  }

  selectRace(slug: string) {
    this.router.navigate(['/builder/new', this.selectedFormat], { queryParams: { race: slug } });
  }

  backToFormats() {
    this.step = 'format';
  }
}
