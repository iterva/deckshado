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

interface PbEditionOption {
  slug: string;            // identificador del grupo (param URL)
  name: string;            // nombre visible
  editions: string[];      // slugs reales de ediciones de la BD que incluye
  races: RaceOption[];     // razas disponibles para este grupo
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
  step: 'format' | 'sub_format' | 'pb_edition' | 'race' = 'format';
  selectedFormat = '';
  selectedFormatName = '';
  selectedSubFormat = '';
  selectedPbEdition: PbEditionOption | null = null;

  readonly enabledFormats = ['imp', 'esc'];
  readonly maintenanceFormats = ['imp_r', 'pb', 'pe'];

  /** Ediciones de Primer Bloque agrupadas con sus razas. */
  readonly pbEditions: PbEditionOption[] = [
    {
      slug: 'espada-sagrada',
      name: 'Espada Sagrada',
      editions: ['espada-sagrada', 'espada_sagrada_aniversario'],
      races: [
        { slug: 'dream', name: 'Dream', description: 'Todas las razas + neutrales' },
        { slug: 'caballero', name: 'Caballero', description: 'Aliados Caballero + neutrales' },
        { slug: 'dragon', name: 'Dragón', description: 'Aliados Dragón + neutrales' },
        { slug: 'faerie', name: 'Faerie', description: 'Aliados Faerie + neutrales' },
      ],
    },
    {
      slug: 'helenica',
      name: 'Helénica',
      editions: ['helenica', 'helenica_aniversario'],
      races: [
        { slug: 'dream', name: 'Dream', description: 'Todas las razas + neutrales' },
        { slug: 'heroe', name: 'Héroe', description: 'Aliados Héroe + neutrales' },
        { slug: 'olimpico', name: 'Olímpico', description: 'Aliados Olímpico + neutrales' },
        { slug: 'titan', name: 'Titán', description: 'Aliados Titán + neutrales' },
      ],
    },
    {
      slug: 'hijos-de-daana',
      name: 'Hijos de Daana',
      editions: ['hijos_de_daana'],
      races: [
        { slug: 'dream', name: 'Dream', description: 'Todas las razas + neutrales' },
        { slug: 'desafiante', name: 'Desafiante', description: 'Aliados Desafiante + neutrales' },
        { slug: 'defensor', name: 'Defensor', description: 'Aliados Defensor + neutrales' },
        { slug: 'sombra', name: 'Sombra', description: 'Aliados Sombra + neutrales' },
      ],
    },
    {
      slug: 'dominios-de-ra',
      name: 'Dominios de Ra',
      editions: ['dominios-de-ra'],
      races: [
        { slug: 'dream', name: 'Dream', description: 'Todas las razas + neutrales' },
        { slug: 'eterno', name: 'Eterno', description: 'Aliados Eterno + neutrales' },
        { slug: 'faraon', name: 'Faraón', description: 'Aliados Faraón + neutrales' },
        { slug: 'sacerdote', name: 'Sacerdote', description: 'Aliados Sacerdote + neutrales' },
      ],
    },
    {
      slug: 'pb-dream',
      name: 'Dream (todas las ediciones)',
      editions: [],
      races: [
        { slug: 'dream', name: 'Dream', description: 'Todas las razas del bloque + neutrales' },
        { slug: 'caballero', name: 'Caballero', description: 'Aliados Caballero + neutrales' },
        { slug: 'dragon', name: 'Dragón', description: 'Aliados Dragón + neutrales' },
        { slug: 'faerie', name: 'Faerie', description: 'Aliados Faerie + neutrales' },
        { slug: 'heroe', name: 'Héroe', description: 'Aliados Héroe + neutrales' },
        { slug: 'olimpico', name: 'Olímpico', description: 'Aliados Olímpico + neutrales' },
        { slug: 'titan', name: 'Titán', description: 'Aliados Titán + neutrales' },
        { slug: 'desafiante', name: 'Desafiante', description: 'Aliados Desafiante + neutrales' },
        { slug: 'defensor', name: 'Defensor', description: 'Aliados Defensor + neutrales' },
        { slug: 'sombra', name: 'Sombra', description: 'Aliados Sombra + neutrales' },
        { slug: 'eterno', name: 'Eterno', description: 'Aliados Eterno + neutrales' },
        { slug: 'faraon', name: 'Faraón', description: 'Aliados Faraón + neutrales' },
        { slug: 'sacerdote', name: 'Sacerdote', description: 'Aliados Sacerdote + neutrales' },
      ],
    },
  ];

  /** Ediciones de Primera Era agrupadas con sus razas. */
  readonly peEditions: PbEditionOption[] = [
    {
      slug: 'el-reto',
      name: 'El Reto',
      editions: ['el-reto'],
      races: [
        { slug: 'caballero', name: 'Caballero', description: 'Aliados Caballero + soporte de la edición' },
        { slug: 'dragon', name: 'Dragón', description: 'Aliados Dragón + soporte de la edición' },
        { slug: 'fairy', name: 'Fairy', description: 'Aliados Fairy + soporte de la edición' },
      ],
    },
    {
      slug: 'mundo-gotico',
      name: 'Mundo Gótico',
      editions: ['mundo-gotico'],
      races: [
        { slug: 'cazador', name: 'Cazador', description: 'Aliados Cazador + soporte de la edición' },
        { slug: 'vampiro', name: 'Vampiro', description: 'Aliados Vampiro + soporte de la edición' },
        { slug: 'licantropo', name: 'Licántropo', description: 'Aliados Licántropo + soporte de la edición' },
      ],
    },
    {
      slug: 'la-ira-del-nahual',
      name: 'La Ira del Nahual',
      editions: ['la-ira-del-nahual'],
      races: [
        { slug: 'bestia', name: 'Bestia', description: 'Aliados Bestia + soporte de la edición' },
        { slug: 'chaman', name: 'Chamán', description: 'Aliados Chamán + soporte de la edición' },
        { slug: 'guerrero', name: 'Guerrero', description: 'Aliados Guerrero + soporte de la edición' },
      ],
    },
    {
      slug: 'ragnarok',
      name: 'Ragnarok',
      editions: ['ragnarok'],
      races: [
        { slug: 'abominacion', name: 'Abominación', description: 'Aliados Abominación + soporte de la edición' },
        { slug: 'barbaro', name: 'Bárbaro', description: 'Aliados Bárbaro + soporte de la edición' },
        { slug: 'dios', name: 'Dios', description: 'Aliados Dios + soporte de la edición' },
      ],
    },
    {
      slug: 'espiritu-de-dragon',
      name: 'Espíritu de Dragón',
      editions: ['espiritu-de-dragon'],
      races: [
        { slug: 'campeon', name: 'Campeón', description: 'Aliados Campeón + soporte de la edición' },
        { slug: 'criaturas', name: 'Criaturas', description: 'Aliados Criaturas + soporte de la edición' },
        { slug: 'kami', name: 'Kami', description: 'Aliados Kami + soporte de la edición' },
        { slug: 'xian', name: 'Xian', description: 'Aliados Xian + soporte de la edición' },
      ],
    },
  ];

  readonly impRaces: RaceOption[] = [
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

  readonly escRaces: RaceOption[] = [
    { slug: 'dream', name: 'Dream', description: 'Todas las razas, talismanes, armas y tótems' },
    { slug: 'totem', name: 'Tótem', description: 'Aliados sin raza + tótems, talismanes y armas' },
    { slug: 'culto-tenebris', name: 'Culto Tenebris', description: 'Aliados Sombra + Oni + neutrales' },
    { slug: 'vigilantes-etereos', name: 'Vigilantes Etéreos', description: 'Aliados Eterno + Faerie + neutrales' },
    { slug: 'gremio-paladin', name: 'Gremio Paladín', description: 'Aliados Caballero + Sacerdote + neutrales' },
    { slug: 'clan-desafiante', name: 'Clan Desafiante', description: 'Aliados Dragón + Guerrero + neutrales' },
    { slug: 'oscuridad', name: 'Oscuridad', description: 'Aliados con habilidad Oscuridad + neutrales' },
    { slug: 'luz', name: 'Luz', description: 'Aliados con habilidad Luz + neutrales' },
    { slug: 'eterno', name: 'Eterno', description: 'Aliados Eterno + neutrales' },
    { slug: 'faerie', name: 'Faerie', description: 'Aliados Faerie + neutrales' },
    { slug: 'dragon', name: 'Dragón', description: 'Aliados Dragón + neutrales' },
    { slug: 'sombra', name: 'Sombra', description: 'Aliados Sombra + neutrales' },
    { slug: 'heroe', name: 'Héroe', description: 'Aliados Héroe + neutrales' },
    { slug: 'sacerdote', name: 'Sacerdote', description: 'Aliados Sacerdote + neutrales' },
    { slug: 'guerrero', name: 'Guerrero', description: 'Aliados Guerrero + neutrales' },
    { slug: 'bestia', name: 'Bestia', description: 'Aliados Bestia + neutrales' },
    { slug: 'caballero', name: 'Caballero', description: 'Aliados Caballero + neutrales' },
    { slug: 'ancestral', name: 'Ancestral', description: 'Aliados Ancestral + neutrales' },
    { slug: 'barbaro', name: 'Bárbaro', description: 'Aliados Bárbaro + neutrales' },
    { slug: 'samurai', name: 'Samurái', description: 'Aliados Samurái + neutrales' },
    { slug: 'oni', name: 'Oni', description: 'Aliados Oni + neutrales' },
  ];

  get races(): RaceOption[] {
    if (this.selectedFormat === 'pb' && this.selectedPbEdition) return this.selectedPbEdition.races;
    if (this.selectedFormat === 'pe' && this.selectedPbEdition) return this.selectedPbEdition.races;
    return this.selectedFormat === 'esc' ? this.escRaces : this.impRaces;
  }

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
        const order = ['imp', 'esc', 'imp_r', 'pb'];
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

  isMaintenance(code: string): boolean {
    return this.maintenanceFormats.includes(code);
  }

  getDisabledLabel(code: string): string {
    return this.isMaintenance(code) ? 'En mantenimiento' : 'Próximamente';
  }

  selectFormat(code: string) {
    if (!this.isEnabled(code)) return;
    this.selectedFormat = code;
    this.selectedFormatName = this.formats.find(f => f.code === code)?.name || code;
    if (code === 'imp') {
      this.step = 'sub_format';
    } else if (code === 'pb' || code === 'pe') {
      this.selectedSubFormat = 'racial';
      this.step = 'pb_edition';
    } else {
      this.selectedSubFormat = 'racial';
      this.step = 'race';
    }
  }

  selectSubFormat(sub: string) {
    this.selectedSubFormat = sub;
    this.step = 'race';
  }

  selectPbEdition(ed: PbEditionOption) {
    this.selectedPbEdition = ed;
    this.step = 'race';
  }

  selectRace(slug: string) {
    const qp: any = { race: slug };
    if (this.selectedSubFormat === 'vcr') {
      qp.sub_fmt = 'vcr';
    }
    if ((this.selectedFormat === 'pb' || this.selectedFormat === 'pe') && this.selectedPbEdition) {
      qp.pb_edition = this.selectedPbEdition.slug;
    }
    this.router.navigate(['/builder/new', this.selectedFormat], { queryParams: qp });
  }

  backToFormats() {
    this.step = 'format';
    this.selectedSubFormat = '';
    this.selectedPbEdition = null;
  }

  backToSubFormat() {
    this.step = 'sub_format';
  }

  backToPbEdition() {
    this.step = 'pb_edition';
    this.selectedPbEdition = null;
  }
}
